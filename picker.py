import tkinter as tk
from tkinter import filedialog
import sys
import json
import glob
import os

def main():
    browse_type = sys.argv[1] if len(sys.argv) > 1 else "files"
    root = tk.Tk()
    # Keep the root window as a standard window but shrink it to a 1-pixel dot
    root.geometry("1x1+0+0")
    root.lift()
    root.attributes("-topmost", True)
    
    paths = []
    if browse_type == "files":
        selected = filedialog.askopenfilenames(
            parent=root,
            title="Select Voter-Roll PDF(s)",
            filetypes=[("PDF files", "*.pdf")]
        )
        paths = list(selected)
    else:
        folder = filedialog.askdirectory(parent=root, title="Select Folder Containing PDFs")
        if folder:
            paths = sorted(glob.glob(os.path.join(folder, "*.pdf")))
            
    root.destroy()
    print(json.dumps(paths))

if __name__ == "__main__":
    main()
