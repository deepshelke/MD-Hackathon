#!/usr/bin/env python3
"""
Process and upload notes for 10,000 patients with single hadm_id.
Only processes patients with exactly one hadm_id (single admission).
"""
import os
import json
import gzip
import csv
import time
import logging
from pathlib import Path
from collections import defaultdict
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv
from src.firestore_client import FirestoreClient
from data_preprocessing.preprocess_discharge_notes import preprocess_discharge_notes

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Firestore limits
MAX_WRITES_PER_DAY = 20000
BATCH_SIZE = 50  # Smaller batches to avoid getting banned
DELAY_BETWEEN_BATCHES = 4  # seconds


def find_single_hadm_patients(raw_dataset_path: str, max_patients: int = 2000) -> List[str]:
    """
    Find patients with exactly one hadm_id.
    
    Args:
        raw_dataset_path: Path to raw discharge CSV file
        max_patients: Maximum number of patients to return
    
    Returns:
        List of patient subject_ids with single hadm_id
    """
    print("="*80)
    print("FINDING PATIENTS WITH SINGLE HADM_ID")
    print("="*80)
    logger.info("="*80)
    logger.info("FINDING PATIENTS WITH SINGLE HADM_ID")
    logger.info("="*80)
    
    discharge_file = Path(raw_dataset_path)
    if not discharge_file.exists():
        error_msg = f"Raw dataset not found: {raw_dataset_path}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    print(f"\n📊 Analyzing patients...")
    logger.info("Analyzing patients...")
    
    # Count hadm_ids per patient
    patient_hadm_ids = defaultdict(set)
    patient_notes = defaultdict(list)
    
    with gzip.open(discharge_file, 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject_id = row.get('subject_id', '').strip()
            hadm_id = row.get('hadm_id', '').strip()
            note_id = row.get('note_id', '').strip()
            
            if subject_id and hadm_id and note_id:
                patient_hadm_ids[subject_id].add(hadm_id)
                patient_notes[subject_id].append({
                    'note_id': note_id,
                    'hadm_id': hadm_id,
                    'subject_id': subject_id
                })
            
            if len(patient_hadm_ids) % 50000 == 0:
                msg = f"Processed {len(patient_hadm_ids):,} patients..."
                print(f"   {msg}")
                logger.info(msg)
    
    print(f"\n📊 Results:")
    logger.info("Results:")
    total_patients = len(patient_hadm_ids)
    print(f"   Total patients: {total_patients:,}")
    logger.info(f"Total patients: {total_patients:,}")
    
    # Find patients with single hadm_id
    single_hadm_patients = []
    for subject_id, hadm_ids in patient_hadm_ids.items():
        if len(hadm_ids) == 1:
            single_hadm_patients.append(subject_id)
    
    single_count = len(single_hadm_patients)
    multiple_count = total_patients - single_count
    
    print(f"   Patients with single hadm_id: {single_count:,}")
    print(f"   Patients with multiple hadm_ids: {multiple_count:,}")
    logger.info(f"Patients with single hadm_id: {single_count:,}")
    logger.info(f"Patients with multiple hadm_ids: {multiple_count:,}")
    
    # Select first max_patients
    selected_patients = single_hadm_patients[:max_patients]
    
    # Count notes for selected patients
    notes_count = sum(len(patient_notes[pid]) for pid in selected_patients)
    avg_notes = notes_count / len(selected_patients) if selected_patients else 0
    
    print(f"\n📊 Selected {len(selected_patients):,} patients:")
    print(f"   Total notes: {notes_count:,}")
    print(f"   Average notes per patient: {avg_notes:.2f}")
    logger.info(f"Selected {len(selected_patients):,} patients")
    logger.info(f"Total notes: {notes_count:,}")
    logger.info(f"Average notes per patient: {avg_notes:.2f}")
    
    # Estimate time
    days_needed = notes_count / MAX_WRITES_PER_DAY
    print(f"\n⏱️  Time estimate:")
    print(f"   Notes to process: {notes_count:,}")
    print(f"   At 20,000 writes/day: {days_needed:.1f} days")
    logger.info(f"Time estimate: {days_needed:.1f} days at {MAX_WRITES_PER_DAY:,} writes/day")
    
    return selected_patients


def load_processed_notes_for_patient(subject_id: str, processed_dir: str = "processed_files") -> List[Dict]:
    """
    Load processed notes for a patient from local files.
    
    Args:
        subject_id: Patient subject_id
        processed_dir: Directory containing processed JSON files
    
    Returns:
        List of processed note dictionaries
    """
    processed_path = Path(processed_dir)
    if not processed_path.exists():
        return []
    
    processed_notes = []
    json_files = processed_path.glob("*.json")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                note = json.load(f)
                if note.get('subject_id', '') == subject_id:
                    processed_notes.append(note)
        except Exception as e:
            continue
    
    return processed_notes


def process_and_upload_18k_patients(raw_dataset_path: str = "raw_dataset/mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/discharge.csv.gz",
                                    collection_name: str = "discharge_notes",
                                    max_patients: int = 2000,
                                    credentials_path: str = None):
    """
    Process and upload notes for 2k patients with single hadm_id.
    
    Args:
        raw_dataset_path: Path to raw discharge CSV file
        collection_name: Firestore collection name
        max_patients: Maximum number of patients to process
        credentials_path: Path to Firebase credentials (uses env var if None)
    """
    print("="*80)
    print("PROCESSING AND UPLOADING 2K PATIENTS WITH SINGLE HADM_ID")
    print("="*80)
    logger.info("="*80)
    logger.info("PROCESSING AND UPLOADING 2K PATIENTS WITH SINGLE HADM_ID")
    logger.info("="*80)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Firestore client
    if credentials_path is None:
        credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    
    cred_msg = credentials_path or 'Using environment variables'
    print(f"\nCredentials: {cred_msg}")
    logger.info(f"Credentials: {cred_msg}")
    
    logger.info("Initializing Firestore client...")
    client = FirestoreClient(credentials_path)
    logger.info("Firestore client initialized")
    
    # Step 1: Find patients with single hadm_id
    print(f"\n{'='*80}")
    print("STEP 1: FINDING PATIENTS WITH SINGLE HADM_ID")
    print(f"{'='*80}")
    logger.info("="*80)
    logger.info("STEP 1: FINDING PATIENTS WITH SINGLE HADM_ID")
    logger.info("="*80)
    
    selected_patients = find_single_hadm_patients(raw_dataset_path, max_patients)
    
    if not selected_patients:
        error_msg = "No patients found with single hadm_id"
        print(f"\n⚠️  {error_msg}")
        logger.warning(error_msg)
        return
    
    # Step 2: Process and upload notes
    print(f"\n{'='*80}")
    print("STEP 2: PROCESSING AND UPLOADING NOTES")
    print(f"{'='*80}")
    logger.info("="*80)
    logger.info("STEP 2: PROCESSING AND UPLOADING NOTES")
    logger.info("="*80)
    
    all_processed_notes = []
    results = {'success': 0, 'skipped': 0, 'failed': 0, 'total_patients': 0, 'total_notes': 0}
    
    start_time = time.time()
    logger.info(f"Starting processing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Total patients to process: {len(selected_patients):,}")
    
    for idx, subject_id in enumerate(selected_patients, 1):
        print(f"\n{'='*80}")
        print(f"Processing Patient {idx}/{len(selected_patients)}: {subject_id}")
        print(f"{'='*80}")
        logger.info("="*80)
        logger.info(f"Processing Patient {idx}/{len(selected_patients)}: {subject_id}")
        logger.info("="*80)
        
        try:
            # Process patient's notes using preprocess_discharge_notes
            print(f"   🔄 Processing notes for patient {subject_id}...")
            logger.info(f"Processing notes for patient {subject_id}...")
            
            processed_files = preprocess_discharge_notes(
                subject_id=subject_id,
                raw_dataset_path=raw_dataset_path,
                output_dir="processed_files"
            )
            
            if not processed_files:
                msg = f"No notes found for patient {subject_id}"
                print(f"   ⚠️  {msg}")
                logger.warning(msg)
                results['failed'] += 1
                continue
            
            logger.info(f"Processed {len(processed_files)} files for patient {subject_id}")
            
            # Load processed notes from files
            processed_notes = load_processed_notes_for_patient(subject_id, "processed_files")
            
            if not processed_notes:
                msg = f"No processed notes found for patient {subject_id}"
                print(f"   ⚠️  {msg}")
                logger.warning(msg)
                results['failed'] += 1
                continue
            
            print(f"   ✅ Processed {len(processed_notes)} notes")
            logger.info(f"Processed {len(processed_notes)} notes for patient {subject_id}")
            results['total_notes'] += len(processed_notes)
            
            # Check which notes are already uploaded
            logger.info(f"Checking which notes are already uploaded for patient {subject_id}...")
            notes_to_upload = []
            for note in processed_notes:
                note_id = note.get('note_id', '')
                hadm_id = note.get('hadm_id', '')
                if note_id and hadm_id:
                    document_id = f"{note_id}_{hadm_id}"
                    if client.document_exists(document_id, collection_name):
                        results['skipped'] += 1
                    else:
                        notes_to_upload.append(note)
            
            logger.info(f"Notes to upload: {len(notes_to_upload)}, Already uploaded: {results['skipped']}")
            
            if notes_to_upload:
                print(f"   📤 Uploading {len(notes_to_upload)} notes...")
                logger.info(f"Uploading {len(notes_to_upload)} notes to Firestore...")
                
                # Upload in batches
                total_batches = (len(notes_to_upload) + BATCH_SIZE - 1) // BATCH_SIZE
                for i in range(0, len(notes_to_upload), BATCH_SIZE):
                    batch = notes_to_upload[i:i + BATCH_SIZE]
                    batch_num = (i // BATCH_SIZE) + 1
                    
                    logger.info(f"Uploading batch {batch_num}/{total_batches} ({len(batch)} notes)...")
                    
                    try:
                        batch_results = client.upload_notes_batch(
                            batch,
                            collection_name=collection_name,
                            skip_if_exists=True,
                            batch_size=BATCH_SIZE
                        )
                        
                        results['success'] += batch_results['success']
                        results['skipped'] += batch_results['skipped']
                        results['failed'] += batch_results['failed']
                        
                        msg = f"Batch {batch_num}: Success={batch_results['success']}, Skipped={batch_results['skipped']}, Failed={batch_results['failed']}"
                        print(f"      ✅ Success: {batch_results['success']}, ⏭️  Skipped: {batch_results['skipped']}, ❌ Failed: {batch_results['failed']}")
                        logger.info(msg)
                        
                        # Delay between batches
                        if i + BATCH_SIZE < len(notes_to_upload):
                            logger.info(f"Waiting {DELAY_BETWEEN_BATCHES} seconds before next batch...")
                            time.sleep(DELAY_BETWEEN_BATCHES)
                    
                    except Exception as e:
                        error_msg = f"Error uploading batch {batch_num}: {e}"
                        print(f"      ❌ {error_msg}")
                        logger.error(error_msg, exc_info=True)
                        results['failed'] += len(batch)
            else:
                msg = f"All notes already uploaded for patient {subject_id}"
                print(f"   ✅ {msg}")
                logger.info(msg)
            
            results['total_patients'] += 1
            
            # Progress update
            elapsed_time = time.time() - start_time
            progress = (idx / len(selected_patients) * 100)
            
            # Calculate estimated remaining time
            # Use average of last 10 patients for better estimate (avoid early inflation)
            if idx > 10:
                # Use last 10 patients for average
                recent_avg = elapsed_time / idx  # Overall average
                # More realistic: assume 2-4 seconds per patient for processing + upload
                realistic_avg = max(2.0, min(4.0, recent_avg))  # Between 2-4 seconds
            else:
                # For first few patients, use realistic estimate
                realistic_avg = 3.0  # 3 seconds per patient average
            
            remaining_patients = len(selected_patients) - idx
            estimated_remaining = remaining_patients * realistic_avg
            
            # Also calculate based on notes (if we know the rate)
            if results['total_notes'] > 0 and elapsed_time > 0:
                notes_per_minute = results['total_notes'] / (elapsed_time / 60)
                remaining_notes = max_patients - results['total_notes']  # Approximate
                if notes_per_minute > 0 and remaining_notes > 0:
                    estimated_by_notes = remaining_notes / notes_per_minute
                    # Use the more realistic estimate (notes-based is usually better)
                    estimated_remaining = min(estimated_remaining / 60, estimated_by_notes)
                else:
                    estimated_remaining = estimated_remaining / 60
            else:
                estimated_remaining = estimated_remaining / 60
            
            # Cap at reasonable maximum (e.g., 24 hours)
            estimated_remaining = min(estimated_remaining, 24 * 60)  # Cap at 24 hours
            
            progress_msg = f"Progress: {progress:.1f}% | Elapsed: {elapsed_time/60:.1f} min | Remaining: {estimated_remaining:.1f} min | Success: {results['success']} | Skipped: {results['skipped']} | Failed: {results['failed']}"
            print(f"\n   Progress: {progress:.1f}%")
            print(f"   Elapsed: {elapsed_time/60:.1f} minutes")
            print(f"   Estimated remaining: {estimated_remaining:.1f} minutes ({estimated_remaining/60:.1f} hours)")
            print(f"   Success: {results['success']} | Skipped: {results['skipped']} | Failed: {results['failed']}")
            logger.info(progress_msg)
            
        except Exception as e:
            error_msg = f"Error processing patient {subject_id}: {e}"
            print(f"   ❌ {error_msg}")
            logger.error(error_msg, exc_info=True)
            results['failed'] += 1
            continue
    
    # Final summary
    total_time = time.time() - start_time
    print(f"\n{'='*80}")
    print("PROCESSING COMPLETE")
    print(f"{'='*80}")
    logger.info("="*80)
    logger.info("PROCESSING COMPLETE")
    logger.info("="*80)
    logger.info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    summary_msg = f"""
    Successfully processed: {results['success']} notes
    Skipped (already exists): {results['skipped']} notes
    Failed: {results['failed']} notes
    Total patients: {results['total_patients']}
    Total notes: {results['total_notes']}
    Total time: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)
    Average rate: {results['total_notes'] / (total_time/60):.1f} notes/minute
    """
    
    print(f"\n✅ Successfully processed: {results['success']} notes")
    print(f"⏭️  Skipped (already exists): {results['skipped']} notes")
    print(f"❌ Failed: {results['failed']} notes")
    print(f"📊 Total patients: {results['total_patients']}")
    print(f"📊 Total notes: {results['total_notes']}")
    print(f"⏱️  Total time: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)")
    print(f"📈 Average rate: {results['total_notes'] / (total_time/60):.1f} notes/minute")
    logger.info(summary_msg)
    
    return results


if __name__ == "__main__":
    import sys
    
    print(f"\n🚀 Starting processing for 2k patients with single hadm_id...\n")
    
    try:
        results = process_and_upload_18k_patients(
            raw_dataset_path="raw_dataset/mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/discharge.csv.gz",
            collection_name="discharge_notes",
            max_patients=2000
        )
        
        if results:
            print(f"\n✅ Processing complete!")
            print(f"   Processed {results['total_patients']} patients")
            print(f"   Uploaded {results['success']} notes")
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Processing interrupted by user")
        print(f"   Progress has been saved. You can resume by running the script again.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

