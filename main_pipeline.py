"""
main_pipeline.py
----------------
End-to-end pipeline & Dynamic Local Web Server:
  1. Spins up a local Flask server at http://127.0.0.1:5000/
  2. Spawns standard OS filedialog pickers for native, restriction-free local file selection
  3. Manages background crop & Surya Malayalam OCR threads cleanly
  4. Delivers dynamic real-time status polling & logs directly to the premium dashboard
  5. Feeds high-speed JSON parsed voter database & statistics to client-side charts
"""

import os
import sys
import json
import csv
import time
import threading
import webbrowser
import glob
import re
from flask import Flask, render_template, jsonify, request



import analytics

# Absolute path for the shared status file - used by both Flask and child process
STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline_status.json")

state_lock = threading.Lock()
_cached_device = None

def detect_execution_device():
    global _cached_device
    if _cached_device is not None:
        return _cached_device
    return "CPU"


# Flask App setup
app = Flask(__name__, template_folder="templates")
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Global pipeline execution state
pipeline_state = {
    "status": "idle",         # "idle", "cropping", "ocr", "saving", "done", "error"
    "crop_pct": 0,
    "ocr_pct": 0,
    "current_file": "",
    "action": "Ready.",
    "logs": [],
    "success": False,
    "created_csv": "",
    "cancel_requested": False,
    "device": detect_execution_device(),
    "error": None
}

# Thread lock already defined above
# Process state and logging helpers
def log_message(msg):
    """Safely append logs to server execution state."""
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"{msg}"
    print(f"[{timestamp}] {msg}")
    
    # Also attempt to append to json status logs list if exists
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["logs"].append(formatted_msg)
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass
    
    with state_lock:
        if "logs" in pipeline_state:
            pipeline_state["logs"].append(formatted_msg)

