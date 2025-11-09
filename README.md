# Medical Note Simplifier

A web application that simplifies complex medical discharge notes into patient-friendly language using AI. Built with Flask, Hugging Face Inference API, and Firestore.

## 🚀 Quick Start - Step by Step

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd MD-Hackathon
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Set Up Environment Variables
**For environment variables and credentials, please contact Deep (deep) to get access to:**
- `FIREBASE_CREDENTIALS_PATH`: Path to Firebase service account JSON file
- `HF_TOKEN`: Your Hugging Face API token

Create a `.env` file in the root directory:
```bash
FIREBASE_CREDENTIALS_PATH=./credentials/firebase-service-account.json
HF_TOKEN=your_huggingface_token_here
```

### Step 4: Run the Application
```bash
python run.py
```

The application will start on `http://localhost:5000`

### Step 5: Access the Web Interface
Open your browser and navigate to:
```
http://localhost:5000
```

Enter a Note ID and HADM ID from Firestore, then click "Simplify Note" to see the simplified output.

---

## 📋 Overview

This application transforms complex medical discharge notes into patient-friendly language that a 6th-8th grade reading level can understand. It uses the JSL-MedLlama-3-8B-v2.0 model via Hugging Face Inference API to simplify medical terminology and structure information in an easy-to-understand format.

## 🏗️ Architecture

```
Firestore (Processed Notes)
    ↓
[Firestore Client] → Fetch discharge notes
    ↓
[Sectionizer] → Extract and organize note sections
    ↓
[Prompt Builder] → Create prompts with Llama 3 chat template format
    ↓
[MedLlama-3 via HF API] → Generate simplified output
    ↓
[Frontend] → Display formatted results
```

## 📁 Project Structure

```
MD-Hackathon/
├── src/
│   ├── firestore_client.py      # Firestore database client
│   ├── model_client.py          # Hugging Face Inference API client
│   ├── pipeline.py              # Main orchestration pipeline
│   ├── prompts.py               # Prompt engineering for MedLlama-3
│   ├── sectionizer.py            # Extract sections from medical notes
│   └── on_demand_processor.py  # On-demand note processing
├── static/
│   ├── css/
│   │   └── style.css            # Frontend styling
│   └── js/
│       └── main.js              # Frontend JavaScript logic
├── templates/
│   └── index.html               # Main web interface
├── data_preprocessing/          # Data preprocessing scripts
├── app.py                       # Flask application
├── run.py                       # Application entry point
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🔧 Components

### 1. Firestore Client (`src/firestore_client.py`)
- Fetches processed discharge notes from Firestore database
- Supports single note queries by Note ID and HADM ID
- Handles batch operations and filtering

### 2. Model Client (`src/model_client.py`)
- Communicates with Hugging Face Inference API
- Uses Llama 3 chat template format: `<|begin_of_text|><|start_header_id|>system<|end_header_id|>...`
- Handles API calls, error handling, and response parsing
- Model: `johnsnowlabs/JSL-MedLlama-3-8B-v2.0`

### 3. Prompt Builder (`src/prompts.py`)
- Heavy prompt engineering for patient-friendly output
- System prompt with strict simplification rules
- User template with structured sections
- Formats prompts using Llama 3 chat template format

### 4. Pipeline (`src/pipeline.py`)
- Main orchestration: Fetch → Sectionize → Prompt → LLM → Output
- Processes medical notes end-to-end
- Returns simplified output in structured format

### 5. Sectionizer (`src/sectionizer.py`)
- Extracts structured sections from raw medical notes
- Identifies: Diagnoses, Hospital Course, Medications, Allergies, etc.
- Organizes content for prompt building

## 🎯 Features

### Web Interface
- **Clean, modern UI** with collapsible sections
- **Real-time processing** of medical notes
- **Formatted output** with emojis and clear structure
- **Test mode** for demonstration without API calls

### Output Format
The simplified output includes:
- **📋 Summary**: 3-5 bullet points explaining what happened during the hospital stay
- **✅ Actions Needed**: What the patient needs to do after discharge
- **💊 Medications Explained**: Each medication with what it does and how to take it
- **⚠️ Safety Information**: Allergies and warning signs
- **📖 Glossary**: Medical terms defined in simple language

## 🔑 Environment Variables

**Contact Deep (deep) to obtain the following environment variables:**

- `FIREBASE_CREDENTIALS_PATH`: Path to Firebase service account JSON file
- `HF_TOKEN`: Hugging Face API token for accessing MedLlama-3 model

## 📦 Dependencies

Key dependencies:
- `flask>=3.0.0` - Web framework
- `google-cloud-firestore>=2.13.0` - Firestore database client
- `huggingface_hub>=0.20.0` - Hugging Face API client
- `python-dotenv>=1.0.0` - Environment variable management
- `pandas>=2.0.0` - Data processing
- `textstat>=0.7.3` - Readability metrics

See `requirements.txt` for complete list.

## 🚀 Usage

### Web Application
1. Start the Flask server: `python run.py`
2. Open browser to `http://localhost:5000`
3. Enter Note ID and HADM ID
4. Click "Simplify Note"
5. View the simplified output

