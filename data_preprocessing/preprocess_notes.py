#!/usr/bin/env python3
"""
Preprocess MIMIC-IV discharge notes locally.
Extracts sections and saves processed notes to JSON files.
"""

import gzip
import csv
import json
import os
from pathlib import Path
from src.sectionizer import DischargeNoteSectionizer

def preprocess_notes(num_notes: int = 3, output_dir: str = "processed_notes"):
    """
    Preprocess discharge notes from MIMIC-IV dataset.
    
    Args:
        num_notes: Number of notes to process
        output_dir: Directory to save processed notes
    """
    file_path = 'mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/discharge.csv.gz'
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("PREPROCESSING MIMIC-IV DISCHARGE NOTES")
    print("=" * 80)
    print(f"\nProcessing {num_notes} notes...")
    print(f"Output directory: {output_dir}\n")
    
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
            
            # Extract sections
            sections = DischargeNoteSectionizer.extract_sections(raw_text)
            
            # Clean sections
            for key in sections:
                sections[key] = DischargeNoteSectionizer.clean_section_text(sections[key])
            
            # Create processed note structure
            processed_note = {
                "note_id": note_id,
                "subject_id": subject_id,
                "hadm_id": hadm_id,
                "note_type": note_type,
                "charttime": charttime,
                "storetime": storetime,
                "raw_text": raw_text,
                "sections": sections,
                "section_summary": {
                    section_name: {
                        "length": len(section_text),
                        "has_content": bool(section_text)
                    }
                    for section_name, section_text in sections.items()
                }
            }
            
            processed_notes.append(processed_note)
            
            # Save individual note
            note_file = output_path / f"{note_id}.json"
            with open(note_file, 'w', encoding='utf-8') as out:
                json.dump(processed_note, out, indent=2, ensure_ascii=False)
            
            print(f"\nExtracted sections:")
            found_sections = [name for name, text in sections.items() if text]
            for section_name in found_sections:
                length = len(sections[section_name])
                print(f"  ✓ {section_name}: {length:,} characters")
            
            empty_sections = [name for name, text in sections.items() if not text]
            if empty_sections:
                print(f"  - Empty: {', '.join(empty_sections)}")
            
            print(f"  Saved to: {note_file}")
    
    # Save combined file
    combined_file = output_path / "all_processed_notes.json"
    with open(combined_file, 'w', encoding='utf-8') as out:
        json.dump(processed_notes, out, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print("PREPROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"\nProcessed {len(processed_notes)} notes")
    print(f"Individual files saved in: {output_dir}/")
    print(f"Combined file saved: {combined_file}")
    
    return processed_notes

def display_processed_note(note_data: dict, note_index: int):
    """Display a processed note in a readable format."""
    print(f"\n{'='*80}")
    print(f"PROCESSED NOTE {note_index + 1}")
    print(f"{'='*80}")
    print(f"Note ID: {note_data['note_id']}")
    print(f"Subject ID: {note_data['subject_id']}")
    print(f"HADM ID: {note_data['hadm_id']}")
    print(f"Chart Time: {note_data['charttime']}")
    print(f"\nSection Summary:")
    for section_name, summary in note_data['section_summary'].items():
        status = "✓" if summary['has_content'] else "✗"
        print(f"  {status} {section_name}: {summary['length']:,} chars")
    
    print(f"\n{'='*80}")
    print("EXTRACTED SECTIONS:")
    print(f"{'='*80}")
    
    for section_name, section_text in note_data['sections'].items():
        if section_text:
            print(f"\n[{section_name}]")
            print("-" * 80)
            # Show first 400 characters
            preview = section_text[:400]
            if len(section_text) > 400:
                preview += "..."
            print(preview)
            print("-" * 80)

if __name__ == "__main__":
    # Process 10 notes
    processed_notes = preprocess_notes(num_notes=10)
    
    # Display processed notes
    print("\n\n" + "=" * 80)
    print("PROCESSED NOTES PREVIEW")
    print("=" * 80)
    
    for idx, note in enumerate(processed_notes):
        display_processed_note(note, idx)
        if idx < len(processed_notes) - 1:
            print("\n")