def run_ocr_background_task(pdf_paths, start_page, test_mode):
    """Background orchestrator executing Poppler cropper and Surya OCR inside a separate OS process."""
    import time
    import json
    import glob
    import os
    import csv
    
    # Redefine pipeline imports INSIDE the process block so they load cleanly
    import batch_cropper
    import surya_ocr
    import analytics
    
    sub_state = {
        "status": "cropping",
        "crop_pct": 0,
        "ocr_pct": 0,
        "current_file": os.path.basename(pdf_paths[0]) if pdf_paths else "",
        "action": "Booting pipeline task...",
        "logs": [],
        "success": False,
        "created_csv": "",
        "cancel_requested": False,
        "device": "CPU",
        "error": None
    }
    
    # Detect GPU device directly inside child process
    try:
        import torch
        sub_state["device"] = "GPU" if torch.cuda.is_available() else "CPU"
    except Exception:
        pass
        
    def update_sub_state(**kwargs):
        for k, v in kwargs.items():
            if v is not None:
                if k == "log_msg":
                    timestamp = time.strftime("%H:%M:%S")
                    sub_state["logs"].append(f"[{timestamp}] {v}")
                    print(f"[{timestamp}] {v}")
                else:
                    sub_state[k] = v
        # Write to the absolute path so Flask can always find it
        status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline_status.json")
        for _ in range(5):
            try:
                with open(status_file, "w", encoding="utf-8") as f:
                    json.dump(dict(sub_state), f)
                break
            except (PermissionError, FileNotFoundError):
                time.sleep(0.05)

    try:
        total_pdfs = len(pdf_paths)
        update_sub_state(log_msg=f"Initializing batch run: {total_pdfs} PDF(s) queued.")
        
        for file_idx, pdf_path in enumerate(pdf_paths, start=1):
            pdf_name = os.path.basename(pdf_path)
            update_sub_state(
                status="cropping",
                current_file=pdf_name,
                action=f"Segmenting page 1 of {pdf_name}...",
                log_msg=f"Processing PDF [{file_idx}/{total_pdfs}]: {pdf_name}"
            )
            
            # poppler crop output folder
            base_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(base_dir, "Cropped_Rows")
            os.makedirs(output_dir, exist_ok=True)
            
            # Clear old segments
            for f in glob.glob(os.path.join(output_dir, "*.png")):
                try:
                    os.remove(f)
                except Exception:
                    pass
            
            # Progress callback for PDF page splitter
            def crop_progress(current, total):
                pct = int((current / total) * 100)
                update_sub_state(
                    crop_pct=pct,
                    action=f"Segmenting page {current} of {total}..."
                )
            
            # Trigger Poppler PDF cropper
            update_sub_state(log_msg=f"Converting PDF pages into row images (Poppler)...")
            output_dir = batch_cropper.process_pdf(
                pdf_path=pdf_path,
                start_page=start_page,
                end_page=None,
                progress_callback=crop_progress,
                test_mode=test_mode
            )
            update_sub_state(crop_pct=100, log_msg="PDF segmentation complete.")
            
            # Find and sort segment files
            cropped_images = sorted(glob.glob(os.path.join(output_dir, "*.png")))
            if not cropped_images:
                raise Exception(f"No row segments detected inside cropped folder for {pdf_name}")
                
            total_images = len(cropped_images)
            update_sub_state(log_msg=f"Found {total_images} row images. Warmup Surya Malayalam OCR engine...")
            
            update_sub_state(
                status="ocr",
                ocr_pct=0,
                action=f"Initializing OCR engine for {total_images} cards..."
            )
            
            # Run OCR on each segment card
            all_people = []
            for idx, image_path in enumerate(cropped_images, start=1):
                try:
                    texts_by_card = surya_ocr.run_malayalam_ocr(image_path)
                    people        = surya_ocr.parse_ocr_data(texts_by_card)
                    all_people.extend(people)
                except Exception as exc:
                    update_sub_state(log_msg=f"Error processing row segment {idx}: {exc}")
                    
                pct = int((idx / total_images) * 100)
                update_sub_state(
                    ocr_pct=pct,
                    action=f"Extracting row segment {idx} of {total_images}..."
                )
                
                if idx % 10 == 0 or idx == total_images:
                    update_sub_state(log_msg=f"Surya Engine progress: Card {idx}/{total_images} OCR complete.")

            # Interpolate missing serial numbers
            update_sub_state(log_msg="Interpolating and cleaning Serial Number sequences...")
            last_serial = 0
            for person in all_people:
                sn_text = person.get("serial_number", "")
                digits = ''.join(filter(str.isdigit, sn_text))
                
                if digits:
                    last_serial = int(digits)
                    person["serial_number"] = str(last_serial)
                else:
                    last_serial += 1
                    person["serial_number"] = str(last_serial)
                    if "raw_fields" not in person:
                        person["raw_fields"] = []
                    person["raw_fields"].append(f"(Auto-filled serial: {last_serial})")

            # Write to CSV
            update_sub_state(
                status="saving",
                action=f"Saving {len(all_people)} records to spreadsheet..."
            )
            
            pdf_basename = os.path.splitext(pdf_name)[0]
            csv_filename = f"{pdf_basename}.csv"
            
            csv_dir = os.path.join(base_dir, "Processed_CSVs")
            os.makedirs(csv_dir, exist_ok=True)
            csv_path = os.path.join(csv_dir, csv_filename)
            
            update_sub_state(log_msg=f"Writing CSV output dataset to: {csv_path}")
            
            # Setup columns definition inside process scope
            FIELDNAMES = ["serial_number", "voter_id", "name", "guardian", "house_number", "age_gender", "raw_fields"]
            with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES, extrasaction="ignore")
                writer.writeheader()
                
                for person in all_people:
                    if isinstance(person.get("raw_fields"), list):
                        person["raw_fields"] = " | ".join(person["raw_fields"])
                    writer.writerow({key: person.get(key, "") for key in FIELDNAMES})
                    
            update_sub_state(log_msg=f"Successfully saved structured records to: {csv_filename}")

            # Generate backup dashboard HTML & Synchronize drop list
            update_sub_state(action="Synchronizing global analytics directories...")
            try:
                analytics.generate_analytics_report(csv_path)
                update_sub_state(log_msg="Local data catalogs synchronized successfully.")
            except Exception as report_err:
                update_sub_state(log_msg=f"Catalog synchronization warning: {report_err}")
                
        # Final success flag setting
        update_sub_state(
            status="done",
            success=True,
            created_csv=csv_filename,
            action="Execution finished."
        )
        update_sub_state(log_msg="All pipeline tasks executed successfully.")
            
    except Exception as err:
        update_sub_state(
            status="error",
            error=str(err),
            log_msg=f"Process interrupted: {err}"
        )

