"""
batch_cropper.py
----------------
Crops the 10 fixed row-regions from every page (3-31) of the voter-roll PDF
using pre-defined perspective coordinates.

Includes a simple Tkinter GUI crop-tool so you can visually re-pick the row
coordinates on a new PDF if the layout ever changes.

Usage
-----
    python batch_cropper.py                    # file dialog + use saved coords
    python batch_cropper.py path/to/file.pdf   # direct path

Environment
-----------
    POPPLER_PATH   Path to poppler bin dir (required on Windows).
                   e.g.  set POPPLER_PATH=C:\path\to\poppler\bin
                   Leave unset on Linux / Mac.
"""

import os
import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np
import pdf2image
from PIL import Image, ImageTk

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DPI          = 200
POPPLER_PATH = os.environ.get("POPPLER_PATH", None)

# Fallback if POPPLER_PATH env var is not set and you are on Windows,
# edit the line below with your local path:
if POPPLER_PATH is None and sys.platform == "win32":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    _local_poppler = os.path.join(base_dir, "poppler-extracted", "poppler-24.08.0", "Library", "bin")
    if os.path.isdir(_local_poppler):
        POPPLER_PATH = _local_poppler

# Pre-measured coordinates for the 10 row-regions (pixels at DPI=200).
# Each entry is [top-left, top-right, bottom-right, bottom-left].
FIXED_ROWS = [
    [(37.6, 76.7),   (1612.4, 76.7),  (1613.9, 287.1),  (36.1, 287.1)],
    [(40.6, 297.6),  (1610.9, 297.6), (1612.4, 506.6),  (36.1, 506.6)],
    [(40.6, 518.6),  (1610.9, 515.6), (1613.9, 726.1),  (36.1, 727.6)],
    [(37.6, 738.1),  (1610.9, 736.6), (1610.9, 948.5),  (37.6, 948.5)],
    [(39.1, 959.1),  (1615.4, 956.0), (1613.9, 1165.0), (36.1, 1169.5)],
    [(36.1, 1177.0), (1613.9, 1175.5),(1613.9, 1387.5), (36.1, 1387.5)],
    [(37.6, 1396.5), (1612.4, 1398.0),(1612.4, 1609.9), (36.1, 1609.9)],
    [(40.6, 1617.5), (1610.9, 1617.5),(1613.9, 1829.4), (39.1, 1829.4)],
    [(36.1, 1839.9), (1613.9, 1838.4),(1610.9, 2050.4), (37.6, 2050.4)],
    [(36.1, 2062.4), (1610.9, 2062.4),(1613.9, 2269.9), (36.1, 2271.4)],
]

COORDS_SAVE_FILE = "row_coords.json"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def sort_quad(pts):
    """Return 4 points ordered [top-left, top-right, bottom-right, bottom-left]."""
    pts  = np.array(pts, dtype="float32")
    s    = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    tl   = pts[np.argmin(s)]
    br   = pts[np.argmax(s)]
    tr   = pts[np.argmin(diff)]
    bl   = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype="float32")


def perspective_crop(image_bgr, pts_float):
    """Warp a quadrilateral region to a flat rectangle."""
    src            = sort_quad(pts_float)
    tl, tr, br, bl = src
    w = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    if w < 1 or h < 1:
        return None
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype="float32")
    M   = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image_bgr, M, (w, h))


# ---------------------------------------------------------------------------
# GUI Crop Tool
# ---------------------------------------------------------------------------

class CropTool:
    """
    Interactive Tkinter window that lets you draw new row rectangles on a
    preview of page 3 of the PDF.  Click four corners per row, then save.
    Saved coordinates are written to row_coords.json next to the script.
    """

    DISPLAY_MAX = 900   # max height of the preview image on screen

    def __init__(self, root, page_bgr, scale):
        self.root    = root
        self.page    = page_bgr
        self.scale   = scale          # display_px / real_px
        self.rows    = []             # list of completed quads (real coords)
        self.current = []             # corners being picked for current row
        self.circles = []
        self.lines   = []

        root.title("Crop Tool — click 4 corners per row, then Save")

        # Convert BGR → RGB → PhotoImage
        rgb = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        dh   = int(h * scale)
        dw   = int(w * scale)
        pil  = Image.fromarray(rgb).resize((dw, dh), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(pil)

        self.canvas = tk.Canvas(root, width=dw, height=dh, cursor="crosshair")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.canvas.bind("<Button-1>", self._on_click)

        # Scrollbar for tall pages
        sb = tk.Scrollbar(root, orient=tk.VERTICAL, command=self.canvas.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=sb.set, scrollregion=(0, 0, dw, dh))
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1*(e.delta//120), "units"))

        # Controls
        ctrl = tk.Frame(root)
        ctrl.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(ctrl, text="Click 4 corners per row (TL→TR→BR→BL). Undo last point or clear current row.").pack(side=tk.LEFT, padx=6)
        tk.Button(ctrl, text="Undo point",   command=self._undo).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="Clear row",    command=self._clear_row).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="Save & close", command=self._save, bg="#2e7d32", fg="white").pack(side=tk.RIGHT, padx=8, pady=4)

        self.status = tk.Label(ctrl, text="Row 1 — pick corner 1/4", anchor=tk.W)
        self.status.pack(side=tk.LEFT, padx=10)

    def _on_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        # Store in real coordinates
        rx = cx / self.scale
        ry = cy / self.scale
        self.current.append((rx, ry))
        r = self.canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill="red", outline="white", width=1)
        self.circles.append(r)

        if len(self.current) > 1:
            px, py = self.current[-2]
            l = self.canvas.create_line(
                px * self.scale, py * self.scale, cx, cy,
                fill="cyan", width=2
            )
            self.lines.append(l)

        if len(self.current) == 4:
            # Close the quad
            px, py = self.current[0]
            l = self.canvas.create_line(
                self.current[-1][0] * self.scale, self.current[-1][1] * self.scale,
                px * self.scale, py * self.scale,
                fill="cyan", width=2
            )
            self.lines.append(l)
            self.rows.append(list(self.current))
            self.current = []
            self.circles = []
            self.lines   = []
            self._update_status()

        else:
            corner = len(self.current)
            self.status.config(text=f"Row {len(self.rows)+1} — pick corner {corner}/4")

    def _undo(self):
        if self.current:
            self.current.pop()
            if self.circles:
                self.canvas.delete(self.circles.pop())
            if self.lines:
                self.canvas.delete(self.lines.pop())
            self._update_status()

    def _clear_row(self):
        for item in self.circles + self.lines:
            self.canvas.delete(item)
        self.current = []
        self.circles = []
        self.lines   = []
        self._update_status()

    def _update_status(self):
        self.status.config(text=f"Row {len(self.rows)+1} — pick corner 1/4  ({len(self.rows)} row(s) done)")

    def _save(self):
        if not self.rows:
            messagebox.showwarning("Nothing to save", "No rows have been defined yet.")
            return
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), COORDS_SAVE_FILE)
        with open(save_path, "w") as f:
            json.dump(self.rows, f, indent=2)
        messagebox.showinfo("Saved", f"{len(self.rows)} row(s) saved to:\n{save_path}")
        self.root.destroy()


