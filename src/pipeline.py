"""
Main pipeline: Firestore → Prompt Builder → MedLlama-3 → Output
"""
import json
from typing import Dict, Optional, Any
from .firestore_client import FirestoreClient
from .prompts import PromptBuilder
from .model_client import HuggingFaceClient


class SimplificationPipeline:
    """Main pipeline to simplify discharge notes."""
    
    def __init__(self,
                 firestore_credentials_path: str,
                 hf_api_token: str,
                 hf_model_name: str = "johnsnowlabs/JSL-MedLlama-3-8B-v2.0",
                 hf_endpoint_url: Optional[str] = None):
        """
        Initialize the pipeline.
        
        Args:
            firestore_credentials_path: Path to Firebase service account JSON
            hf_api_token: Hugging Face API token
            hf_model_name: Model name on Hugging Face
            hf_endpoint_url: Optional custom HF endpoint URL
        """
        self.firestore_client = FirestoreClient(firestore_credentials_path)
        self.hf_client = HuggingFaceClient(
            model_name=hf_model_name,
            api_token=hf_api_token,
            endpoint_url=hf_endpoint_url
        )
        self.prompt_builder = PromptBuilder()
    
    def process_note(self, 
                    note_id: str,
                    collection_name: str = "discharge_notes",
                    note_text_field: str = "note_text",
                    sections_field: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a single note: fetch → prompt → LLM → return result.
        
        Args:
            note_id: Firestore document ID
            collection_name: Firestore collection name
            note_text_field: Field name containing raw note text
            sections_field: Optional field name with pre-sectionized data.
                          If None, assumes note_text_field contains full text.
        
        Returns:
            Dictionary with:
            - note_id: Original note ID
            - input_sections: Sectionized input
            - simplified_output: LLM response (JSON string)
            - parsed_output: Parsed JSON (if valid)
            - error: Error message if any
        """
        result = {
            "note_id": note_id,
            "input_sections": None,
            "simplified_output": None,
            "parsed_output": None,
            "error": None
        }
        
        try:
            # Step 1: Fetch note from Firestore
            note_doc = self.firestore_client.get_discharge_note(note_id, collection_name)
            
            if not note_doc:
                result["error"] = f"Note {note_id} not found in Firestore"
                return result
            
            # Step 2: Extract sections
            if sections_field and sections_field in note_doc:
                # Use pre-sectionized data if available
                sections = note_doc[sections_field]
            elif note_text_field in note_doc:
                # For now, assume note_text contains full text
                # TODO: Add sectionizer if needed
                # For now, create a simple structure
                note_text = note_doc[note_text_field]
                sections = {
                    "Diagnoses": note_text,  # Placeholder - will be sectionized later
                    "Hospital Course": "",
                    "Discharge Medications": "",
                    "Follow-up": "",
                    "Allergies": "",
                    "Pending Tests": "",
                    "Diet/Activity": ""
                }
            else:
                result["error"] = f"Note text not found in field '{note_text_field}'"
                return result
            
            result["input_sections"] = sections
            
            # Step 3: Build prompts
            prompts = self.prompt_builder.build_full_prompt(sections)
            
            # Step 4: Call LLM
            simplified_output = self.hf_client.simplify_note(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                max_tokens=900,
                temperature=0.2
            )
            
            result["simplified_output"] = simplified_output
            
            # Step 5: Try to parse JSON
            try:
                # Clean the output (remove markdown code blocks if present)
                cleaned_output = simplified_output.strip()
                if cleaned_output.startswith("```json"):
                    cleaned_output = cleaned_output[7:]
                if cleaned_output.startswith("```"):
                    cleaned_output = cleaned_output[3:]
                if cleaned_output.endswith("```"):
                    cleaned_output = cleaned_output[:-3]
                cleaned_output = cleaned_output.strip()
                
                parsed_output = json.loads(cleaned_output)
                result["parsed_output"] = parsed_output
            except json.JSONDecodeError as e:
                result["error"] = f"Failed to parse JSON output: {e}"
                result["parsed_output"] = None
            
        except Exception as e:
            result["error"] = f"Pipeline error: {str(e)}"
        
        return result
    
    def process_multiple_notes(self,
                              note_ids: list,
                              collection_name: str = "discharge_notes",
                              **kwargs) -> list:
        """
        Process multiple notes.
        
        Args:
            note_ids: List of Firestore document IDs
            collection_name: Firestore collection name
            **kwargs: Additional args for process_note
            
        Returns:
            List of result dictionaries
        """
        results = []
        for note_id in note_ids:
            result = self.process_note(note_id, collection_name, **kwargs)
            results.append(result)
        return results

