# CareNotes

A web application that simplifies complex medical discharge notes into patient-friendly language using AI. Built with Flask, Hugging Face Inference API, and Firestore.

## 🚀 How to Run This Repository - Step by Step Guide

Follow these steps to set up and run CareNotes on your local machine:

### Prerequisites
Before you begin, make sure you have:
- **Python 3.11+** installed on your system
- **Git** installed
- **pip** (Python package manager)
- Access to Firebase credentials (contact Deep for access)
- Hugging Face API token (contact Deep for access)

---

### Step 1: Clone the Repository

Open your terminal/command prompt and run:

```bash
git clone https://github.com/deepshelke/MD-Hackathon.git
cd MD-Hackathon
```

This will download the repository and navigate into the project directory.

---

### Step 2: Create a Virtual Environment (Recommended)

It's best practice to use a virtual environment to isolate project dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt, indicating the virtual environment is active.

---

### Step 3: Install Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- Google Cloud Firestore (database client)
- Hugging Face Hub (AI API client)
- And all other dependencies

**Note:** This may take a few minutes depending on your internet connection.

---

### Step 4: Set Up Environment Variables

**Important:** Contact Deep (deep) to obtain the following credentials:
- Firebase service account JSON file
- Hugging Face API token

#### 4.1: Create `.env` File

Create a `.env` file in the root directory of the project:

```bash
# On macOS/Linux:
touch .env

# On Windows:
type nul > .env
```

#### 4.2: Add Environment Variables

Open the `.env` file in a text editor and add:

```bash
FIREBASE_CREDENTIALS_PATH=./credentials/firebase-service-account.json
HF_TOKEN=your_huggingface_token_here
```

**Replace:**
- `your_huggingface_token_here` with your actual Hugging Face API token
- Make sure the Firebase credentials file path is correct

#### 4.3: Add Firebase Credentials

1. Place your Firebase service account JSON file in the `credentials/` directory
2. If the `credentials/` folder doesn't exist, create it:
   ```bash
   mkdir credentials
   ```
3. Copy your Firebase JSON file to `credentials/firebase-service-account.json`

**Alternative:** You can also set Firebase credentials using individual environment variables:
```bash
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=your-client-email
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY=your-private-key
```

---

### Step 5: Verify Installation

Check that everything is set up correctly:

```bash
# Verify Python version (should be 3.11+)
python --version

# Verify Flask is installed
python -c "import flask; print(flask.__version__)"

# Verify Firestore client is installed
python -c "import google.cloud.firestore; print('Firestore installed')"

# Verify Hugging Face client is installed
python -c "import huggingface_hub; print('Hugging Face Hub installed')"
```

If all commands run without errors, you're ready to proceed!

---

### Step 6: Run the Application

Start the Flask development server:

```bash
python run.py
```

You should see output like:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

**Note:** The application runs on port 5000 by default. If port 5000 is already in use, you'll see an error. In that case, you can:
- Stop the other application using port 5000, or
- Modify `run.py` to use a different port

---

### Step 7: Access the Web Interface

1. Open your web browser
2. Navigate to: `http://localhost:5000`
3. You should see the CareNotes interface with:
   - Input fields for Note ID and HADM ID
   - A "Simplify" button

---

### Step 8: Test the Application

1. **Get Test IDs:** Contact Deep to get sample Note ID and HADM ID from Firestore, or use the `patients_list.csv` file if available

2. **Enter IDs:**
   - Note ID: e.g., `10000032-DS-21`
   - HADM ID: e.g., `22595853`

3. **Click "Simplify"** button

4. **Wait for processing** (this may take 10-30 seconds as it:
   - Fetches the note from Firestore
   - Sends it to MedLlama-3 AI model
   - Generates simplified output)

5. **View Results:** You should see the simplified medical note with sections:
   - 📋 Summary
   - ✅ Actions Needed
   - 💊 Medications Explained
   - ⚠️ Safety Information
   - 📖 Glossary

---

### Step 9: Stop the Application

When you're done testing, stop the server by pressing:
```
Ctrl + C
```
in your terminal.

---

## ✅ Success Checklist

You've successfully set up CareNotes if:
- ✅ Repository cloned
- ✅ Virtual environment created and activated
- ✅ Dependencies installed
- ✅ `.env` file created with credentials
- ✅ Firebase credentials file in place
- ✅ Application starts without errors
- ✅ Web interface loads at `http://localhost:5000`
- ✅ You can simplify a medical note successfully

---

## 🆘 Common Issues and Solutions

### Issue: "Module not found" error
**Solution:** Make sure you activated the virtual environment and installed dependencies:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Issue: "Port 5000 already in use"
**Solution:** Stop other applications using port 5000, or change the port in `run.py`

### Issue: "Firebase credentials not found"
**Solution:** 
- Verify the path in `.env` is correct
- Check that the JSON file exists in the `credentials/` folder
- Ensure the file has proper read permissions

### Issue: "HF_TOKEN not set"
**Solution:** 
- Verify your `.env` file has `HF_TOKEN=your_actual_token`
- Make sure there are no spaces around the `=` sign
- Restart the application after updating `.env`

### Issue: "Note not found in Firestore"
**Solution:** 
- Verify the Note ID and HADM ID are correct
- Check that the note exists in Firestore
- Verify Firebase credentials have read permissions

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

The application processes real medical notes from Firestore. Enter a valid Note ID and HADM ID to test the simplification functionality.

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