def launch_crop_tool(pdf_path):
    """Open the crop tool on page 3 of *pdf_path* and block until closed."""
    print("Rendering page 3 for crop tool...")
    pages = pdf2image.convert_from_path(
        pdf_path, dpi=DPI, poppler_path=POPPLER_PATH, first_page=3, last_page=3
    )
    if not pages:
        print("Could not render page 3.")
        return

    page_bgr = cv2.cvtColor(np.array(pages[0]), cv2.COLOR_RGB2BGR)
    h        = page_bgr.shape[0]
    scale    = min(1.0, CropTool.DISPLAY_MAX / h)

    root = tk.Tk()
    CropTool(root, page_bgr, scale)
    root.mainloop()


# ---------------------------------------------------------------------------
# Load coordinates (saved file takes priority over hardcoded FIXED_ROWS)
# ---------------------------------------------------------------------------

def load_row_coords():
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), COORDS_SAVE_FILE)
    if os.path.isfile(save_path):
        with open(save_path) as f:
            coords = json.load(f)
        print(f"Loaded {len(coords)} row(s) from {COORDS_SAVE_FILE}")
        return coords
    return FIXED_ROWS


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_pdf(pdf_path=None, start_page=3, end_page=None, progress_callback=None, test_mode=False):
    """
    Crop all row-regions from start_page to end_page of the voter-roll PDF and save
    them as PNGs in an 'auto_cropped_rows/<pdf_name>' subfolder next to the PDF.
    If end_page is None, it automatically calculates the second-to-last page.
    If test_mode is True, it extracts up to the very last page.

    Returns the path to the output directory, or None on failure.
    """
    # --- Resolve PDF path ---
    if not pdf_path:
        root = tk.Tk()
        root.withdraw()
        pdf_path = filedialog.askopenfilename(
            title="Select Voter-Roll PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        root.destroy()

    if not pdf_path or not os.path.isfile(pdf_path):
        print("No valid PDF selected. Exiting.")
        return None

    row_coords = load_row_coords()
    
    # --- Calculate Dynamic End Page ---
    if not end_page:
        info = pdf2image.pdfinfo_from_path(pdf_path, poppler_path=POPPLER_PATH)
        total_pdf_pages = info.get("Pages", 0)
        
        if test_mode:
            end_page = total_pdf_pages
        else:
            if total_pdf_pages > 1:
                end_page = total_pdf_pages - 1
            else:
                end_page = start_page

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "auto_cropped_rows", pdf_name)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    total_pages = end_page - start_page + 1
    for i, page_num in enumerate(range(start_page, end_page + 1)):
        print(f"  Rendering page {page_num}...")
        if progress_callback:
            progress_callback(i + 1, total_pages)
        try:
            pages = pdf2image.convert_from_path(
                pdf_path,
                dpi=DPI,
                poppler_path=POPPLER_PATH,
                first_page=page_num,
                last_page=page_num,
            )
        except Exception as exc:
            print(f"  Stopped at page {page_num}: {exc}")
            break

        if not pages:
            print("  Reached end of PDF.")
            break

        page_bgr = cv2.cvtColor(np.array(pages[0]), cv2.COLOR_RGB2BGR)

        for row_idx, pts in enumerate(row_coords):
            warped = perspective_crop(page_bgr, pts)
            if warped is not None and warped.size > 0:
                fname = f"page{page_num:03d}_row{row_idx + 1:04d}.png"
                cv2.imwrite(os.path.join(output_dir, fname), warped)

    print(f"\nDone - cropped rows saved to: {output_dir}")
    return output_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch-crop voter-roll PDF rows.")
    parser.add_argument("pdf", nargs="?", help="Path to voter-roll PDF.")
    parser.add_argument("--crop-tool", action="store_true",
                        help="Launch the visual crop tool to define new row coordinates.")
    args = parser.parse_args()

    pdf = args.pdf
    if not pdf:
        root = tk.Tk()
        root.withdraw()
        pdf = filedialog.askopenfilename(
            title="Select Voter-Roll PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        root.destroy()

    if not pdf:
        print("No PDF selected.")
        sys.exit(1)

    if args.crop_tool:
        launch_crop_tool(pdf)

    process_pdf(pdf)
