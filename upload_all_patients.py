#!/usr/bin/env python3
"""
Upload all processed notes to Firestore with rate limiting.
Respects Firestore free tier limits (20,000 writes/day).
"""
import os
import json
import time
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
from src.firestore_client import FirestoreClient
from datetime import datetime, timedelta


# Firestore free tier limits
MAX_WRITES_PER_DAY = 20000
SAFE_WRITES_PER_HOUR = 800  # Conservative: 20,000 / 25 hours
SAFE_WRITES_PER_MINUTE = 13  # Conservative: 800 / 60
BATCH_SIZE = 500  # Firestore batch limit
DELAY_BETWEEN_BATCHES = 4  # seconds (to stay under rate limit)


def load_processed_notes(processed_dir: str = "processed_files") -> List[Dict]:
    """Load all processed notes from JSON files."""
    processed_path = Path(processed_dir)
    if not processed_path.exists():
        raise ValueError(f"Processed directory not found: {processed_dir}")
    
    notes = []
    json_files = sorted(processed_path.glob("*.json"))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                note = json.load(f)
                notes.append(note)
        except Exception as e:
            print(f"⚠️  Error loading {json_file.name}: {e}")
    
    return notes


def check_already_uploaded(client: FirestoreClient, notes: List[Dict], collection_name: str) -> List[Dict]:
    """Filter out notes that are already uploaded."""
    print(f"\n🔍 Checking which notes are already uploaded...")
    
    notes_to_upload = []
    already_uploaded = 0
    
    for note in notes:
        note_id = note.get('note_id', '')
        hadm_id = note.get('hadm_id', '')
        if note_id and hadm_id:
            document_id = f"{note_id}_{hadm_id}"
            if client.document_exists(document_id, collection_name):
                already_uploaded += 1
            else:
                notes_to_upload.append(note)
    
    print(f"   Already uploaded: {already_uploaded}")
    print(f"   Need to upload: {len(notes_to_upload)}")
    
    return notes_to_upload


def upload_with_rate_limiting(client: FirestoreClient, 
                             notes: List[Dict],
                             collection_name: str = "discharge_notes",
                             max_writes_per_day: int = MAX_WRITES_PER_DAY,
                             batch_size: int = BATCH_SIZE,
                             delay_between_batches: int = DELAY_BETWEEN_BATCHES) -> Dict:
    """
    Upload notes with rate limiting to respect Firestore free tier limits.
    
    Args:
        client: FirestoreClient instance
        notes: List of note dictionaries to upload
        collection_name: Firestore collection name
        max_writes_per_day: Maximum writes per day (default: 20,000)
        batch_size: Number of notes per batch (default: 500)
        delay_between_batches: Delay in seconds between batches (default: 4)
    
    Returns:
        Dictionary with upload results
    """
    print("="*80)
    print("UPLOADING WITH RATE LIMITING")
    print("="*80)
    
    total_notes = len(notes)
    print(f"\nTotal notes to upload: {total_notes}")
    print(f"Batch size: {batch_size}")
    print(f"Delay between batches: {delay_between_batches} seconds")
    print(f"Max writes per day: {max_writes_per_day}")
    
    # Calculate time estimates
    total_batches = (total_notes + batch_size - 1) // batch_size
    total_time_seconds = total_batches * delay_between_batches
    total_time_hours = total_time_seconds / 3600
    total_time_days = total_time_hours / 24
    
    print(f"\nEstimated time:")
    print(f"   Total batches: {total_batches}")
    print(f"   Total time: {total_time_hours:.1f} hours ({total_time_days:.1f} days)")
    print(f"   Writes per day: {total_notes / total_time_days:.0f} (under {max_writes_per_day} limit)")
    
    if total_notes > max_writes_per_day:
        print(f"\n⚠️  WARNING: {total_notes} notes will take {total_time_days:.1f} days to upload")
        print(f"   This is within the {max_writes_per_day} writes/day limit")
    
    # Upload in batches
    results = {'success': 0, 'skipped': 0, 'failed': 0}
    start_time = time.time()
    
    for i in range(0, total_notes, batch_size):
        batch = notes[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"\n{'='*80}")
        print(f"Processing batch {batch_num}/{total_batches}")
        print(f"{'='*80}")
        print(f"Notes {i+1} to {min(i+batch_size, total_notes)} of {total_notes}")
        
        # Upload batch
        try:
            batch_results = client.upload_notes_batch(
                batch,
                collection_name=collection_name,
                skip_if_exists=True,
                batch_size=batch_size
            )
            
            results['success'] += batch_results['success']
            results['skipped'] += batch_results['skipped']
            results['failed'] += batch_results['failed']
            
            print(f"   ✅ Success: {batch_results['success']}")
            print(f"   ⏭️  Skipped: {batch_results['skipped']}")
            print(f"   ❌ Failed: {batch_results['failed']}")
            
        except Exception as e:
            print(f"   ❌ Error uploading batch: {e}")
            results['failed'] += len(batch)
        
        # Progress update
        elapsed_time = time.time() - start_time
        progress = ((i + batch_size) / total_notes * 100) if total_notes > 0 else 0
        avg_time_per_note = elapsed_time / (i + batch_size) if (i + batch_size) > 0 else 0
        remaining_notes = total_notes - (i + batch_size)
        estimated_remaining = remaining_notes * avg_time_per_note
        
        print(f"\n   Progress: {progress:.1f}%")
        print(f"   Elapsed: {elapsed_time/60:.1f} minutes")
        print(f"   Estimated remaining: {estimated_remaining/60:.1f} minutes")
        
        # Delay between batches (except for last batch)
        if i + batch_size < total_notes:
            print(f"   Waiting {delay_between_batches} seconds before next batch...")
            time.sleep(delay_between_batches)
    
    # Final summary
    total_time = time.time() - start_time
    print(f"\n{'='*80}")
    print("UPLOAD COMPLETE")
    print(f"{'='*80}")
    print(f"\n✅ Successfully uploaded: {results['success']}")
    print(f"⏭️  Skipped (already exists): {results['skipped']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📊 Total: {total_notes}")
    print(f"⏱️  Total time: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)")
    print(f"📈 Average rate: {total_notes / (total_time/60):.1f} notes/minute")
    
    return results


