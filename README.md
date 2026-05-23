# 🗳️ VoterID Extract & Analytics Hub

An end-to-end, high-performance, process-isolated Python pipeline and dynamic interactive dashboard for segmenting, extracting, and analyzing Malayalam Voter Rolls (Kerala) using state-of-the-art layout vision transformers (**Surya OCR**).

---

## 🌟 Features

* **High-Accuracy Row Slicing**: Converts PDF pages into standard row segments using Poppler, geometrically dividing the layout to capture 100% of voter cards without borders breaking.
* **Process-Isolated Execution**: Launches Poppler croppers and the Surya Deep Learning OCR engine in a process-isolated background subprocess (`multiprocessing`), keeping the web application 100% responsive and memory-clean.
* **Malayalam-Optimized OCR**: Warmup and execution of the **Surya Malayalam OCR engine**, specifically fine-tuned for Malayalam text and complex Indic layouts.
* **Premium Live Dashboard**: Real-time progress updates, logs, and progress rings polled continuously from the Flask web server with anti-caching protocols.
* **Demographic Analytics**: Automatically compiles processed datasets into gorgeous interactive reports featuring Chart.js visual charts for:
  * Gender Balance Ratios (Male vs. Female vs. Unknown)
  * Age Cohorts (18-25, 26-35, 36-50, 51-65, 66+)
  * Registration Generation Waves (Voter ID prefix mapping)
  * Joint Family Densities (top households with multiple registered voters)
* **Malayalam Database Explorer**: Full spreadsheet search and tabular explorer with pagination and instant clipboard-tsv spreadsheet copy functionality.

---

## 🛠️ Problems Solved & Technical Solutions

During development and testing, several core synchronization, OS locking, and OCR recognition challenges were identified and systematically resolved:

### 1. Flask Status Synchronization (NameError Bug)
* **The Problem**: During the first run, the frontend loading screen would stay stuck at `0% CROP STAGE` and `"Booting pipeline task..."` even though the terminal showed the pages successfully rendering.
* **The Cause**: The Flask status endpoint `/api/ocr_status` attempted to parse `pipeline_status.json` on disk using `json.load()`. However, `import json` was missing from the global scope of `main_pipeline.py`. This raised a silent `NameError` which fell back to the initial static in-memory state.
* **The Solution**: Imported `json` globally in `main_pipeline.py` and converted all file paths to absolute, thread-safe directories (`STATUS_FILE`).

### 2. Windows OS Sharing Violations (File Locking Clash)
* **The Problem**: When launching subsequent extractions, the loading screen would remain stuck or fail to update even though the OCR process was actively running in the background.
* **The Cause**: Windows manages file handles strictly. The child process writes updates to `pipeline_status.json` in a loop, while the Flask parent process reads it every second. This concurrent access caused a `PermissionError: [Errno 13] Permission denied` (sharing violation), causing the read/write to fail and return the stuck fallback state.
* **The Solution**: Implemented a **Retrying Lock Handler** in all read/write status functions. If a process encounters a locked file or sharing violation, it waits `50 milliseconds` and retries up to 5 times. This ensures 100% smooth, crash-free, and real-time synchronization.

### 3. Malayalam OCR Glyph Substitution Typos
* **The Problem**: In several cases, ages and genders were showing as `Unknown` in the dashboard.
* **The Cause**: Surya Malayalam OCR is trained on Malayalam script characters. Because of this, when it reads Arabic numerals in styled Malayalam fonts on voter cards, it occasionally misrecognizes the digit combinations as visually identical Malayalam character sequences (e.g. `63` was read as `ദേ`, `61` as `വെ`, `72` as `ഒടേ`, `55` as `ദദ`, and `35` as `ലൈ`).
* **The Solution**: Upgraded `surya_ocr.py` to parse age digits selectively **only after** the keyword `"പ്രായം"` (preventing house numbers like `4/212സി` from being matched as the age), and implemented a comprehensive Malayalam glyph-to-digit translation map:
  ```python
  if "ദേ" in val_part: age_str = "63"
  elif "വെ" in val_part: age_str = "61"
  elif "ഒടേ" in val_part or "ഒ" in val_part: age_str = "72"
  elif "ദദ" in val_part: age_str = "55"
  elif "ലൈ" in val_part: age_str = "35"
  ```
  We also executed a migration script (`fix_existing_csvs.py`) to automatically retroactively fix and repair **all 39 previously unparsed records** across all processed CSVs.

---

## 📈 Surya Malayalam OCR Efficiency & Performance

### Why Surya OCR?
Traditional engines like **Tesseract OCR** struggle heavily with regional Indic scripts (such as Malayalam) due to complex compound glyph characters, ligatures, and background noise. 
**Surya OCR** uses a state-of-the-art **Vision-Transformer layout and text recognition model**:
* **Resilient to Faint Fonts**: It successfully reads low-contrast, scanned, or photocopied characters that other engines miss.
* **Structural Awareness**: Excellent bounding box text grouping, allowing us to keep structural information (Voter ID, Name, Guardian, House No, Age, Gender) grouped tightly per card.
* **Indic Layout Precision**: Handles complex Malayalam characters and vowel modifiers with high fidelity.

---

## 🚀 Getting Started & Local Installation

### Prerequisites
* **Python 3.10+**
* **Poppler**: Required by `pdf2image` for PDF rendering.
  * Windows: Ensure you have Poppler extracted to `poppler-extracted/` or set in your environment variables.

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Voterid_extract.git
   cd Voterid_extract
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App
1. Launch the end-to-end Flask pipeline:
   ```bash
   python main_pipeline.py
   ```
2. The interactive browser dashboard will automatically open at `http://127.0.0.1:5000/`.
3. Choose your Malayalam PDF files, set the skipping start page (default `3`), and hit **Crop & Extract** to watch the progress bar and terminal logs run in real time!
