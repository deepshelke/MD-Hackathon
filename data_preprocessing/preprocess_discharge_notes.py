#!/usr/bin/env python3
"""
Comprehensive preprocessing script for MIMIC-IV discharge notes.
Processes discharge notes from raw_dataset and saves to processed_files.

Features:
- Robust sectionizer that properly identifies section boundaries
- Data cleaning (removes \n, em dashes, __ dashes)
- Preserves all medical data
- Saves as noteid_hadm_id.json format
"""

import gzip
import csv
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import OrderedDict


class RobustDischargeNoteSectionizer:
    """
    Robust sectionizer that properly identifies section boundaries
    by finding ALL section headers first, then creating boundaries.
    """
    
    # All possible section headers in order of appearance
    # Include "Attending:" as a boundary marker (not a section we extract)
    SECTION_HEADERS = [
        'Allergies:',
        'Attending:',  # Boundary marker - stops Allergies section
        'Chief Complaint:',
        'History of Present Illness:',
        'Past Medical History:',
        'Social History:',
        'Family History:',
        'Physical Exam:',
        'Pertinent Results:',
        'Brief Hospital Course:',
        'Hospital Course:',
        'Discharge Medications:',
        'Medications on Admission:',
        'Discharge Diagnosis:',
        'Discharge Diagnoses:',
        'Discharge Instructions:',
        'Follow-up:',
        'Followup:',
        'Follow Up:',
        'Pending Tests:',
        'Diet:',
        'Activity:',
    ]
    
    # Standard section names we want to extract
    STANDARD_SECTIONS = {
        'Allergies': ['Allergies:'],
        'Chief Complaint': ['Chief Complaint:'],
        'History of Present Illness': ['History of Present Illness:'],
        'Past Medical History': ['Past Medical History:'],
        'Physical Exam': ['Physical Exam:'],
        'Pertinent Results': ['Pertinent Results:'],
        'Hospital Course': ['Brief Hospital Course:', 'Hospital Course:'],
        'Discharge Medications': ['Discharge Medications:'],
        'Discharge Diagnosis': ['Discharge Diagnosis:', 'Discharge Diagnoses:'],
        'Discharge Instructions': ['Discharge Instructions:'],
        'Follow-up': ['Follow-up:', 'Followup:', 'Follow Up:'],
        'Pending Tests': ['Pending Tests:'],
        'Diet/Activity': ['Diet:', 'Activity:'],
    }
    
    @staticmethod
    def extract_sections(note_text: str) -> Dict[str, str]:
        """
        Extract sections from discharge note by finding ALL section headers first,
        then creating proper boundaries.
        
        Args:
            note_text: Raw discharge note text
            
        Returns:
            Dictionary with section names as keys and section text as values
        """
        sections = {
            "Allergies": "",
            "Chief Complaint": "",
            "History of Present Illness": "",
            "Past Medical History": "",
            "Physical Exam": "",
            "Pertinent Results": "",
            "Hospital Course": "",
            "Discharge Medications": "",
            "Discharge Diagnosis": "",
            "Discharge Instructions": "",
            "Follow-up": "",
            "Pending Tests": "",
            "Diet/Activity": ""
        }
        
        # Find all section headers with their positions
        header_positions = []
        
        for header in RobustDischargeNoteSectionizer.SECTION_HEADERS:
            # Escape special characters in header
            pattern = re.escape(header)
            # Find all occurrences
            for match in re.finditer(pattern, note_text, re.IGNORECASE):
                header_positions.append((match.start(), match.end(), header))
        
        # Sort by position
        header_positions.sort(key=lambda x: x[0])
        
        # Map headers to standard section names
        header_to_section = {}
        for standard_name, headers in RobustDischargeNoteSectionizer.STANDARD_SECTIONS.items():
            for header in headers:
                header_to_section[header.lower()] = standard_name
        
        # Extract text for each section
        for i, (start, end, header) in enumerate(header_positions):
            # Find end position (next section or end of text)
            next_start = header_positions[i + 1][0] if i + 1 < len(header_positions) else len(note_text)
            
            # Extract section text (from after header to next section)
            section_text = note_text[end:next_start].strip()
            
            # Map header to standard section name
            standard_name = header_to_section.get(header.lower(), None)
            
            # Special handling for Allergies - stop at "Attending:" or next section
            if header.lower() == 'allergies:':
                # Stop at "Attending:" if present
                attending_match = re.search(r'Attending:', section_text, re.IGNORECASE)
                if attending_match:
                    section_text = section_text[:attending_match.start()].strip()
                # Also stop at next major section if it appears
                next_section_match = re.search(r'\n\s*(?:Chief Complaint|History of Present Illness|Past Medical History|Physical Exam|Hospital Course|Discharge)', 
                                              section_text, re.IGNORECASE)
                if next_section_match:
                    section_text = section_text[:next_section_match.start()].strip()
            
            if standard_name:
                # If section already has content, append (for multiple occurrences)
                if sections[standard_name]:
                    sections[standard_name] += "\n\n" + section_text
                else:
                    sections[standard_name] = section_text
        
        return sections
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean text by removing unwanted characters while preserving medical data.
        
        Removes:
        - \n (newlines) - replace with space
        - \r (carriage returns) - replace with space
        - em dashes (—) - replace with space
        - __ dashes (double underscores) - replace with space
        - ___ dashes (triple underscores) - replace with space
        
        Preserves:
        - All medical terms
        - All numbers
        - All dates
        - All punctuation (except above)
        - All medical abbreviations
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Replace newlines and carriage returns with space
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')
        
        # Remove em dashes (—) - Unicode character U+2014
        text = text.replace('—', ' ')
        text = text.replace('–', ' ')  # en dash U+2013
        
        # Remove multiple underscores (__ or ___)
        text = re.sub(r'_{2,}', ' ', text)
        
        # Remove excessive whitespace (multiple spaces)
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text


