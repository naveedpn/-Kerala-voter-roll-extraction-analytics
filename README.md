# 🗳️ VoterID Extract & Analytics Hub

An end-to-end, high-performance, process-isolated Python pipeline and dynamic interactive dashboard for segmenting, extracting, and analyzing Malayalam Voter Rolls (Kerala) using state-of-the-art layout vision transformers (**Surya OCR**).

---

## 🌍 Real-World Impact & Applications

This project bridges the gap between raw, static electoral PDF documents and actionable, real-world community insights. Below are key real-world scenarios where this tool is highly helpful:

### 1. Targeted Democratic Campaigning (Microlocal Outreach)
* **Senior Citizen Assistance**: Political campaigns and social welfare groups can identify households with multiple senior citizens (`66+`) in a ward to coordinate physical logistics, wheelchair support, or transport to polling booths on election day.
* **Youth Engagement**: Organizers can locate clusters of young voters (`18-25`) to run ward-level student outreach, digital policy debates, or first-time voter celebration forums.

### 2. Family Density & Grassroots Campaigning
* **Joint Family Engagement**: By automatically clustering voters by house numbers, the tool identifies high-density family households. This allows grassroots volunteers to optimize their door-to-door campaigning by prioritizing joint families where a single household represents 8+ registered voters.

### 3. Electoral Registry Audits & Voter Rights Protection
* **Detecting Errors & Auditing**: Electoral reform NGOs and local civic groups can audit raw PDF lists to verify that voters are registered correctly, ensure missing family members are restored, correct Malayalam spelling errors in addresses, and report duplicate registrations or deceased entries.
* **WARD-Level Audits**: Search the entire booth database instantly by name, address, or voter ID prefix in the browser to audit registration completeness during revised voter roll publication cycles.

### 4. Public Policy & Sociological Research
* **Gender Disparity Analysis**: Social scientists can analyze booth-level gender ratios to map out local gender representation trends and target civic awareness programs to sections where female voter registration is underrepresented.

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



### 1. Malayalam OCR Glyph Substitution Typos
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