# Global active process tracker
import multiprocessing
active_pipeline_process = None

# ---------------------------------------------------------------------------
# WEB APPLICATION SERVER ROUTINGS
# ---------------------------------------------------------------------------

@app.route('/')
def home():
    """Render single-page dynamic analytics control center."""
    return render_template("index.html")

@app.route('/api/browse', methods=['POST'])
def browse_files():
    """Trigger native Windows Forms filedialog using a process-isolated PowerShell script."""
    data = request.get_json() or {}
    browse_type = data.get("type", "files")
    
    paths = []
    
    # We use PowerShell Windows Forms dialogs which are natively topmost and fully thread-safe!
    if browse_type == "files":
        ps_script = (
            "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;"
            "$d = New-Object System.Windows.Forms.OpenFileDialog;"
            "$d.Filter = 'PDF files (*.pdf)|*.pdf';"
            "$d.Multiselect = $true;"
            "$d.Title = 'Select Voter-Roll PDF(s)';"
            "if ($d.ShowDialog() -eq 'OK') { ConvertTo-Json @($d.FileNames) } else { ConvertTo-Json @() }"
        )
    else:
        ps_script = (
            "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;"
            "$d = New-Object System.Windows.Forms.FolderBrowserDialog;"
            "$d.Description = 'Select Folder Containing PDFs';"
            "if ($d.ShowDialog() -eq 'OK') { "
            "  $folder = $d.SelectedPath; "
            "  $files = Get-ChildItem -Path $folder -Filter *.pdf | ForEach-Object { $_.FullName }; "
            "  ConvertTo-Json @($files) "
            "} else { ConvertTo-Json @() }"
        )
        
    try:
        import subprocess
        import json
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=120
        )
        if res.stdout.strip():
            paths = json.loads(res.stdout.strip())
            if isinstance(paths, str):
                paths = [paths]
    except Exception as err:
        log_message(f"PowerShell local file picker error: {err}")
        paths = []
        
    return jsonify({"paths": paths})

@app.route('/api/start_ocr', methods=['POST'])
def start_ocr():
    """Initialize standard Malayalam OCR run inside background multiprocessing process."""
    global pipeline_state, active_pipeline_process
    
    data = request.get_json() or {}
    paths = data.get("paths", [])
    start_page = int(data.get("start_page", 3))
    test_mode = data.get("test_mode", False)
    
    if not paths:
        return jsonify({"status": "error", "message": "No PDF paths supplied."}), 400
        
    with state_lock:
        # Check if the process is alive
        if active_pipeline_process and active_pipeline_process.is_alive():
            return jsonify({"status": "error", "message": "An extraction job is already in progress."}), 409
            
        # Clean up old status file
        if os.path.exists(STATUS_FILE):
            try:
                os.remove(STATUS_FILE)
            except Exception:
                pass
                
        # Reset local in-memory tracker status
        pipeline_state.update({
            "status": "cropping",
            "crop_pct": 0,
            "ocr_pct": 0,
            "current_file": os.path.basename(paths[0]) if paths else "",
            "action": "Booting pipeline task...",
            "logs": [],
            "success": False,
            "created_csv": "",
            "cancel_requested": False,
            "device": detect_execution_device(),
            "error": None
        })
        
        # Write initial JSON status file
        for _ in range(5):
            try:
                with open(STATUS_FILE, "w", encoding="utf-8") as f:
                    json.dump(dict(pipeline_state), f)
                break
            except (PermissionError, FileNotFoundError):
                time.sleep(0.05)
        
    # Start the clean, process-isolated child task!
    active_pipeline_process = multiprocessing.Process(
        target=run_ocr_background_task,
        args=(paths, start_page, test_mode),
        daemon=True
    )
    active_pipeline_process.start()
    
    return jsonify({"status": "started"})

