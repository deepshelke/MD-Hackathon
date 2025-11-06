"""
Example usage of the simplification pipeline.
"""
import os
from dotenv import load_dotenv
from src.pipeline import SimplificationPipeline

# Load environment variables
load_dotenv()

def main():
    # Initialize pipeline
    pipeline = SimplificationPipeline(
        firestore_credentials_path=os.getenv("FIREBASE_CREDENTIALS_PATH"),
        hf_api_token=os.getenv("HF_TOKEN"),
        hf_model_name="johnsnowlabs/JSL-MedLlama-3-8B-v2.0"
    )
    
    # Example: Process a single note
    note_id = "example_note_id_123"  # Replace with actual Firestore document ID
    
    print(f"Processing note: {note_id}")
    result = pipeline.process_note(note_id)
    
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        print("\n=== Simplified Output ===")
        if result["parsed_output"]:
            import json
            print(json.dumps(result["parsed_output"], indent=2))
        else:
            print(result["simplified_output"])
    
    # Example: Process multiple notes
    # note_ids = ["note1", "note2", "note3"]
    # results = pipeline.process_multiple_notes(note_ids)
    # for result in results:
    #     print(f"Note {result['note_id']}: {'Success' if not result['error'] else result['error']}")

if __name__ == "__main__":
    main()

