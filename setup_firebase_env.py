"""
Helper script to convert Firebase JSON credentials to environment variables.
This is useful for deployment platforms that prefer environment variables over file paths.
"""
import json
import os
import sys
import base64

def json_to_env_vars(json_file_path: str):
    """
    Convert Firebase JSON credentials file to environment variable format.
    
    Args:
        json_file_path: Path to Firebase service account JSON file
    """
    if not os.path.exists(json_file_path):
        print(f"❌ Error: File not found: {json_file_path}")
        return
    
    print(f"📖 Reading Firebase credentials from: {json_file_path}")
    
    try:
        with open(json_file_path, 'r') as f:
            creds = json.load(f)
        
        print("\n✅ Firebase Credentials Environment Variables:")
        print("=" * 60)
        print("\n# Copy these to your hosting platform's environment variables:\n")
        
        print(f"FIREBASE_PROJECT_ID={creds.get('project_id', '')}")
        print(f"FIREBASE_CLIENT_EMAIL={creds.get('client_email', '')}")
        print(f"FIREBASE_PRIVATE_KEY_ID={creds.get('private_key_id', '')}")
        print(f"FIREBASE_PRIVATE_KEY={creds.get('private_key', '').replace(chr(10), '\\n')}")
        
        print("\n" + "=" * 60)
        print("\n💡 Alternative: Base64 encoded JSON (for platforms that prefer single env var):\n")
        
        # Base64 encode the entire JSON
        json_str = json.dumps(creds)
        encoded = base64.b64encode(json_str.encode()).decode()
        print(f"FIREBASE_CREDENTIALS_JSON_B64={encoded}")
        
        print("\n" + "=" * 60)
        print("\n✅ Done! Copy the environment variables above to your hosting platform.")
        print("   The FirestoreClient will automatically use these if FIREBASE_CREDENTIALS_PATH is not set.")
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON file: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python setup_firebase_env.py <path-to-firebase-json>")
        print("\nExample:")
        print("  python setup_firebase_env.py ./credentials/firebase-service-account.json")
        sys.exit(1)
    
    json_file_path = sys.argv[1]
    json_to_env_vars(json_file_path)

