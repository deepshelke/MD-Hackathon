"""
Main pipeline: Firestore → Prompt Builder → MedLlama-3 → Output
"""
import json
import os
import logging
from typing import Dict, Optional, Any
from dotenv import load_dotenv
from .firestore_client import FirestoreClient
from .prompts import PromptBuilder
from .model_client import HuggingFaceClient
from .sectionizer import DischargeNoteSectionizer

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimplificationPipeline:
    """Main pipeline to simplify discharge notes."""
    
    def __init__(self,
                 firestore_credentials_path: Optional[str] = None,
                 hf_api_token: Optional[str] = None,
                 hf_model_name: str = "johnsnowlabs/JSL-MedLlama-3-8B-v2.0",
                 hf_endpoint_url: Optional[str] = None):
        """
        Initialize the pipeline.
        
        Args:
            firestore_credentials_path: Path to Firebase service account JSON (optional, uses env vars if None)
            hf_api_token: Hugging Face API token (optional, uses HF_TOKEN env var if None)
            hf_model_name: Model name on Hugging Face
            hf_endpoint_url: Optional custom HF endpoint URL
        """
        self.firestore_client = FirestoreClient(firestore_credentials_path)
        self.hf_client = HuggingFaceClient(
            model_name=hf_model_name,
            api_token=hf_api_token or os.getenv("HF_TOKEN"),
            endpoint_url=hf_endpoint_url
        )
        self.prompt_builder = PromptBuilder()
    
    def process_note(self, 
                    note_id: Optional[str] = None,
                    hadm_id: Optional[str] = None,
                    document_id: Optional[str] = None,
                    collection_name: str = "discharge_notes",
                    sections_field: str = "sections") -> Dict[str, Any]:
        """
        Process a single note: fetch → prompt → LLM → return result.
        
        Args:
            note_id: Note ID (e.g., "10000032-DS-21")
            hadm_id: Hospital admission ID (e.g., "22595853")
            document_id: Firestore document ID (if provided, note_id and hadm_id are ignored)
                        Format: "noteid_hadm_id" (e.g., "10000032-DS-21_22595853")
            collection_name: Firestore collection name
            sections_field: Field name with pre-sectionized data (default: "sections")
        
        Returns:
            Dictionary with:
            - note_id: Original note ID
            - hadm_id: Hospital admission ID
            - document_id: Firestore document ID used
            - input_sections: Sectionized input
            - simplified_output: LLM response (JSON string)
            - parsed_output: Parsed JSON (if valid)
            - error: Error message if any
        """
        # Construct document ID
        if document_id:
            doc_id = document_id
        elif note_id and hadm_id:
            doc_id = f"{note_id}_{hadm_id}"
        else:
            return {
                "note_id": note_id,
                "hadm_id": hadm_id,
                "document_id": None,
                "input_sections": None,
                "simplified_output": None,
                "parsed_output": None,
                "error": "Either document_id or both note_id and hadm_id must be provided"
            }
        
        result = {
            "note_id": note_id,
            "hadm_id": hadm_id,
            "document_id": doc_id,
            "input_sections": None,
            "simplified_output": None,
            "parsed_output": None,
            "error": None
        }
        
        try:
            # Step 1: Fetch note from Firestore
            note_doc = self.firestore_client.get_discharge_note(doc_id, collection_name)
            
            if not note_doc:
                result["error"] = f"Note {doc_id} not found in Firestore"
                return result
            
            # Step 2: Extract sections from processed note
            if sections_field in note_doc:
                # Use pre-sectionized data from processed note
                sections = note_doc[sections_field]
                
                # Ensure sections is a dictionary
                if not isinstance(sections, dict):
                    result["error"] = f"Sections field '{sections_field}' is not a dictionary"
                    return result
                
                # Check if sections have any content
                total_content = sum(len(str(v)) for v in sections.values() if v)
                if total_content == 0:
                    result["error"] = f"All sections in '{sections_field}' are empty - no content to process"
                    return result
            else:
                result["error"] = f"Sections field '{sections_field}' not found in document"
                return result
            
            result["input_sections"] = sections
            
            # Log sections for debugging
            logger.info(f"📋 Sections extracted:")
            logger.info(f"   Total sections: {len(sections)}")
            for section_name, section_content in sections.items():
                content_length = len(str(section_content)) if section_content else 0
                has_content = bool(section_content and str(section_content).strip())
                logger.info(f"   - {section_name}: {content_length} chars, has_content: {has_content}")
                if has_content:
                    preview = str(section_content)[:100].replace('\n', ' ')
                    logger.info(f"     Preview: {preview}...")
            
            # Step 3: Build prompts (with trimming if needed)
            logger.info(f"🔨 Building prompts...")
            prompts = self.prompt_builder.build_full_prompt(sections)
            
            # Log prompt length (no limit check - removed filter)
            total_length = prompts.get("total_length", len(prompts["system"]) + len(prompts["user"]))
            logger.info(f"📊 Prompt stats:")
            logger.info(f"   System prompt: {len(prompts['system'])} chars")
            logger.info(f"   User prompt: {len(prompts['user'])} chars")
            logger.info(f"   Total: {total_length} chars")
            # Note: Prompt length limit removed - no longer checking against 7000 char limit
            
            # Step 4: Call LLM
            simplified_output = self.hf_client.simplify_note(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                max_tokens=1500,  # Reduced to save memory
                temperature=0.2
            )
            
            result["simplified_output"] = simplified_output
            
            # Step 5: Try to parse JSON (optional - model returns plain text by default)
            # Only try to parse if output looks like JSON, otherwise keep as plain text
            if simplified_output and simplified_output.strip():
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
                    
                    # Only try to parse if it starts with { or [
                    if cleaned_output.startswith("{") or cleaned_output.startswith("["):
                        parsed_output = json.loads(cleaned_output)
                        result["parsed_output"] = parsed_output
                    else:
                        # Plain text output - this is expected and fine
                        result["parsed_output"] = None
                except json.JSONDecodeError:
                    # Not JSON - this is fine, we expect plain text
                    result["parsed_output"] = None
            else:
                # Empty output - this is an error
                result["error"] = "Model returned empty response"
                result["parsed_output"] = None
            
        except Exception as e:
            result["error"] = f"Pipeline error: {str(e)}"
        
        return result
    
    def process_multiple_notes(self,
                              note_ids: list,
                              hadm_ids: Optional[list] = None,
                              document_ids: Optional[list] = None,
                              collection_name: str = "discharge_notes",
                              **kwargs) -> list:
        """
        Process multiple notes.
        
        Args:
            note_ids: List of note IDs (e.g., ["10000032-DS-21", ...])
            hadm_ids: List of hadm_ids corresponding to note_ids (optional)
            document_ids: List of Firestore document IDs (if provided, note_ids and hadm_ids are ignored)
                        Format: ["noteid_hadm_id", ...]
            collection_name: Firestore collection name
            **kwargs: Additional args for process_note
            
        Returns:
            List of result dictionaries
        """
        results = []
        
        if document_ids:
            # Use document IDs directly
            for doc_id in document_ids:
                result = self.process_note(
                    document_id=doc_id,
                    collection_name=collection_name,
                    **kwargs
                )
                results.append(result)
        elif note_ids and hadm_ids and len(note_ids) == len(hadm_ids):
            # Use note_id and hadm_id pairs
            for note_id, hadm_id in zip(note_ids, hadm_ids):
                result = self.process_note(
                    note_id=note_id,
                    hadm_id=hadm_id,
                    collection_name=collection_name,
                    **kwargs
                )
                results.append(result)
        else:
            # Fallback: try to use note_ids as document_ids
            for note_id in note_ids:
                result = self.process_note(
                    document_id=note_id,
                    collection_name=collection_name,
                    **kwargs
                )
                results.append(result)
        
        return results