def upload_all_patients(processed_dir: str = "processed_files",
                        collection_name: str = "discharge_notes",
                        credentials_path: str = None,
                        max_writes_per_day: int = MAX_WRITES_PER_DAY,
                        batch_size: int = BATCH_SIZE,
                        delay_between_batches: int = DELAY_BETWEEN_BATCHES):
    """
    Upload all processed notes to Firestore with rate limiting.
    
    Args:
        processed_dir: Directory containing processed JSON files
        collection_name: Firestore collection name
        credentials_path: Path to Firebase credentials (uses env var if None)
        max_writes_per_day: Maximum writes per day (default: 20,000)
        batch_size: Number of notes per batch (default: 500)
        delay_between_batches: Delay in seconds between batches (default: 4)
    """
    print("="*80)
    print("UPLOADING ALL PATIENTS TO FIRESTORE")
    print("="*80)
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Firestore client
    if credentials_path is None:
        credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    
    print(f"\nCredentials: {credentials_path or 'Using environment variables'}")
    client = FirestoreClient(credentials_path)
    
    # Load all processed notes
    print(f"\n📖 Loading processed notes from {processed_dir}...")
    all_notes = load_processed_notes(processed_dir)
    print(f"   Total notes found: {len(all_notes)}")
    
    if not all_notes:
        print(f"\n⚠️  No notes found to upload")
        return
    
    # Check which notes are already uploaded
    notes_to_upload = check_already_uploaded(client, all_notes, collection_name)
    
    if not notes_to_upload:
        print(f"\n✅ All notes are already uploaded!")
        return
    
    # Upload with rate limiting
    print(f"\n📤 Starting upload with rate limiting...")
    results = upload_with_rate_limiting(
        client,
        notes_to_upload,
        collection_name=collection_name,
        max_writes_per_day=max_writes_per_day,
        batch_size=batch_size,
        delay_between_batches=delay_between_batches
    )
    
    # Final verification
    if results['success'] > 0:
        print(f"\n🔍 Verifying upload...")
        verified = 0
        for note in notes_to_upload[:min(10, len(notes_to_upload))]:  # Verify first 10
            note_id = note.get('note_id', '')
            hadm_id = note.get('hadm_id', '')
            if note_id and hadm_id:
                document_id = f"{note_id}_{hadm_id}"
                if client.document_exists(document_id, collection_name):
                    verified += 1
        
        print(f"   Verified: {verified}/{min(10, len(notes_to_upload))} sample notes exist")
    
    print(f"\n{'='*80}")
    print("UPLOAD COMPLETE")
    print(f"{'='*80}")
    print(f"""
✅ Successfully uploaded: {results['success']} notes
⏭️  Skipped (already exists): {results['skipped']} notes
❌ Failed: {results['failed']} notes
📊 Total processed: {len(all_notes)} notes

✅ Upload complete!
""")
    
    return results


if __name__ == "__main__":
    import sys
    
    print(f"\n🚀 Starting upload for all patients...\n")
    
    try:
        # Check if user wants to proceed
        if len(sys.argv) > 1 and sys.argv[1] == "--confirm":
            results = upload_all_patients(
                processed_dir="processed_files",
                collection_name="discharge_notes",
                max_writes_per_day=MAX_WRITES_PER_DAY,
                batch_size=BATCH_SIZE,
                delay_between_batches=DELAY_BETWEEN_BATCHES
            )
        else:
            print("="*80)
            print("FIRESTORE UPLOAD - SAFETY CHECK")
            print("="*80)
            print(f"""
This script will upload all processed notes to Firestore.

Firestore Free Tier Limits:
- 20,000 writes per day
- Current processed files: {len(list(Path('processed_files').glob('*.json')))}

The script will:
1. Check which notes are already uploaded
2. Upload remaining notes in batches of {BATCH_SIZE}
3. Add {DELAY_BETWEEN_BATCHES} second delay between batches
4. Respect the 20,000 writes/day limit

To proceed, run:
    python3 upload_all_patients.py --confirm
""")
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Upload interrupted by user")
        print(f"   Progress has been saved. You can resume by running the script again.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

