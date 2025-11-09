#!/usr/bin/env python3
"""
Combine data from discharge, radiology, and radiology_detail files by patient.
Process and clean the data, then store combined patient records.
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


def load_radiology_details():
    """Load radiology detail metadata into a dictionary."""
    print("Loading radiology detail metadata...")
    details = defaultdict(dict)
    
    file_path = 'mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/radiology_detail.csv.gz'
    with gzip.open(file_path, 'rt') as f:
        reader = csv.DictReader(f)
        for row in reader:
            note_id = row['note_id']
            field_name = row['field_name']
            field_value = row['field_value']
            details[note_id][field_name] = field_value
    
    print(f"  Loaded metadata for {len(details)} radiology notes")
    return details


def combine_patient_data(output_dir: str = "combined_patient_data", 
                        num_patients: int = 5):
    """
    Combine discharge and radiology notes by patient (subject_id).
    
    Args:
        output_dir: Directory to save combined patient data
        num_patients: Number of patients to process
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("COMBINING PATIENT DATA FROM ALL FILES")
    print("=" * 80)
    
    # Load radiology details
    radiology_details = load_radiology_details()
    
    # Load discharge notes
    print("\nLoading discharge notes...")
    discharge_file = 'mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/discharge.csv.gz'
    discharge_notes = defaultdict(list)
    
    with gzip.open(discharge_file, 'rt') as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject_id = row['subject_id']
            discharge_notes[subject_id].append(row)
    
    print(f"  Loaded {sum(len(notes) for notes in discharge_notes.values())} discharge notes for {len(discharge_notes)} patients")
    
    # Load radiology notes
    print("\nLoading radiology notes...")
    radiology_file = 'mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/radiology.csv.gz'
    radiology_notes = defaultdict(list)
    
    with gzip.open(radiology_file, 'rt') as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject_id = row['subject_id']
            radiology_notes[subject_id].append(row)
    
    print(f"  Loaded {sum(len(notes) for notes in radiology_notes.values())} radiology notes for {len(radiology_notes)} patients")
    
    # Get patients that have both discharge and radiology notes
    patients_with_both = set(discharge_notes.keys()) & set(radiology_notes.keys())
    print(f"\nPatients with both discharge and radiology notes: {len(patients_with_both)}")
    
    # Process patients
    processed_patients = []
    patient_count = 0
    
    for subject_id in sorted(patients_with_both):
        if patient_count >= num_patients:
            break
        
        patient_count += 1
        print(f"\n{'='*80}")
        print(f"Processing Patient {patient_count}/{num_patients}: Subject ID {subject_id}")
        print(f"{'='*80}")
        
        # Get patient's notes
        patient_discharge_notes = discharge_notes[subject_id]
        patient_radiology_notes = radiology_notes[subject_id]
        
        print(f"  Discharge notes: {len(patient_discharge_notes)}")
        print(f"  Radiology notes: {len(patient_radiology_notes)}")
        
        # Process discharge notes
        processed_discharge = []
        for note in patient_discharge_notes:
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
        
        # Process radiology notes
        processed_radiology = []
        for note in patient_radiology_notes:
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
        
        # Create combined patient record
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
        
        # Save individual patient file
        patient_file = output_path / f"patient_{subject_id}.json"
        with open(patient_file, 'w', encoding='utf-8') as f:
            json.dump(patient_record, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved: {patient_file}")
        processed_patients.append(patient_record)
    
    # Save combined file
    combined_file = output_path / "all_combined_patients.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(processed_patients, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print("COMBINING COMPLETE")
    print(f"{'='*80}")
    print(f"\nProcessed {len(processed_patients)} patients")
    print(f"Output directory: {output_dir}/")
    print(f"Combined file: {combined_file}")
    
    return processed_patients


if __name__ == "__main__":
    # Combine data for 5 patients
    combined_data = combine_patient_data(num_patients=5)

