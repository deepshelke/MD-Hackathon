# MD-Hackathon: Medical Note Simplification

Convert complex medical discharge notes into patient-friendly language using JSL-MedLlama-3-8B-v2.0.

## Architecture

```
Firestore (Processed Notes)
    ↓
[Fetch via Firestore Client]
    ↓
[Sectionizer] → [Prompt Builder] → [MedLlama-3 via HF API] → [Post-Processor]
    ↓
[Simplified Output: JSON with summary, actions, medications, glossary]
```

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your credentials:
# - FIREBASE_CREDENTIALS_PATH: Path to Firebase service account JSON
# - HF_TOKEN: Your Hugging Face API token
```

### 2. Setup Hugging Face

1. Get your API token from [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Add it to `.env` file: `HF_TOKEN=your_token_here`
3. See [HUGGINGFACE_SETUP.md](HUGGINGFACE_SETUP.md) for detailed instructions

### 3. Setup Firebase Credentials

1. Copy your Firebase service account JSON to `credentials/` directory
2. Update `.env` with the path: `FIREBASE_CREDENTIALS_PATH=./credentials/your-file.json`

### 4. Run Example

**Terminal/Command Line:**
```bash
python example_usage.py
```

**Streamlit UI (Recommended for Demo):**
```bash
streamlit run src/ui_app.py
```

Or use the helper script:
```bash
python run_ui.py
```

The UI will open in your browser at `http://localhost:8501`

## Why We Use Hugging Face Inference API (Not Local Model)

**We're using the API approach** (not loading the model locally) because:

1. ✅ **Your MacBook Air M2 (8GB RAM)** can't handle an 8B parameter model locally
2. ✅ **No infrastructure setup** - just API calls
3. ✅ **Fast to get started** - perfect for hackathon
4. ✅ **Reliable** - managed by Hugging Face
5. ✅ **Cost-effective** - pay per request (~$0.01-0.05 per note)

**The code uses `requests` to call the API** - no need for `transformers` or `pipeline` locally!

## Project Structure

```
MD-Hackathon/
├── src/
│   ├── firestore_client.py    # Fetch notes from Firestore
│   ├── prompts.py             # Heavy prompt engineering
│   ├── model_client.py        # Hugging Face Inference API client
│   ├── pipeline.py            # Main orchestration
│   └── checks.py              # Validation & metrics (coming soon)
├── credentials/               # Firebase service account JSON (gitignored)
├── data/                      # MIMIC-IV data (when available)
├── output/                    # Processed results
├── example_usage.py           # Example script
├── requirements.txt           # Dependencies
├── .env                       # Environment variables (gitignored)
└── README.md                  # This file
```

## Components

### 1. Firestore Client (`src/firestore_client.py`)
- Fetches processed discharge notes from Firestore
- Supports single note, batch, and filtered queries

### 2. Prompt Builder (`src/prompts.py`)
- Heavy prompt engineering for patient-friendly output
- System prompt with strict rules (6th-8th grade reading level)
- User template with structured sections

### 3. Model Client (`src/model_client.py`)
- Calls Hugging Face Inference API
- Handles retries, rate limiting, model loading
- No local model loading required!

### 4. Pipeline (`src/pipeline.py`)
- Orchestrates: Fetch → Prompt → LLM → Output
- Returns structured JSON with simplified note

## Usage

```python
from src.pipeline import SimplificationPipeline

# Initialize
pipeline = SimplificationPipeline(
    firestore_credentials_path="./credentials/firebase.json",
    hf_api_token="your_hf_token"
)

# Process a note
result = pipeline.process_note("note_id_123")

# Check result
if result["error"]:
    print(f"Error: {result['error']}")
else:
    print(result["parsed_output"])  # Simplified JSON
```

## UI Features

The Streamlit UI provides:
- 📝 **Input Form**: Enter Note ID from Firestore
- 📋 **Plain Summary**: Bullet points of what happened
- ✅ **What To Do Next**: Actions with timeline and who to contact
- 💊 **Your Medications**: Detailed medication information
- 📖 **Terms Explained**: Glossary of medical terms
- 📊 **Reading Level**: Grade level indicator

## Next Steps

- [ ] Add sectionizer for raw note text
- [ ] Add post-processor (JSON validation, readability checks)
- [ ] Add FastAPI endpoint
- [x] Add Streamlit UI ✅
- [ ] Add GCS storage for results

## Resources

- [MIMIC-IV-Note Dataset](https://physionet.org/content/mimic-iv-note/2.2/)
- [JSL-MedLlama-3-8B-v2.0 Model](https://huggingface.co/johnsnowlabs/JSL-MedLlama-3-8B-v2.0)
- [Hugging Face Setup Guide](HUGGINGFACE_SETUP.md)
