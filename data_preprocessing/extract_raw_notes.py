#!/usr/bin/env python3
"""
Extract raw note text from processed notes and save to a new folder.
This allows comparison between raw and processed versions.
"""

import json
import os
from pathlib import Path

def extract_raw_notes(processed_dir: str = "processed_notes", output_dir: str = "raw_notes"):
    """
    Extract raw note text from processed JSON files and save as text files.
    
    Args:
        processed_dir: Directory containing processed note JSON files
        output_dir: Directory to save raw note text files
    """
    processed_path = Path(processed_dir)
    output_path = Path(output_dir)
    
    # Create output directory
    output_path.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("EXTRACTING RAW NOTES FROM PROCESSED FILES")
    print("=" * 80)
    print(f"\nInput directory: {processed_dir}")
    print(f"Output directory: {output_dir}\n")
    
    # Get all processed note files (excluding the combined file)
    note_files = sorted([f for f in processed_path.glob("*.json") if f.name != "all_processed_notes.json"])
    
    print(f"Found {len(note_files)} processed note files\n")
    
    extracted_count = 0
    
    for note_file in note_files:
        # Read processed note
        with open(note_file, 'r', encoding='utf-8') as f:
            note_data = json.load(f)
        
        note_id = note_data['note_id']
        raw_text = note_data['raw_text']
        
        # Save raw text to file
        raw_file = output_path / f"{note_id}.txt"
        with open(raw_file, 'w', encoding='utf-8') as f:
            f.write(raw_text)
        
        extracted_count += 1
        print(f"✓ Extracted: {note_id}")
        print(f"  Raw text length: {len(raw_text):,} characters")
        print(f"  Saved to: {raw_file}")
        print()
    
    print("=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\nExtracted {extracted_count} raw note files")
    print(f"Raw notes saved in: {output_dir}/")
    print(f"\nYou can now compare:")
    print(f"  - Raw notes: {output_dir}/{{note_id}}.txt")
    print(f"  - Processed notes: {processed_dir}/{{note_id}}.json")

if __name__ == "__main__":
    extract_raw_notes()

