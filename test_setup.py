"""
Test script to verify environment setup.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_setup():
    """Test if all required environment variables are set."""
    print("🔍 Testing Environment Setup...\n")
    
    # Check HF_TOKEN
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        print(f"✅ HF_TOKEN: Found (starts with: {hf_token[:10]}...)")
    else:
        print("❌ HF_TOKEN: Not found in .env file")
        print("   Add: HF_TOKEN=your_token_here")
    
    # Check FIREBASE_CREDENTIALS_PATH
    firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if firebase_path:
        print(f"✅ FIREBASE_CREDENTIALS_PATH: {firebase_path}")
        
        # Check if file exists
        if os.path.exists(firebase_path):
            print(f"   ✅ File exists at: {firebase_path}")
        else:
            print(f"   ❌ File NOT found at: {firebase_path}")
            print(f"   Make sure the path is correct!")
    else:
        print("❌ FIREBASE_CREDENTIALS_PATH: Not found in .env file")
        print("   Add: FIREBASE_CREDENTIALS_PATH=./credentials/your-file.json")
    
    print("\n" + "="*50)
    
    # Summary
    if hf_token and firebase_path and os.path.exists(firebase_path):
        print("✅ All setup looks good! You're ready to go.")
        print("\nNext steps:")
        print("1. Wait for your teammate to add data to Firestore")
        print("2. Update example_usage.py with a real note_id")
        print("3. Run: python example_usage.py")
    else:
        print("⚠️  Please fix the issues above before proceeding.")
    
    print("="*50)

if __name__ == "__main__":
    test_setup()

