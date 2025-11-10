"""
Flask application for CareNotes - Simplifying medical discharge notes.
"""
import os
import json
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from src.pipeline import SimplificationPipeline

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize pipeline (lazy loading)
pipeline = None

def get_pipeline():
    """Get or initialize the pipeline."""
    global pipeline
    if pipeline is None:
        try:
            hf_token = os.getenv("HF_TOKEN")
            firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            
            if not hf_token:
                raise Exception("HF_TOKEN environment variable is not set")
            
            pipeline = SimplificationPipeline(
                firestore_credentials_path=firebase_path,
                hf_api_token=hf_token,
                hf_model_name="johnsnowlabs/JSL-MedLlama-3-8B-v2.0"
            )
        except Exception as e:
            print(f"ERROR: Failed to initialize pipeline: {str(e)}")
            raise Exception(f"Failed to initialize pipeline: {str(e)}")
    return pipeline

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors gracefully."""
    return jsonify({
        'success': False,
        'error': 'Internal server error. Please try again later.'
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all exceptions gracefully."""
    return jsonify({
        'success': False,
        'error': f'An error occurred: {str(e)}'
    }), 500

@app.route('/api/simplify', methods=['POST'])
def simplify_note():
    """API endpoint to simplify a medical note."""
    try:
        data = request.get_json()
        note_id = data.get('note_id', '').strip()
        hadm_id = data.get('hadm_id', '').strip()
        
        if not note_id or not hadm_id:
            return jsonify({
                'success': False,
                'error': 'Both Note ID and HADM ID are required.'
            }), 400
        
        # Get pipeline and process note
        pipeline = get_pipeline()
        result = pipeline.process_note(note_id=note_id, hadm_id=hadm_id)
        
        # Get simplified output
        simplified_output = result.get("simplified_output", "")
        
        # Check for errors (but only if there's no output)
        if result.get("error"):
            error_msg = result['error']
            
            # If we have output despite an error (like JSON parse error), ignore the error
            if simplified_output and len(simplified_output.strip()) > 0:
                # We have output, so the "error" is likely just a JSON parse failure
                # which is fine since we expect plain text
                pass
            else:
                # Real error - no output
                # Make error message more helpful
                if "not found in Firestore" in error_msg:
                    error_msg = f"Note '{note_id}' not found in Firestore. Please check:\n1. The Note ID is correct\n2. Your teammate has added data to Firestore\n3. The collection name is correct"
                elif "API requires payment" in error_msg or "free tier limit" in error_msg.lower():
                    error_msg = "Hugging Face API free tier limit reached. Please add API credits."
                elif "402" in error_msg or "Payment Required" in error_msg:
                    error_msg = "Hugging Face API requires payment. Please add API credits."
                elif "empty response" in error_msg.lower():
                    error_msg = "Model returned empty response. Please try again."
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 400
        
        # Return simplified output (model returns plain text, not JSON)
        if not simplified_output or len(simplified_output.strip()) == 0:
            return jsonify({
                'success': False,
                'error': 'Model returned empty response. Please try again.'
            }), 400
        
        # Return the simplified output directly
        # Flask automatically sets Content-Length, don't set it manually
        return jsonify({
            'success': True,
            'data': {
                'simplified_output': simplified_output
            }
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = str(e)
        
        # Log error for debugging
        print(f"ERROR in simplify_note: {error_msg}")
        print(f"Traceback: {error_details}")
        
        # Provide user-friendly error messages
        if "Failed to initialize pipeline" in error_msg:
            user_error = "Server configuration error. Please check server logs."
        elif "HF_TOKEN" in error_msg or "environment variable" in error_msg.lower():
            user_error = "Configuration error: Missing environment variables."
        elif "Firebase" in error_msg or "FIREBASE" in error_msg:
            user_error = "Configuration error: Firebase credentials not set."
        else:
            user_error = f"An error occurred: {error_msg}"
        
        return jsonify({
            'success': False,
            'error': user_error
        }), 500

def parse_text_to_structure(text):
    """Parse text output and try to extract structured information."""
    import re
    
    result = {
        "summary": [],
        "actions": [],
        "medications": [],
        "glossary": []
    }
    
    # Try to extract summary bullets
    summary_patterns = [
        r'[•\-\*]\s*(.+?)(?=\n|$)',
        r'\d+\.\s*(.+?)(?=\n|$)',
        r'Summary[:\s]*(.+?)(?=Actions|Medications|Glossary|$)',
    ]
    
    for pattern in summary_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            result["summary"] = [m.strip() for m in matches[:6]]
            break
    
    # If no summary found, use first few sentences
    if not result["summary"]:
        sentences = re.split(r'[.!?]+\s+', text)
        result["summary"] = [s.strip() for s in sentences[:6] if s.strip() and len(s.strip()) > 20]
    
    # Try to extract medications
    med_patterns = [
        r'(?:medication|prescribed|take)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(?:\d+\s*(?:mg|mcg|units?))',
        r'([A-Za-z]+)\s+\d+\s*(?:mg|mcg|units?)',
    ]
    
    for pattern in med_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            result["medications"] = [{"name": m, "why": "not specified", "how_to_take": "not specified", 
                                     "schedule": "not specified", "cautions": "not specified"} 
                                    for m in matches[:10]]
            break
    
    # Try to extract actions
    action_keywords = ['follow up', 'appointment', 'see doctor', 'call', 'return']
    for keyword in action_keywords:
        if keyword in text.lower():
            result["actions"].append({
                "task": f"Follow up as instructed",
                "when": "not specified",
                "who": "not specified"
            })
            break
    
    # Try to extract glossary terms
    medical_terms = ['myocardial infarction', 'STEMI', 'PCI', 'stent', 'hypertension', 
                     'diabetes', 'hyperlipidemia', 'troponin', 'echocardiography']
    for term in medical_terms:
        if term.lower() in text.lower():
            result["glossary"].append({
                "term": term,
                "plain": "Medical term - see simplified summary for explanation"
            })
    
    return result

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Use PORT environment variable if available (for production hosting)
    port = int(os.environ.get('PORT', 5000))
    # Only enable debug in development
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)

