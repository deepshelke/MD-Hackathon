# .env File Setup Guide

## Your .env file should look like this:

```env
HF_TOKEN=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
FIREBASE_CREDENTIALS_PATH=./credentials/md-hackathon-15fe7-firebase-adminsdk-fbsvc-7c21cfeeba.json
```

## Important Rules:

1. **NO spaces around the `=` sign**
   - ✅ Correct: `HF_TOKEN=your_token`
   - ❌ Wrong: `HF_TOKEN = your_token`

2. **NO quotes around values** (unless path has spaces)
   - ✅ Correct: `HF_TOKEN=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`
   - ❌ Wrong: `HF_TOKEN="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"`

3. **File must be named exactly `.env`** (with the dot at the start)

4. **File must be in the project root** (same folder as `example_usage.py`)

## Steps to Fix:

1. Open your `.env` file
2. Make sure it has these two lines (exactly as shown above):
   ```
   HF_TOKEN=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
   FIREBASE_CREDENTIALS_PATH=./credentials/md-hackathon-15fe7-firebase-adminsdk-fbsvc-7c21cfeeba.json
   ```

3. Make sure:
   - No extra spaces
   - No quotes
   - File is saved

4. Run the test again:
   ```bash
   python test_setup.py
   ```

## If Still Not Working:

1. Check the file location:
   ```bash
   ls -la .env
   ```
   Should show the file in the project root.

2. Check file contents (carefully - don't share your token!):
   ```bash
   cat .env
   ```

3. Make sure the Firebase credentials file exists:
   ```bash
   ls -la credentials/md-hackathon-15fe7-firebase-adminsdk-fbsvc-7c21cfeeba.json
   ```

If it doesn't exist, copy it:
```bash
mkdir -p credentials
cp /Users/deepshelke/Downloads/md-hackathon-15fe7-firebase-adminsdk-fbsvc-7c21cfeeba.json credentials/
```

