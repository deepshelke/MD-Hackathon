"""
Simple test to check if Hugging Face API is working.
"""
import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    print("❌ HF_TOKEN not found")
    exit(1)

print("🧪 Testing Hugging Face API with simple prompt...\n")

client = InferenceClient(
    model="johnsnowlabs/JSL-MedLlama-3-8B-v2.0",
    token=hf_token
)

# Test 1: Very simple prompt
print("Test 1: Very simple prompt")
try:
    response1 = client.text_generation(
        prompt="What is a heart attack?",
        max_new_tokens=50,
        temperature=0.2,
        return_full_text=False
    )
    print(f"✅ Response: {response1}")
    print(f"   Length: {len(str(response1))} chars\n")
except Exception as e:
    print(f"❌ Error: {e}\n")

# Test 2: Medical prompt
print("Test 2: Medical prompt")
try:
    response2 = client.text_generation(
        prompt="Explain myocardial infarction in simple terms:",
        max_new_tokens=100,
        temperature=0.2,
        return_full_text=False
    )
    print(f"✅ Response: {response2}")
    print(f"   Length: {len(str(response2))} chars\n")
except Exception as e:
    print(f"❌ Error: {e}\n")

# Test 3: JSON prompt
print("Test 3: JSON format prompt")
try:
    response3 = client.text_generation(
        prompt="Output JSON: {\"summary\": \"test\"}",
        max_new_tokens=50,
        temperature=0.2,
        return_full_text=False
    )
    print(f"✅ Response: {response3}")
    print(f"   Length: {len(str(response3))} chars\n")
except Exception as e:
    print(f"❌ Error: {e}\n")