### API Endpoint
```bash
POST /api/simplify
Content-Type: application/json

{
  "note_id": "10000032-DS-21",
  "hadm_id": "22595853"
}
```

### Python API
```python
from src.pipeline import SimplificationPipeline

# Initialize pipeline
pipeline = SimplificationPipeline(
    firestore_credentials_path=os.getenv("FIREBASE_CREDENTIALS_PATH"),
    hf_api_token=os.getenv("HF_TOKEN")
)

# Process a note
result = pipeline.process_note(
    note_id="10000032-DS-21",
    hadm_id="22595853"
)

# Access simplified output
if result.get("simplified_output"):
    print(result["simplified_output"])
```

## 🧪 Testing

The application includes a "Test Mode" checkbox that uses sample output without making API calls. This is useful for:
- Testing the frontend interface
- Demonstrating the application
- Avoiding API costs during development

## 🔒 Security Notes

- Environment variables are stored in `.env` (gitignored)
- Firebase credentials should never be committed
- API tokens should be kept secure
- Raw data directories (`raw_notes/`, `raw_dataset/`) are gitignored

## 📊 Data Processing

The repository includes scripts for processing medical notes:
- `upload_all_patients.py` - Upload processed notes to Firestore
- `process_18k_single_hadm_patients.py` - Process large batches of patients
- `data_preprocessing/` - Various preprocessing utilities

## 🐛 Troubleshooting

### Application won't start
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify environment variables are set correctly
- Ensure port 5000 is not in use

### API errors
- Verify `HF_TOKEN` is valid and has API access
- Check Hugging Face API status
- Review API rate limits

### Firestore connection issues
- Verify `FIREBASE_CREDENTIALS_PATH` points to valid credentials file
- Check Firebase project permissions
- Ensure Firestore database is accessible

## 📝 Model Details

- **Model**: JSL-MedLlama-3-8B-v2.0 (Johnsnowlabs)
- **Format**: Llama 3 chat template with special tokens
- **API**: Hugging Face Inference API
- **Input**: Structured medical note sections
- **Output**: Simplified patient-friendly language

## 🌐 Deployment

Want to host this app so your teammates can access it without downloading anything locally?

**Quick Deploy (5 minutes):**
- See [QUICK_DEPLOY_RENDER.md](QUICK_DEPLOY_RENDER.md) for step-by-step Render deployment
- See [DEPLOYMENT.md](DEPLOYMENT.md) for all hosting options (Render, Railway, PythonAnywhere, Google Cloud Run)

**Recommended:** [Render](https://render.com) - Free tier available, one-click deployment from GitHub, automatic HTTPS.

**Cost:** Free tier available (spins down after inactivity) or $7/month for always-on.

## 🤝 Contributing

For questions or issues, contact Deep (deep).

## 📄 License

See LICENSE file for details.

## 🙏 Acknowledgments

- MIMIC-IV-Note Dataset
- Johnsnowlabs for MedLlama-3 model
- Hugging Face for Inference API
