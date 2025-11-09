#!/usr/bin/env python3
"""
On-demand note processor.
Processes notes from raw data only when requested, then uploads to Firestore.
"""
import os
import json
import gzip
import csv
from pathlib import Path
from typing import Dict, Optional, List
from dotenv import load_dotenv
from .firestore_client import FirestoreClient
from data_preprocessing.preprocess_discharge_notes import RobustDischargeNoteSectionizer, preprocess_discharge_notes


class OnDemandProcessor:
    """Process notes on-demand from raw data."""
    
    def __init__(self, 
                 raw_dataset_path: str = "raw_dataset/mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/discharge.csv.gz",
                 credentials_path: Optional[str] = None):
        """
        Initialize on-demand processor.
        
        Args:
            raw_dataset_path: Path to raw discharge CSV file
            credentials_path: Path to Firebase credentials (uses env var if None)
        """
        self.raw_dataset_path = Path(raw_dataset_path)
        self.sectionizer = RobustDischargeNoteSectionizer()
        
        # Initialize Firestore client
        load_dotenv()
        if credentials_path is None:
            credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        
        self.firestore_client = FirestoreClient(credentials_path)
        self.collection_name = "discharge_notes"
    
    def get_or_process_note(self, 
                           note_id: str, 
                           hadm_id: str,
                           upload_to_firestore: bool = True) -> Optional[Dict]:
        """
        Get note from Firestore, or process from raw data if not found.
        
        Args:
            note_id: Note ID (e.g., "10000032-DS-21")
            hadm_id: Hospital admission ID (e.g., "22595853")
            upload_to_firestore: If True, upload processed note to Firestore
        
        Returns:
            Processed note dictionary, or None if not found
        """
        document_id = f"{note_id}_{hadm_id}"
        
        # Step 1: Check if note exists in Firestore
        print(f"🔍 Checking Firestore for: {document_id}")
        note = self.firestore_client.get_discharge_note(document_id, self.collection_name)
        
        if note:
            print(f"   ✅ Found in Firestore")
            return note
        
        # Step 2: Process from raw data
        print(f"   ⚠️  Not found in Firestore, processing from raw data...")
        note = self._process_from_raw(note_id, hadm_id)
        
        if not note:
            print(f"   ❌ Note not found in raw data")
            return None
        
        # Step 3: Upload to Firestore (if requested)
        if upload_to_firestore:
            print(f"   📤 Uploading to Firestore...")
            try:
                self.firestore_client.upload_note(
                    note,
                    document_id=document_id,
                    collection_name=self.collection_name,
                    skip_if_exists=True
                )
                print(f"   ✅ Uploaded to Firestore")
            except Exception as e:
                print(f"   ⚠️  Error uploading to Firestore: {e}")
        
        return note
    
    def _process_from_raw(self, note_id: str, hadm_id: str) -> Optional[Dict]:
        """
        Process note from raw CSV file.
        
        Args:
            note_id: Note ID
            hadm_id: Hospital admission ID
        
        Returns:
            Processed note dictionary, or None if not found
        """
        if not self.raw_dataset_path.exists():
            print(f"   ❌ Raw dataset not found: {self.raw_dataset_path}")
            return None
        
        # Load note from raw CSV
        print(f"   📖 Loading from raw CSV...")
        raw_note = None
        
        try:
            with gzip.open(self.raw_dataset_path, 'rt', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (row.get('note_id', '').strip() == note_id and 
                        row.get('hadm_id', '').strip() == hadm_id):
                        raw_note = row
                        break
        except Exception as e:
            print(f"   ❌ Error reading raw CSV: {e}")
            return None
        
        if not raw_note:
            print(f"   ❌ Note not found in raw data")
            return None
        
        print(f"   ✅ Found in raw data")
        
        # Process note
        print(f"   🔄 Processing note...")
        raw_text = raw_note.get('text', '')
        
        # Extract sections
        sections = self.sectionizer.extract_sections(raw_text)
        
        # Clean sections
        cleaned_sections = {}
        for section_name, section_text in sections.items():
            cleaned_text = self.sectionizer.clean_text(section_text)
            cleaned_sections[section_name] = cleaned_text
        
        # Create processed note structure
        processed_note = {
            "note_id": note_id,
            "subject_id": raw_note.get('subject_id', ''),
            "hadm_id": hadm_id,
            "note_type": raw_note.get('note_type', 'DS'),
            "charttime": raw_note.get('charttime', ''),
            "storetime": raw_note.get('storetime', ''),
            "sections": cleaned_sections,
            "section_summary": {
                section_name: {
                    "length": len(section_text),
                    "has_content": bool(section_text)
                }
                for section_name, section_text in cleaned_sections.items()
            }
        }
        
        print(f"   ✅ Processed successfully")
        return processed_note
    
    def process_patient_notes(self, 
                             subject_id: str,
                             upload_to_firestore: bool = True) -> List[Dict]:
        """
        Process all notes for a patient on-demand.
        
        Args:
            subject_id: Patient subject_id
            upload_to_firestore: If True, upload processed notes to Firestore
        
        Returns:
            List of processed notes
        """
        print(f"📋 Processing notes for patient: {subject_id}")
        
        # Get all note IDs for this patient from raw data
        note_ids = []
        
        if not self.raw_dataset_path.exists():
            print(f"   ❌ Raw dataset not found: {self.raw_dataset_path}")
            return []
        
        try:
            with gzip.open(self.raw_dataset_path, 'rt', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('subject_id', '').strip() == subject_id:
                        note_id = row.get('note_id', '').strip()
                        hadm_id = row.get('hadm_id', '').strip()
                        if note_id and hadm_id:
                            note_ids.append((note_id, hadm_id))
        except Exception as e:
            print(f"   ❌ Error reading raw CSV: {e}")
            return []
        
        print(f"   Found {len(note_ids)} notes for patient {subject_id}")
        
        # Process each note
        processed_notes = []
        for note_id, hadm_id in note_ids:
            note = self.get_or_process_note(note_id, hadm_id, upload_to_firestore)
            if note:
                processed_notes.append(note)
        
        print(f"   ✅ Processed {len(processed_notes)} notes")
        return processed_notes


def process_note_on_demand(note_id: str, 
                          hadm_id: str,
                          raw_dataset_path: str = "raw_dataset/mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/discharge.csv.gz",
                          upload_to_firestore: bool = True) -> Optional[Dict]:
    """
    Convenience function to process a single note on-demand.
    
    Args:
        note_id: Note ID (e.g., "10000032-DS-21")
        hadm_id: Hospital admission ID (e.g., "22595853")
        raw_dataset_path: Path to raw discharge CSV file
        upload_to_firestore: If True, upload processed note to Firestore
    
    Returns:
        Processed note dictionary, or None if not found
    """
    processor = OnDemandProcessor(raw_dataset_path=raw_dataset_path)
    return processor.get_or_process_note(note_id, hadm_id, upload_to_firestore)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python3 on_demand_processor.py <note_id> <hadm_id>")
        print("Example: python3 on_demand_processor.py 10000032-DS-21 22595853")
        sys.exit(1)
    
    note_id = sys.argv[1]
    hadm_id = sys.argv[2]
    
    print(f"🚀 Processing note on-demand: {note_id} (hadm_id: {hadm_id})\n")
    
    note = process_note_on_demand(note_id, hadm_id, upload_to_firestore=True)
    
    if note:
        print(f"\n✅ Successfully processed note!")
        print(f"   Note ID: {note.get('note_id', 'N/A')}")
        print(f"   hadm_id: {note.get('hadm_id', 'N/A')}")
        print(f"   Sections: {len(note.get('sections', {}))}")
    else:
        print(f"\n❌ Failed to process note")
        sys.exit(1)

