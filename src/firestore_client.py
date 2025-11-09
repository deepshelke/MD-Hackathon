"""
Firestore client to fetch processed discharge notes.
"""
import os
from typing import Dict, List, Optional
from google.cloud import firestore
from google.oauth2 import service_account


class FirestoreClient:
    """Client to interact with Firestore database."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Firestore client.
        
        Args:
            credentials_path: Path to Firebase service account JSON file.
                            If None, looks for FIREBASE_CREDENTIALS_PATH env var.
                            If not found, tries to create from individual env vars.
        """
        credentials = None
        
        # Try to load from file path
        if credentials_path is None:
            credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        
        if credentials_path:
            # Load from file
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
        else:
            # Try to create from environment variables
            project_id = os.getenv("FIREBASE_PROJECT_ID")
            client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
            private_key_id = os.getenv("FIREBASE_PRIVATE_KEY_ID")
            private_key = os.getenv("FIREBASE_PRIVATE_KEY")
            
            if project_id and client_email and private_key:
                # Create credentials from env vars
                import json
                credentials_dict = {
                    "type": "service_account",
                    "project_id": project_id,
                    "private_key_id": private_key_id,
                    "private_key": private_key.replace('\\n', '\n'),
                    "client_email": client_email,
                    "client_id": "",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}"
                }
                
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict
                )
            else:
                raise ValueError(
                    "Firebase credentials required. "
                    "Set FIREBASE_CREDENTIALS_PATH env var, or set "
                    "FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY env vars."
                )
        
        # Initialize Firestore client
        self.db = firestore.Client(
            credentials=credentials,
            project=credentials.project_id
        )
    
    def get_discharge_note(self, note_id: str, collection_name: str = "discharge_notes") -> Optional[Dict]:
        """
        Fetch a single discharge note by ID.
        
        Args:
            note_id: Document ID in Firestore
            collection_name: Name of the Firestore collection
            
        Returns:
            Document data as dict, or None if not found
        """
        doc_ref = self.db.collection(collection_name).document(note_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        return None
    
    def get_all_notes(self, collection_name: str = "discharge_notes", limit: Optional[int] = None) -> List[Dict]:
        """
        Fetch all discharge notes from collection.
        
        Args:
            collection_name: Name of the Firestore collection
            limit: Maximum number of documents to fetch (None = all)
            
        Returns:
            List of document data as dicts
        """
        query = self.db.collection(collection_name)
        
        if limit:
            query = query.limit(limit)
        
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    
    def get_notes_by_field(self, 
                          field: str, 
                          value: any, 
                          collection_name: str = "discharge_notes",
                          limit: Optional[int] = None) -> List[Dict]:
        """
        Fetch notes filtered by a field value.
        
        Args:
            field: Field name to filter by
            value: Value to match
            collection_name: Name of the Firestore collection
            limit: Maximum number of documents to fetch
            
        Returns:
            List of matching documents
        """
        query = self.db.collection(collection_name).where(field, "==", value)
        
        if limit:
            query = query.limit(limit)
        
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    
    def get_note_text(self, note_id: str, text_field: str = "note_text", collection_name: str = "discharge_notes") -> Optional[str]:
        """
        Convenience method to get just the note text.
        
        Args:
            note_id: Document ID
            text_field: Field name containing the note text
            collection_name: Name of the Firestore collection
            
        Returns:
            Note text as string, or None if not found
        """
        note = self.get_discharge_note(note_id, collection_name)
        if note and text_field in note:
            return note[text_field]
        return None
    
    def upload_note(self, note_data: Dict, document_id: Optional[str] = None, collection_name: str = "discharge_notes", skip_if_exists: bool = True) -> bool:
        """
        Upload a single discharge note to Firestore.
        
        Args:
            note_data: Dictionary containing note data
            document_id: Document ID (if None, uses note_id_hadm_id format)
            collection_name: Name of the Firestore collection
            skip_if_exists: If True, skip upload if document already exists
            
        Returns:
            True if uploaded successfully, False otherwise
        """
        # Generate document ID if not provided
        if document_id is None:
            note_id = note_data.get('note_id', '')
            hadm_id = note_data.get('hadm_id', '')
            if note_id and hadm_id:
                document_id = f"{note_id}_{hadm_id}"
            else:
                raise ValueError("Cannot generate document ID: note_id and hadm_id required")
        
        # Check if document exists
        if skip_if_exists:
            doc_ref = self.db.collection(collection_name).document(document_id)
            if doc_ref.get().exists:
                return False  # Already exists, skip
        
        # Upload document
        doc_ref = self.db.collection(collection_name).document(document_id)
        doc_ref.set(note_data)
        return True
    
    def upload_notes_batch(self, notes_data: List[Dict], collection_name: str = "discharge_notes", skip_if_exists: bool = True, batch_size: int = 500) -> Dict[str, int]:
        """
        Upload multiple discharge notes to Firestore in batches.
        
        Args:
            notes_data: List of dictionaries containing note data
            collection_name: Name of the Firestore collection
            skip_if_exists: If True, skip upload if document already exists
            batch_size: Number of documents per batch (max 500)
            
        Returns:
            Dictionary with counts: {'success': int, 'skipped': int, 'failed': int}
        """
        if batch_size > 500:
            batch_size = 500  # Firestore limit
        
        results = {'success': 0, 'skipped': 0, 'failed': 0}
        
        # Process in batches
        for i in range(0, len(notes_data), batch_size):
            batch = notes_data[i:i + batch_size]
            batch_results = self._upload_batch(batch, collection_name, skip_if_exists)
            
            results['success'] += batch_results['success']
            results['skipped'] += batch_results['skipped']
            results['failed'] += batch_results['failed']
        
        return results
    
    def _upload_batch(self, notes_data: List[Dict], collection_name: str, skip_if_exists: bool) -> Dict[str, int]:
        """Upload a single batch of notes."""
        results = {'success': 0, 'skipped': 0, 'failed': 0}
        batch = self.db.batch()
        batch_count = 0
        
        for note_data in notes_data:
            # Generate document ID
            note_id = note_data.get('note_id', '')
            hadm_id = note_data.get('hadm_id', '')
            if not note_id or not hadm_id:
                results['failed'] += 1
                continue
            
            document_id = f"{note_id}_{hadm_id}"
            
            # Check if document exists
            if skip_if_exists:
                doc_ref = self.db.collection(collection_name).document(document_id)
                if doc_ref.get().exists:
                    results['skipped'] += 1
                    continue
            
            # Add to batch
            doc_ref = self.db.collection(collection_name).document(document_id)
            batch.set(doc_ref, note_data)
            batch_count += 1
            
            # Commit batch if it reaches 500 operations
            if batch_count >= 500:
                try:
                    batch.commit()
                    results['success'] += batch_count
                    batch_count = 0
                    batch = self.db.batch()
                except Exception as e:
                    results['failed'] += batch_count
                    batch_count = 0
                    batch = self.db.batch()
        
        # Commit remaining operations
        if batch_count > 0:
            try:
                batch.commit()
                results['success'] += batch_count
            except Exception as e:
                results['failed'] += batch_count
        
        return results
    
    def document_exists(self, document_id: str, collection_name: str = "discharge_notes") -> bool:
        """
        Check if a document exists in Firestore.
        
        Args:
            document_id: Document ID
            collection_name: Name of the Firestore collection
            
        Returns:
            True if document exists, False otherwise
        """
        doc_ref = self.db.collection(collection_name).document(document_id)
        return doc_ref.get().exists

