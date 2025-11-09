#!/usr/bin/env python3
"""
Upload processed discharge notes to Firestore.
Supports uploading notes for a single patient or all patients.
"""
import os
import json
import sys
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
from src.firestore_client import FirestoreClient


def load_processed_notes(processed_dir: str = "processed_files") -> List[Dict]:
    """
    Load all processed notes from JSON files.
    
    Args:
        processed_dir: Directory containing processed JSON files
        
    Returns:
        List of note dictionaries
    """
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


def upload_patient_notes(subject_id: str, 
                         processed_dir: str = "processed_files",
                         collection_name: str = "discharge_notes",
                         credentials_path: str = None) -> Dict:
    """
    Upload processed notes for a single patient to Firestore.
    
    Args:
        subject_id: Patient subject_id
        processed_dir: Directory containing processed JSON files
        collection_name: Firestore collection name
        credentials_path: Path to Firebase credentials (uses env var if None)
        
    Returns:
        Dictionary with upload results
    """
    print("=" * 80)
    print("UPLOADING PATIENT NOTES TO FIRESTORE")
    print("=" * 80)
    print(f"\nPatient: {subject_id}")
    print(f"Collection: {collection_name}")
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Firestore client (will use env vars if credentials_path is None)
    print(f"Credentials: {credentials_path or 'Using environment variables'}")
    
    client = FirestoreClient(credentials_path)
    
    # Load all processed notes
    print(f"\n📖 Loading processed notes from {processed_dir}...")
    all_notes = load_processed_notes(processed_dir)
    print(f"   Total notes found: {len(all_notes)}")
    
    # Filter notes for this patient
    patient_notes = [note for note in all_notes if note.get('subject_id', '') == subject_id]
    
    if not patient_notes:
        print(f"\n⚠️  No notes found for patient {subject_id}")
        return {'success': 0, 'skipped': 0, 'failed': 0, 'total': 0}
    
    print(f"   Notes for patient {subject_id}: {len(patient_notes)}")
    
    # Check which notes already exist
    print(f"\n🔍 Checking existing documents...")
    existing_count = 0
    for note in patient_notes:
        note_id = note.get('note_id', '')
        hadm_id = note.get('hadm_id', '')
        if note_id and hadm_id:
            document_id = f"{note_id}_{hadm_id}"
            if client.document_exists(document_id, collection_name):
                existing_count += 1
    
    print(f"   Already uploaded: {existing_count}/{len(patient_notes)}")
    
    # Upload notes
    print(f"\n📤 Uploading notes...")
    results = client.upload_notes_batch(
        patient_notes,
        collection_name=collection_name,
        skip_if_exists=True,
        batch_size=500
    )
    
    # Print results
    print(f"\n{'='*80}")
    print("UPLOAD RESULTS")
    print(f"{'='*80}")
    print(f"\n✅ Successfully uploaded: {results['success']}")
    print(f"⏭️  Skipped (already exists): {results['skipped']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📊 Total: {len(patient_notes)}")
    
    # Verify upload
    if results['success'] > 0:
        print(f"\n🔍 Verifying upload...")
        verified = 0
        for note in patient_notes:
            note_id = note.get('note_id', '')
            hadm_id = note.get('hadm_id', '')
            if note_id and hadm_id:
                document_id = f"{note_id}_{hadm_id}"
                if client.document_exists(document_id, collection_name):
                    verified += 1
        
        print(f"   Verified: {verified}/{len(patient_notes)} documents exist")
        
        # Test retrieval
        if verified > 0:
            print(f"\n🧪 Testing retrieval...")
            sample_note = patient_notes[0]
            sample_note_id = sample_note.get('note_id', '')
            sample_hadm_id = sample_note.get('hadm_id', '')
            sample_doc_id = f"{sample_note_id}_{sample_hadm_id}"
            
            retrieved = client.get_discharge_note(sample_doc_id, collection_name)
            if retrieved:
                print(f"   ✅ Successfully retrieved: {sample_doc_id}")
                print(f"      Note ID: {retrieved.get('note_id', 'N/A')}")
                print(f"      hadm_id: {retrieved.get('hadm_id', 'N/A')}")
                print(f"      Sections: {len(retrieved.get('sections', {}))}")
            else:
                print(f"   ⚠️  Could not retrieve: {sample_doc_id}")
    
    return {
        'success': results['success'],
        'skipped': results['skipped'],
        'failed': results['failed'],
        'total': len(patient_notes)
    }


if __name__ == "__main__":
    # Default: upload patient 10000032
    subject_id = "10000032"
    
    if len(sys.argv) > 1:
        subject_id = sys.argv[1]
    
    print(f"\n🚀 Starting upload for patient {subject_id}...\n")
    
    try:
        results = upload_patient_notes(
            subject_id=subject_id,
            processed_dir="processed_files",
            collection_name="discharge_notes"
        )
        
        if results['success'] > 0:
            print(f"\n✅ Successfully uploaded {results['success']} notes!")
        elif results['skipped'] > 0:
            print(f"\n✅ All notes already uploaded ({results['skipped']} skipped)")
        else:
            print(f"\n⚠️  No notes uploaded")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

