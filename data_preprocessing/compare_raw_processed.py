#!/usr/bin/env python3
"""
Compare raw and processed notes to check for data loss.
Verifies that all data from raw notes is preserved in processed notes.
"""

import json
import os
from pathlib import Path
from typing import Dict, List

def compare_raw_processed():
    """Compare raw and processed notes for all 10 notes."""
    
    raw_dir = Path("raw_notes")
    processed_dir = Path("processed_notes")
    
    print("=" * 80)
    print("COMPARING RAW vs PROCESSED NOTES")
    print("=" * 80)
    print("\nChecking for data loss during preprocessing...\n")
    
    # Get all note IDs
    raw_files = sorted(raw_dir.glob("*.txt"))
    processed_files = sorted([f for f in processed_dir.glob("*.json") 
                             if f.name != "all_processed_notes.json"])
    
    if len(raw_files) != len(processed_files):
        print(f"⚠️  WARNING: Mismatch in file counts!")
        print(f"   Raw files: {len(raw_files)}")
        print(f"   Processed files: {len(processed_files)}")
        return
    
    print(f"Comparing {len(raw_files)} notes...\n")
    
    results = []
    
    for raw_file in raw_files:
        note_id = raw_file.stem
        
        # Read raw note
        with open(raw_file, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        
        # Read processed note
        processed_file = processed_dir / f"{note_id}.json"
        if not processed_file.exists():
            print(f"⚠️  {note_id}: Processed file not found!")
            continue
        
        with open(processed_file, 'r', encoding='utf-8') as f:
            processed_data = json.load(f)
        
        # Compare raw_text in processed with raw file
        processed_raw_text = processed_data.get('raw_text', '')
        sections = processed_data.get('sections', {})
        
        # Check if raw_text matches
        raw_match = (raw_text.strip() == processed_raw_text.strip())
        
        # Calculate section coverage
        all_sections_text = "\n".join([v for v in sections.values() if v])
        total_section_length = sum(len(v) for v in sections.values() if v)
        raw_length = len(raw_text)
        
        # Check if all sections are subsets of raw text
        sections_valid = True
        missing_sections = []
        
        for section_name, section_text in sections.items():
            if section_text:
                # Check if section text appears in raw text (allowing for some formatting differences)
                section_cleaned = section_text.strip().replace('\n\n', '\n')
                raw_cleaned = raw_text.strip().replace('\n\n', '\n')
                
                # Check if key parts of section are in raw text
                if len(section_text) > 50:
                    # Take first 50 chars of section
                    section_sample = section_text[:50].strip()
                    if section_sample not in raw_text:
                        sections_valid = False
                        missing_sections.append(section_name)
        
        # Calculate coverage percentage
        coverage_pct = (total_section_length / raw_length * 100) if raw_length > 0 else 0
        
        result = {
            'note_id': note_id,
            'raw_length': raw_length,
            'processed_raw_length': len(processed_raw_text),
            'raw_match': raw_match,
            'total_section_length': total_section_length,
            'coverage_pct': coverage_pct,
            'sections_valid': sections_valid,
            'missing_sections': missing_sections,
            'sections_found': [k for k, v in sections.items() if v],
            'sections_empty': [k for k, v in sections.items() if not v]
        }
        
        results.append(result)
    
    # Print detailed results
    print("=" * 80)
    print("DETAILED COMPARISON RESULTS")
    print("=" * 80)
    
    all_raw_match = True
    all_sections_valid = True
    total_coverage = 0
    
    for result in results:
        print(f"\n{'='*80}")
        print(f"Note ID: {result['note_id']}")
        print(f"{'='*80}")
        
        # Raw text comparison
        if result['raw_match']:
            print(f"✓ Raw text: MATCH ({result['raw_length']:,} chars)")
        else:
            print(f"⚠️  Raw text: MISMATCH!")
            print(f"   Raw file: {result['raw_length']:,} chars")
            print(f"   Processed raw_text: {result['processed_raw_length']:,} chars")
            all_raw_match = False
        
        # Section coverage
        print(f"\nSection Coverage:")
        print(f"  Raw text length: {result['raw_length']:,} chars")
        print(f"  Total section length: {result['total_section_length']:,} chars")
        print(f"  Coverage: {result['coverage_pct']:.1f}%")
        
        # Sections found
        print(f"\nSections Extracted:")
        for section in result['sections_found']:
            section_len = len(sections.get(section, ''))
            print(f"  ✓ {section}: {section_len:,} chars")
        
        if result['sections_empty']:
            print(f"\nEmpty Sections:")
            for section in result['sections_empty']:
                print(f"  - {section}")
        
        # Validation
        if result['sections_valid']:
            print(f"\n✓ All sections validated (found in raw text)")
        else:
            print(f"\n⚠️  Some sections not found in raw text:")
            for section in result['missing_sections']:
                print(f"   - {section}")
            all_sections_valid = False
        
        total_coverage += result['coverage_pct']
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    avg_coverage = total_coverage / len(results) if results else 0
    
    print(f"\nTotal Notes Compared: {len(results)}")
    print(f"\nRaw Text Preservation:")
    if all_raw_match:
        print(f"  ✓ All raw texts match perfectly")
    else:
        print(f"  ⚠️  Some raw texts have mismatches")
    
    print(f"\nSection Extraction:")
    if all_sections_valid:
        print(f"  ✓ All extracted sections validated")
    else:
        print(f"  ⚠️  Some sections not found in raw text")
    
    print(f"\nAverage Coverage: {avg_coverage:.1f}%")
    print(f"  (Percentage of raw text captured in sections)")
    
    # Data loss analysis
    print(f"\n{'='*80}")
    print("DATA LOSS ANALYSIS")
    print(f"{'='*80}")
    
    if all_raw_match and all_sections_valid:
        print("\n✓ NO DATA LOSS DETECTED")
        print("  - All raw text is preserved in processed files")
        print("  - All extracted sections are validated")
        print("  - Note: Some text may not be in sections (normal - not all text fits into predefined sections)")
    else:
        print("\n⚠️  POTENTIAL ISSUES DETECTED:")
        if not all_raw_match:
            print("  - Raw text mismatch between files")
        if not all_sections_valid:
            print("  - Some sections not found in raw text")
    
    print(f"\nNote: Coverage < 100% is expected because:")
    print("  - Some text doesn't fit into predefined sections")
    print("  - Headers, metadata, and formatting are excluded")
    print("  - Only relevant clinical sections are extracted")

if __name__ == "__main__":
    compare_raw_processed()