@app.route('/api/cancel_ocr', methods=['POST'])
def cancel_ocr():
    """Request the active background pipeline process to cancel/terminate execution."""
    global pipeline_state, active_pipeline_process
    
    with state_lock:
        if active_pipeline_process and active_pipeline_process.is_alive():
            log_message("User requested process cancellation. Terminating active GPU process...")
            # Terminate and reclaim VRAM instantly!
            active_pipeline_process.terminate()
            active_pipeline_process.join(timeout=5)
            active_pipeline_process = None
            
        # Reset state to idle
        pipeline_state.update({
            "status": "idle",
            "cancel_requested": True,
            "action": "Process cancelled by user."
        })
        
        # Write cancelled status to JSON
        for _ in range(5):
            try:
                with open(STATUS_FILE, "w", encoding="utf-8") as f:
                    json.dump(dict(pipeline_state), f)
                break
            except (PermissionError, FileNotFoundError):
                time.sleep(0.05)
            
    return jsonify({"status": "idle"})

@app.route('/api/ocr_status', methods=['GET'])
def get_ocr_status():
    """Retrieve progress metrics and logs from the shared JSON status file."""
    data = None
    if os.path.exists(STATUS_FILE):
        for _ in range(5):
            try:
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        break
            except (PermissionError, json.JSONDecodeError, FileNotFoundError):
                time.sleep(0.05)
            
    if data is None:
        # Fallback to in-memory state
        with state_lock:
            data = dict(pipeline_state)
            
    resp = jsonify(data)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

@app.route('/api/csvs', methods=['GET'])
def list_processed_csvs():
    """Scan processed folder and return index sorted alphabetically."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_dir = os.path.join(base_dir, "Processed_CSVs")
    
    if not os.path.exists(csv_dir):
        return jsonify({"csvs": []})
        
    csvs = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
    csvs.sort()
    return jsonify({"csvs": csvs})

@app.route('/api/csv_data/<csv_name>', methods=['GET'])
def get_csv_data(csv_name):
    """Compile structured counts and row sets for direct dashboard load."""
    csv_name = os.path.basename(csv_name) # sanitize
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "Processed_CSVs", csv_name)
    
    if not os.path.exists(csv_path):
        return jsonify({"error": "Specified CSV file not found"}), 404
        
    data = analytics.compile_csv_data(csv_path)
    if not data:
        return jsonify({"error": "Failed to parse CSV dataset"}), 500
        
    return jsonify(data)

# ---------------------------------------------------------------------------
# SERVER INITIALIZER AND BROWSER AUTOMATIC RUNNER
# ---------------------------------------------------------------------------

def boot_browser():
    """Briefly wait for Flask routing table to load, then open default browser."""
    time.sleep(1.5)
    log_message("Launching interactive browser dashboard at http://127.0.0.1:5000/ ...")
    webbrowser.open("http://127.0.0.1:5000/")

def main():
    # Detect GPU/CPU execution device lazily in a background thread to prevent PyTorch from blocking Flask startup
    def load_device_cache():
        global _cached_device
        try:
            import torch
            dev = "GPU" if torch.cuda.is_available() else "CPU"
        except Exception:
            dev = "CPU"
        _cached_device = dev
        with state_lock:
            pipeline_state["device"] = dev

    threading.Thread(target=load_device_cache, daemon=True).start()

    # Auto-open browser thread
    threading.Thread(target=boot_browser, daemon=True).start()
    
    # Run multi-threaded Flask server
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
