#!/usr/bin/env python3
"""
Process multiple patients' data from all 3 files.
Each patient is saved in a separate file: patient_data/patient_{subject_id}.json
"""

from process_single_patient import process_single_patient
import sys
import gzip
import csv


def find_patients_with_both_notes(num_patients: int = 10):
    """Find patients that have both discharge and radiology notes."""
    print("Finding patients with both discharge and radiology notes...")
    
    # Get discharge note subject IDs
    discharge_subjects = set()
    discharge_file = 'mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/discharge.csv.gz'
    with gzip.open(discharge_file, 'rt') as f:
        reader = csv.DictReader(f)
        for row in reader:
            discharge_subjects.add(row['subject_id'])
            if len(discharge_subjects) >= 1000:  # Sample first 1000 for speed
                break
    
    # Get radiology note subject IDs
    radiology_subjects = set()
    radiology_file = 'mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/radiology.csv.gz'
    with gzip.open(radiology_file, 'rt') as f:
        reader = csv.DictReader(f)
        for row in reader:
            radiology_subjects.add(row['subject_id'])
            if len(radiology_subjects) >= 1000:  # Sample first 1000 for speed
                break
    
    # Get patients with both
    patients_with_both = sorted(set(discharge_subjects) & set(radiology_subjects))
    
    print(f"Found {len(patients_with_both)} patients with both note types")
    return patients_with_both[:num_patients]


def process_multiple_patients(num_patients: int = 10):
    """
    Process multiple patients, each saved in a separate file.
    
    Args:
        num_patients: Number of patients to process
    """
    print("=" * 80)
    print(f"PROCESSING {num_patients} PATIENTS")
    print("=" * 80)
    print("Each patient will be saved in a separate file: patient_data/patient_{subject_id}.json\n")
    
    # Find patients
    patient_ids = find_patients_with_both_notes(num_patients)
    
    if not patient_ids:
        print("No patients found with both note types")
        return
    
    processed_count = 0
    failed_count = 0
    
    for idx, subject_id in enumerate(patient_ids, 1):
        try:
            print(f"\n{'='*80}")
            print(f"Processing Patient {idx}/{num_patients}: {subject_id}")
            print(f"{'='*80}")
            
            result = process_single_patient(subject_id)
            
            if result:
                processed_count += 1
                print(f"  ✓ Successfully saved: patient_data/patient_{subject_id}.json")
            else:
                failed_count += 1
                print(f"  ✗ Failed to process patient {subject_id}")
        except Exception as e:
            print(f"  ⚠️  Error processing patient {subject_id}: {e}")
            failed_count += 1
    
    print(f"\n{'='*80}")
    print("BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"\nProcessed: {processed_count} patients")
    print(f"Failed: {failed_count} patients")
    print(f"Total: {processed_count + failed_count} patients")
    print(f"\nEach patient saved in separate file:")
    print(f"  patient_data/patient_{{subject_id}}.json")


if __name__ == "__main__":
    num_patients = 10
    if len(sys.argv) > 1:
        num_patients = int(sys.argv[1])
    
    process_multiple_patients(num_patients)

