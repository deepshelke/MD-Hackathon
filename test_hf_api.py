"""
Test script to verify Hugging Face API works with a sample medical note.
Uses huggingface_hub InferenceClient (recommended approach).
"""
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_huggingface_api():
    """Test Hugging Face Inference API with a sample medical note."""
    print("🧪 Testing Hugging Face API...\n")
    
    # Get token
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN not found in .env file")
        print("   Add: HF_TOKEN=your_token_here")
        return False
    
    print(f"✅ HF Token found (starts with: {hf_token[:10]}...)\n")
    
    # Try to import huggingface_hub
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        print("❌ huggingface_hub not installed")
        print("   Installing...")
        import subprocess
        subprocess.check_call(["pip", "install", "huggingface_hub"])
        from huggingface_hub import InferenceClient
    
    # Model name
    model_name = "johnsnowlabs/JSL-MedLlama-3-8B-v2.0"
    
    print(f"📡 Connecting to: {model_name}\n")
    
    # Sample medical note (simplified for testing)
    sample_note = """Patient admitted with chest pain. 
    Diagnosed with myocardial infarction. 
    Treated with aspirin and atorvastatin. 
    Discharged with follow-up in 1 week."""
    
    # Simple prompt for testing
    test_prompt = f"""System: You are a medical communication specialist. Convert this medical note into simple, patient-friendly language. Target 6th-8th grade reading level. Return JSON with summary, actions, medications, and glossary.

User: Medical Note:
{sample_note}

Assistant:"""
    
    print("📤 Sending request to Hugging Face API...")
    print("⏳ This may take 30-60 seconds on first request (model loading)...\n")
    
    try:
        # Create InferenceClient
        client = InferenceClient(model=model_name, token=hf_token)
        
        # Make request
        response = client.text_generation(
            prompt=test_prompt,
            max_new_tokens=500,
            temperature=0.2,
            return_full_text=False
        )
        
        print("✅ API Response received!\n")
        print("="*60)
        print("📝 MODEL OUTPUT:")
        print("="*60)
        
        generated_text = response.strip()
        print(generated_text)
        print("="*60)
        
        # Try to parse as JSON
        try:
            cleaned = generated_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            parsed = json.loads(cleaned)
            print("\n✅ Successfully parsed as JSON!")
            print("\n📋 Parsed Structure:")
            print(json.dumps(parsed, indent=2))
        except json.JSONDecodeError:
            print("\n⚠️  Response is not valid JSON (this is okay for testing)")
            print("   The model is working, but may need better prompting")
        
        print("\n" + "="*60)
        print("✅ Hugging Face API is working!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n⚠️  Possible issues:")
        print("1. Model may not be available via free Inference API")
        print("2. You may need to accept model terms on Hugging Face")
        print("3. Model may require Inference Endpoints (paid)")
        print("\n💡 Try:")
        print("1. Visit: https://huggingface.co/johnsnowlabs/JSL-MedLlama-3-8B-v2.0")
        print("2. Accept model terms if prompted")
        print("3. Wait a few minutes and try again")
        return False

if __name__ == "__main__":
    success = test_huggingface_api()
    
    if success:
        print("\n🎉 Test passed! Your Hugging Face API is working correctly.")
        print("\nNext steps:")
        print("1. Wait for your teammate to add data to Firestore")
        print("2. Test the full pipeline with: python example_usage.py")
    else:
        print("\n⚠️  Test failed. Please check:")
        print("1. Your HF_TOKEN in .env file")
        print("2. Your internet connection")
        print("3. If model is loading, wait 30-60 seconds and try again")

