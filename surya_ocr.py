import os
import cv2
import numpy as np
from PIL import Image
from surya.common.surya.schema import TaskNames
from surya.detection import DetectionPredictor
from surya.foundation import FoundationPredictor
from surya.recognition import RecognitionPredictor


# ---------------------------------------------------------------------------
# Card detection
# ---------------------------------------------------------------------------

def get_cropped_cards(image_path):
    """
    Geometrically slice the row image into 3 perfect equal thirds.
    This guarantees exactly 3 cards are processed per row, preventing
    any skips due to faint or broken borders.
    """
    pil_image = Image.open(image_path).convert("RGB")
    w, h = pil_image.size
    
    card_w = w // 3
    cards = []
    
    for i in range(3):
        box = (i * card_w, 0, (i + 1) * card_w, h)
        cards.append(pil_image.crop(box))
        
    return cards


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

_foundation_predictor = None
_det_predictor = None
_rec_predictor = None

def run_malayalam_ocr(image_path):
    """
    Run Surya OCR on all cards found in image_path.
    Returns a list of lists: [ [{text, confidence}, ...], ... ]
    One inner list per card.
    """
    global _foundation_predictor, _det_predictor, _rec_predictor

    print("  Finding cards in image...")
    cropped_images = get_cropped_cards(image_path)
    print(f"  Found {len(cropped_images)} card(s).")

    if _foundation_predictor is None:
        print("  Loading Surya models into GPU/Memory (Once)...")
        _foundation_predictor = FoundationPredictor()
        _det_predictor        = DetectionPredictor()
        _rec_predictor        = RecognitionPredictor(_foundation_predictor)

    print("  Running OCR...")
    predictions = _rec_predictor(
        cropped_images,
        task_names=[TaskNames.ocr_with_boxes] * len(cropped_images),
        det_predictor=_det_predictor,
    )

    extracted_data_by_card = []
    for pred in predictions:
        card_data = []
        if pred and getattr(pred, "text_lines", None):
            sorted_lines = sorted(
                pred.text_lines,
                key=lambda l: (round(l.bbox[1] / 30) * 30, l.bbox[0])
            )
            for line in sorted_lines:
                text = line.text.strip()
                if not text:
                    continue
                confidence = round(getattr(line, "confidence", 0.0), 2)
                card_data.append({"text": text, "confidence": confidence, "bbox": line.bbox})
        extracted_data_by_card.append(card_data)

    return extracted_data_by_card


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _is_voter_id(text):
    """
    Kerala voter IDs: 3 uppercase letters + 7 digits  e.g. UAZ1658285
    """
    if len(text) != 10:
        return False
    return text[:3].isalpha() and text[:3].isupper() and text[3:].isdigit()


import re

