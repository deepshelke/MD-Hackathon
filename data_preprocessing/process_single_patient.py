#!/usr/bin/env python3
"""
Process a single patient's data from all 3 files.
Fetches discharge notes, radiology notes, and radiology details for one patient.
Processes, cleans, and stores as a single file.
"""

import gzip
import csv
import json
import re
from pathlib import Path
from collections import defaultdict
from src.sectionizer import DischargeNoteSectionizer, RadiologyNoteSectionizer


def clean_text(text: str) -> str:
    """
    Clean text by removing unwanted characters.
    Removes: \n, em dashes (__), quotes ("), colons (:), semicolons (;)
    Keeps: full stops (.)
    """
    if not text:
        return ""
    
    # Remove newlines (replace with space)
    text = text.replace('\n', ' ')
    text = text.replace('\r', ' ')
    
    # Remove em dashes (___ or __)
    text = re.sub(r'_{2,}', '', text)
    
    # Remove quotes (both single and double)
    text = text.replace('"', '')
    text = text.replace("'", '')
    
    # Remove colons and semicolons
    text = text.replace(':', '')
    text = text.replace(';', '')
    
    # Clean up multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def process_single_patient(subject_id: str, output_dir: str = "patient_data"):
    """
    Process a single patient's data from all 3 files.
    
    Args:
        subject_id: Patient's subject_id
        output_dir: Directory to save processed patient file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print("=" * 80)
    print(f"PROCESSING PATIENT: {subject_id}")
    print("=" * 80)
    
    # Load radiology details
    print("\nLoading radiology detail metadata...")
    radiology_details = defaultdict(dict)
    radiology_detail_file = 'mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/radiology_detail.csv.gz'
    
    with gzip.open(radiology_detail_file, 'rt') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['subject_id'] == subject_id:
                note_id = row['note_id']
                field_name = row['field_name']
                field_value = row['field_value']
                radiology_details[note_id][field_name] = field_value
    
    print(f"  Loaded metadata for {len(radiology_details)} radiology notes")
    
    # Load discharge notes for this patient
    print("\nLoading discharge notes...")
    discharge_notes = []
    discharge_file = 'mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/discharge.csv.gz'
    
    with gzip.open(discharge_file, 'rt') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['subject_id'] == subject_id:
                discharge_notes.append(row)
    
    print(f"  Found {len(discharge_notes)} discharge notes")
    
    # Load radiology notes for this patient
    print("\nLoading radiology notes...")
    radiology_notes = []
    radiology_file = 'mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/radiology.csv.gz'
    
    with gzip.open(radiology_file, 'rt') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['subject_id'] == subject_id:
                radiology_notes.append(row)
    
    print(f"  Found {len(radiology_notes)} radiology notes")
    
    if not discharge_notes and not radiology_notes:
        print(f"\n⚠️  No notes found for patient {subject_id}")
        return None
    
    # Process discharge notes
    print("\nProcessing discharge notes...")
    processed_discharge = []
    for note in discharge_notes:
        raw_text = note['text']
        
        # Extract sections
        sections = DischargeNoteSectionizer.extract_sections(raw_text)
        for key in sections:
            sections[key] = DischargeNoteSectionizer.clean_section_text(sections[key])
            # Clean the text
            sections[key] = clean_text(sections[key])
        
        # Clean raw text
        cleaned_raw = clean_text(raw_text)
        
        processed_note = {
            "note_id": note['note_id'],
            "hadm_id": note['hadm_id'],
            "note_type": note['note_type'],
            "charttime": note['charttime'],
            "storetime": note['storetime'],
            "raw_text": cleaned_raw,
            "sections": sections
        }
        processed_discharge.append(processed_note)
        print(f"  ✓ Processed: {note['note_id']}")
    
    # Process radiology notes
    print("\nProcessing radiology notes...")
    processed_radiology = []
    for note in radiology_notes:
        note_id = note['note_id']
        raw_text = note['text']
        
        # Get radiology detail metadata
        metadata = radiology_details.get(note_id, {})
        
        # Extract sections
        sections = RadiologyNoteSectionizer.extract_sections(raw_text)
        for key in sections:
            sections[key] = RadiologyNoteSectionizer.clean_section_text(sections[key])
            # Clean the text
            sections[key] = clean_text(sections[key])
        
        # Clean raw text
        cleaned_raw = clean_text(raw_text)
        
        processed_note = {
            "note_id": note_id,
            "hadm_id": note['hadm_id'],
            "note_type": note['note_type'],
            "charttime": note['charttime'],
            "storetime": note['storetime'],
            "raw_text": cleaned_raw,
            "sections": sections,
            "metadata": {
                "exam_code": metadata.get('exam_code', ''),
                "exam_name": metadata.get('exam_name', ''),
                "cpt_code": metadata.get('cpt_code', '')
            }
        }
        processed_radiology.append(processed_note)
        print(f"  ✓ Processed: {note_id}")
    
    # Create patient record
    patient_record = {
        "subject_id": subject_id,
        "discharge_notes": processed_discharge,
        "radiology_notes": processed_radiology,
        "summary": {
            "total_discharge_notes": len(processed_discharge),
            "total_radiology_notes": len(processed_radiology),
            "total_notes": len(processed_discharge) + len(processed_radiology)
        }
    }
    
    # Save patient file
    patient_file = output_path / f"patient_{subject_id}.json"
    with open(patient_file, 'w', encoding='utf-8') as f:
        json.dump(patient_record, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print("PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"\nPatient: {subject_id}")
    print(f"  Discharge notes: {len(processed_discharge)}")
    print(f"  Radiology notes: {len(processed_radiology)}")
    print(f"  Total notes: {len(processed_discharge) + len(processed_radiology)}")
    print(f"\nSaved to: {patient_file}")
    
    return patient_record


if __name__ == "__main__":
    # Example: Process patient 10000032
    import sys
    
    if len(sys.argv) > 1:
        subject_id = sys.argv[1]
    else:
        subject_id = "10000032"  # Default patient
    
    process_single_patient(subject_id)

