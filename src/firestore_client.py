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
        """
        if credentials_path is None:
            credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        
        if credentials_path is None:
            raise ValueError(
                "Firebase credentials path required. "
                "Set FIREBASE_CREDENTIALS_PATH env var or pass credentials_path."
            )
        
        # Load credentials
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
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