def preprocess_discharge_notes(
    subject_id: str,
    raw_dataset_path: str = "raw_dataset/mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/discharge.csv.gz",
    output_dir: str = "processed_files"
):
    """
    Preprocess discharge notes for a single patient.
    
    Args:
        subject_id: Patient subject_id to process
        raw_dataset_path: Path to raw discharge CSV file
        output_dir: Directory to save processed files
        
    Returns:
        List of processed note filenames
    """
    print("=" * 80)
    print("PREPROCESSING DISCHARGE NOTES")
    print("=" * 80)
    print(f"\nPatient: {subject_id}")
    print(f"Raw dataset: {raw_dataset_path}")
    print(f"Output directory: {output_dir}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Check if raw dataset exists
    raw_file = Path(raw_dataset_path)
    if not raw_file.exists():
        print(f"\n❌ Error: Raw dataset not found at {raw_file}")
        return []
    
    # Load discharge notes for this patient
    print(f"\n📖 Loading discharge notes for patient {subject_id}...")
    discharge_notes = []
    
    with gzip.open(raw_file, 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('subject_id', '') == subject_id:
                discharge_notes.append(row)
    
    if not discharge_notes:
        print(f"\n⚠️  No discharge notes found for patient {subject_id}")
        return []
    
    print(f"✅ Found {len(discharge_notes)} discharge notes")
    
    # Process each discharge note
    processed_files = []
    sectionizer = RobustDischargeNoteSectionizer()
    
    for idx, note in enumerate(discharge_notes, 1):
        note_id = note.get('note_id', '')
        hadm_id = note.get('hadm_id', '').strip()
        raw_text = note.get('text', '')
        
        print(f"\n{'=' * 80}")
        print(f"Processing Note {idx}/{len(discharge_notes)}: {note_id}")
        print(f"{'=' * 80}")
        print(f"  hadm_id: {hadm_id}")
        print(f"  Raw text length: {len(raw_text):,} characters")
        
        # Extract sections
        print(f"\n📝 Extracting sections...")
        sections = sectionizer.extract_sections(raw_text)
        
        # Show section sizes
        print(f"  Sections found:")
        for section_name, section_text in sections.items():
            if section_text:
                print(f"    - {section_name}: {len(section_text):,} chars")
        
        # Clean sections
        print(f"\n🧹 Cleaning sections...")
        cleaned_sections = {}
        for section_name, section_text in sections.items():
            cleaned_text = sectionizer.clean_text(section_text)
            cleaned_sections[section_name] = cleaned_text
            if section_text and cleaned_text:
                print(f"    - {section_name}: {len(section_text):,} → {len(cleaned_text):,} chars")
        
        # Create processed note structure
        processed_note = {
            "note_id": note_id,
            "subject_id": subject_id,
            "hadm_id": hadm_id,
            "note_type": note.get('note_type', 'DS'),
            "charttime": note.get('charttime', ''),
            "storetime": note.get('storetime', ''),
            "sections": cleaned_sections,
            "section_summary": {
                section_name: {
                    "length": len(section_text),
                    "has_content": bool(section_text)
                }
                for section_name, section_text in cleaned_sections.items()
            }
        }
        
        # Save as noteid_hadm_id.json
        filename = f"{note_id}_{hadm_id}.json"
        filepath = output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(processed_note, f, indent=2, ensure_ascii=False)
        
        processed_files.append(filename)
        print(f"\n✅ Saved: {filename}")
        print(f"   File: {filepath}")
        
        # Show summary
        total_chars = sum(len(v) for v in cleaned_sections.values())
        print(f"   Total processed text: {total_chars:,} characters")
    
    print(f"\n{'=' * 80}")
    print("PREPROCESSING COMPLETE")
    print(f"{'=' * 80}")
    print(f"\n✅ Processed {len(processed_files)} discharge notes")
    print(f"📁 Output directory: {output_path}")
    print(f"\nProcessed files:")
    for filename in processed_files:
        print(f"  - {filename}")
    
    return processed_files


if __name__ == "__main__":
    import sys
    
    # Default: process patient 10000032
    subject_id = "10000032"
    
    if len(sys.argv) > 1:
        subject_id = sys.argv[1]
    
    print(f"\n🚀 Starting preprocessing for patient {subject_id}...\n")
    
    processed_files = preprocess_discharge_notes(
        subject_id=subject_id,
        raw_dataset_path="raw_dataset/mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/discharge.csv.gz",
        output_dir="processed_files"
    )
    
    if processed_files:
        print(f"\n✅ Successfully processed {len(processed_files)} notes!")
    else:
        print(f"\n⚠️  No notes processed")

