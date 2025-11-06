"""
Test script to test model response locally with debugging.
Uses sample text from test_note.txt
"""
import os
import json
from dotenv import load_dotenv
from src.prompts import PromptBuilder
from src.model_client import HuggingFaceClient

# Load environment variables
load_dotenv()

def test_model_with_sample_text():
    """Test the model with sample text and show debugging info."""
    print("="*80)
    print("🧪 TESTING MODEL WITH SAMPLE TEXT")
    print("="*80)
    
    # Read sample text
    print("\n📄 Reading sample text from test_note.txt...")
    try:
        with open('test_note.txt', 'r') as f:
            sample_text = f.read()
        print(f"✅ Sample text loaded ({len(sample_text)} characters)")
        print(f"\n📝 First 200 characters:\n{sample_text[:200]}...\n")
    except FileNotFoundError:
        print("❌ test_note.txt not found!")
        return
    
    # Get HF token
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN not found in .env file")
        return
    
    print(f"✅ HF Token found (starts with: {hf_token[:10]}...)\n")
    
    # Create sections (for test mode)
    print("🔧 Creating sections from sample text...")
    sections = {
        "Diagnoses": sample_text,
        "Hospital Course": "",
        "Discharge Medications": "",
        "Follow-up": "",
        "Allergies": "",
        "Pending Tests": "",
        "Diet/Activity": ""
    }
    print("✅ Sections created\n")
    
    # Build prompts
    print("📝 Building prompts...")
    prompt_builder = PromptBuilder()
    prompts = prompt_builder.build_full_prompt(sections)
    
    print("\n" + "="*80)
    print("📤 SYSTEM PROMPT:")
    print("="*80)
    print(prompts["system"])
    print("\n" + "="*80)
    print("📤 USER PROMPT:")
    print("="*80)
    print(prompts["user"][:500] + "..." if len(prompts["user"]) > 500 else prompts["user"])
    print("="*80)
    
    # Create full prompt
    full_prompt = f"{prompts['system']}\n\n{prompts['user']}\n\nOutput (JSON only):"
    print(f"\n📊 Full prompt length: {len(full_prompt)} characters")
    print(f"📊 Full prompt tokens (approx): {len(full_prompt.split())} words\n")
    
    # Initialize model client
    print("🤖 Initializing Hugging Face client...")
    try:
        hf_client = HuggingFaceClient(
            model_name="johnsnowlabs/JSL-MedLlama-3-8B-v2.0",
            api_token=hf_token
        )
        print("✅ Model client initialized\n")
    except Exception as e:
        print(f"❌ Failed to initialize model client: {e}")
        return
    
    # Call model
    print("="*80)
    print("🔄 CALLING MODEL...")
    print("="*80)
    print("⏳ This may take 30-60 seconds...\n")
    
    try:
        # Call directly to see raw response
        print("📤 Making API call...")
        print(f"   Max tokens: 900")
        print(f"   Temperature: 0.2\n")
        
        # Build full prompt
        full_prompt = f"{prompts['system']}\n\n{prompts['user']}\n\nOutput (JSON only):"
        
        # Call the model directly with more debugging
        print("📤 Sending request to Hugging Face API...")
        print(f"   Prompt length: {len(full_prompt)} chars")
        print(f"   Prompt preview: {full_prompt[:100]}...\n")
        
        try:
            response = hf_client.client.text_generation(
                prompt=full_prompt,
                max_new_tokens=900,
                temperature=0.2,
                top_p=0.95,
                return_full_text=False
            )
            
            print(f"✅ API call completed")
            print(f"📊 Response type: {type(response)}")
            print(f"📊 Response repr: {repr(response)}")
            print(f"📊 Response length: {len(str(response))} characters")
            
            # Check if response is empty or None
            if not response or len(str(response).strip()) == 0:
                print("\n⚠️  WARNING: Empty response received!")
                print("   This might mean:")
                print("   1. Model is not generating output")
                print("   2. Response is being filtered")
                print("   3. API issue")
                print("\n   Trying with return_full_text=True...")
                
                # Try with return_full_text=True
                response2 = hf_client.client.text_generation(
                    prompt=full_prompt,
                    max_new_tokens=900,
                    temperature=0.2,
                    top_p=0.95,
                    return_full_text=True
                )
                print(f"   Response with return_full_text=True: {len(str(response2))} chars")
                if response2 and len(str(response2)) > 0:
                    response = response2
                    print("   ✅ Got response with return_full_text=True\n")
            
        except Exception as api_error:
            print(f"❌ API Error: {api_error}")
            import traceback
            traceback.print_exc()
            return
        
        print("="*80)
        print("✅ MODEL RESPONSE RECEIVED")
        print("="*80)
        
        # Convert to string if needed
        response_str = str(response).strip()
        print(f"📊 Response length: {len(response_str)} characters")
        print(f"📊 Response tokens (approx): {len(response_str.split())} words\n")
        
        print("="*80)
        print("📝 RAW RESPONSE (first 500 chars):")
        print("="*80)
        print(response_str[:500])
        if len(response_str) > 500:
            print(f"... (truncated, total {len(response_str)} chars)")
        print("="*80)
        
        print("\n📝 FULL RAW RESPONSE:")
        print("="*80)
        print(response_str)
        print("="*80)
        
        # Try to parse JSON
        print("\n" + "="*80)
        print("🔍 PARSING JSON...")
        print("="*80)
        
        cleaned = response_str.strip()
        
        # Strategy 1: Remove markdown
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
            print("✅ Removed ```json markdown")
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
            print("✅ Removed ``` markdown")
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            print("✅ Removed closing ```")
        cleaned = cleaned.strip()
        
        # Strategy 2: Try direct JSON parse
        output = None
        try:
            output = json.loads(cleaned)
            print("✅ Successfully parsed as JSON!")
        except json.JSONDecodeError as e:
            print(f"❌ Direct JSON parse failed: {e}")
            
            # Strategy 3: Try to extract JSON from text
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
            if json_match:
                print(f"✅ Found JSON-like pattern (length: {len(json_match.group(0))} chars)")
                try:
                    output = json.loads(json_match.group(0))
                    print("✅ Successfully parsed extracted JSON!")
                except json.JSONDecodeError as e2:
                    print(f"❌ Extracted JSON parse failed: {e2}")
                    print(f"📝 Extracted text:\n{json_match.group(0)[:200]}...")
        
        # Display results
        if output:
            print("\n" + "="*80)
            print("✅ PARSED OUTPUT:")
            print("="*80)
            print(json.dumps(output, indent=2))
            print("="*80)
            
            # Check structure
            print("\n📋 Structure Check:")
            print(f"  Summary items: {len(output.get('summary', []))}")
            print(f"  Actions: {len(output.get('actions', []))}")
            print(f"  Medications: {len(output.get('medications', []))}")
            print(f"  Glossary terms: {len(output.get('glossary', []))}")
        else:
            print("\n" + "="*80)
            print("⚠️  JSON PARSING FAILED - Using text extraction")
            print("="*80)
            
            # Use text extraction
            from app import parse_text_to_structure
            output = parse_text_to_structure(cleaned)
            print("\n📋 Extracted Structure:")
            print(json.dumps(output, indent=2))
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Error calling model: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_model_with_sample_text()