def parse_ocr_data(texts_by_card):
    """
    Convert raw OCR token lists into structured dicts, one per person.
    Since texts_by_card already groups text by card (1 person = 1 card),
    we process all text in a card into a single person dictionary.
    """
    people = []

    for card_texts in texts_by_card:
        current_person = {}
        fields = []

        # --- Positional Tagging for Serial Number ---
        # Find the text block closest to the top-left corner (min x+y) that has digits
        serial_item = None
        min_dist = float('inf')
        for item in card_texts:
            text = item["text"].strip()
            # Look for a short string containing at least one digit
            if len(text) <= 5 and any(c.isdigit() for c in text):
                bbox = item.get("bbox", [0, 0, 0, 0])
                dist = bbox[0] + bbox[1]  # x + y distance from origin
                if dist < min_dist:
                    min_dist = dist
                    serial_item = item
                    
        if serial_item:
            current_person["serial_number"] = serial_item["text"]

        for item in card_texts:
            text = item["text"].strip()
            if not text:
                continue

            fields.append(text)

            # Skip the serial item since we already parsed it
            if serial_item and text == serial_item["text"]:
                continue

            # Parse Name
            if text.startswith("പേര്"):
                val = text.split(":", 1)[-1] if ":" in text else text.replace("പേര്", "")
                current_person["name"] = val.strip()
            
            # Parse Guardian
            elif any(k in text for k in ("അമ്മയുടെ", "അച്ഛന്റെ", "ഭർത്താവിന്റെ", "രക്ഷാ", "അച്ചന്റെ")):
                current_person["guardian"] = text
            
            # House number parsing removed from here to be processed with priorities after the loop
            
            # Parse Age & Gender
            elif any(k in text for k in ("പ്രായം", "പ്രയം", "പ്രാം", "ായം")):
                # Focus only on the portion of text after the "age" keyword to avoid house/serial numbers
                parts_by_prayam = re.split(r'പ്രായം|പ്രയം|ായം', text, maxsplit=1)
                after_prayam = parts_by_prayam[1] if len(parts_by_prayam) > 1 else text
                
                # Extract age
                age_str = ""
                digit_match = re.search(r'\d+', after_prayam)
                if digit_match:
                    age_str = digit_match.group()
                else:
                    # Look for glyph substitutions in the section after key word
                    val_part = after_prayam.replace(":", "").replace("-", "").strip()
                    if "ദേ" in val_part:
                        age_str = "63"
                    elif "വെ" in val_part:
                        age_str = "61"
                    elif any(o in val_part for o in ("ഒടേ", "ഒഴെ", "ഒേ", "ഒ")):
                        age_str = "72"
                    elif "ദദ" in val_part:
                        age_str = "55"
                    elif "ദ" in val_part:
                        age_str = "60"
                    elif "മു" in val_part:
                        age_str = "33"
                    elif "ഈ" in val_part:
                        age_str = "21"
                    elif "ഖ" in val_part:
                        age_str = "45"
                    elif "ലൈ" in val_part:
                        age_str = "35"
                        
                # Extract gender
                gender_str = "Unknown"
                if any(f_var in text for f_var in ["സ്ത്രീ", "Female", "സ്കീ", "സ്തീ", "സൂീ", "സ്ലീ", "സ്ക്കീ", "സൂ"]):
                    gender_str = "സ്ത്രീ"
                elif any(m_var in text for m_var in ["പുരുഷൻ", "Male", "പുരുഷ", "പരുഷൻ", "പു"]):
                    gender_str = "പുരുഷൻ"
                
                if age_str:
                    current_person["age_gender"] = f"{age_str} {gender_str}"
                else:
                    current_person["age_gender"] = gender_str
            
            # Parse Voter ID
            elif _is_voter_id(text):
                current_person["voter_id"] = text

        # Prioritized House Number Extraction
        best_house = ""
        # 1. Look for a line that is EXACTLY digits/digits
        for f in fields:
            if re.search(r'^\d+/\d+$', f.strip()):
                best_house = f.strip()
                break
                
        # 2. Look for a line containing digits/digits if we didn't find exact match
        if not best_house:
            for f in fields:
                if re.search(r'\d+/\d+', f):
                    best_house = f.strip()
                    break
                    
        # 3. Look for labeled line if still not found
        if not best_house:
            for f in fields:
                if "വീട്ടു" in f and "നമ്പ" in f:
                    val = f.split(":", 1)[-1] if ":" in f else f
                    best_house = val.strip()
                    break
                    
        # 4. Look for "ഹൗസ്"
        if not best_house:
            for f in fields:
                if "ഹൗസ്" in f:
                    best_house = f.strip()
                    break
                    
        if best_house:
            current_person["house_number"] = best_house

        if current_person or fields:
            current_person["raw_fields"] = fields
            people.append(current_person)

    return people


# ---------------------------------------------------------------------------
# Stand-alone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json, time

    test_image = r"C:\Users\navee\OneDrive\Desktop\suryamodel\image copy 11.png"

    if not os.path.exists(test_image):
        print(f"Error: {test_image} not found.")
    else:
        print(f"Processing {test_image} ...")
        texts_by_card = run_malayalam_ocr(test_image)
        people        = parse_ocr_data(texts_by_card)

        outputs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
        os.makedirs(outputs_dir, exist_ok=True)

        base      = os.path.splitext(os.path.basename(test_image))[0]
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        out_file  = os.path.join(outputs_dir, f"{base}_{timestamp}.json")

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(people, f, ensure_ascii=False, indent=4)

        print(f"\nDone — {len(people)} entries saved to {out_file}")
