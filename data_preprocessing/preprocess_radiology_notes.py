#!/usr/bin/env python3
"""
Preprocess MIMIC-IV radiology notes.
Extracts notes and saves both raw and processed versions.
"""

import gzip
import csv
import json
import os
from pathlib import Path
from src.sectionizer import RadiologyNoteSectionizer

def preprocess_radiology_notes(num_notes: int = 10, 
                               raw_dir: str = "radiology_raw",
                               processed_dir: str = "radiology_processed"):
    """
    Preprocess radiology notes from MIMIC-IV dataset.
    
    Args:
        num_notes: Number of notes to process
        raw_dir: Directory to save raw note text files
        processed_dir: Directory to save processed notes as JSON
    """
    file_path = 'mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/radiology.csv.gz'
    
    # Create output directories
    raw_path = Path(raw_dir)
    processed_path = Path(processed_dir)
    raw_path.mkdir(exist_ok=True)
    processed_path.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("PREPROCESSING MIMIC-IV RADIOLOGY NOTES")
    print("=" * 80)
    print(f"\nProcessing {num_notes} notes...")
    print(f"Raw notes directory: {raw_dir}/")
    print(f"Processed notes directory: {processed_dir}/\n")
    
    processed_notes = []
    
    with gzip.open(file_path, 'rt') as f:
        reader = csv.DictReader(f)
        
        for idx, row in enumerate(reader):
            if idx >= num_notes:
                break
            
            note_id = row['note_id']
            subject_id = row['subject_id']
            hadm_id = row['hadm_id']
            note_type = row['note_type']
            charttime = row['charttime']
            storetime = row['storetime']
            raw_text = row['text']
            
            print(f"\n{'='*80}")
            print(f"Processing Note {idx + 1}/{num_notes}: {note_id}")
            print(f"{'='*80}")
            print(f"Subject ID: {subject_id}")
            print(f"HADM ID: {hadm_id}")
            print(f"Note Type: {note_type}")
            print(f"Raw text length: {len(raw_text):,} characters")
            
            # Save raw text to file
            raw_file = raw_path / f"{note_id}.txt"
            with open(raw_file, 'w', encoding='utf-8') as f:
                f.write(raw_text)
            
            print(f"  ✓ Saved raw text: {raw_file}")
            
            # Extract sections using sectionizer
            sections = RadiologyNoteSectionizer.extract_sections(raw_text)
            
            # Clean sections
            for key in sections:
                sections[key] = RadiologyNoteSectionizer.clean_section_text(sections[key])
            
            # Create processed note structure
            processed_note = {
                "note_id": note_id,
                "subject_id": subject_id,
                "hadm_id": hadm_id,
                "note_type": note_type,
                "charttime": charttime,
                "storetime": storetime,
                "raw_text": raw_text,
                "text_length": len(raw_text),
                "sections": sections,
                "section_summary": {
                    section_name: {
                        "length": len(section_text),
                        "has_content": bool(section_text)
                    }
                    for section_name, section_text in sections.items()
                }
            }
            
            # Show extracted sections
            found_sections = [name for name, text in sections.items() if text]
            print(f"  Extracted sections: {len(found_sections)}")
            for section_name in found_sections:
                length = len(sections[section_name])
                print(f"    ✓ {section_name}: {length:,} characters")
            
            processed_notes.append(processed_note)
            
            # Save individual processed note
            processed_file = processed_path / f"{note_id}.json"
            with open(processed_file, 'w', encoding='utf-8') as out:
                json.dump(processed_note, out, indent=2, ensure_ascii=False)
            
            print(f"  ✓ Saved processed note: {processed_file}")
            
            # Show text preview
            print(f"\nText preview (first 300 chars):")
            print("-" * 80)
            print(raw_text[:300])
            if len(raw_text) > 300:
                print("...")
            print("-" * 80)
    
    # Save combined file
    combined_file = processed_path / "all_processed_radiology_notes.json"
    with open(combined_file, 'w', encoding='utf-8') as out:
        json.dump(processed_notes, out, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print("PREPROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"\nProcessed {len(processed_notes)} radiology notes")
    print(f"Raw notes saved in: {raw_dir}/")
    print(f"Processed notes saved in: {processed_dir}/")
    print(f"Combined file saved: {combined_file}")
    
    return processed_notes

if __name__ == "__main__":
    # Process 10 radiology notes
    processed_notes = preprocess_radiology_notes(num_notes=10)

