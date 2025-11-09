"""
Flask application for Medical Note Simplification.
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
            pipeline = SimplificationPipeline(
                firestore_credentials_path=os.getenv("FIREBASE_CREDENTIALS_PATH"),
                hf_api_token=os.getenv("HF_TOKEN"),
                hf_model_name="johnsnowlabs/JSL-MedLlama-3-8B-v2.0"
            )
        except Exception as e:
            raise Exception(f"Failed to initialize pipeline: {str(e)}")
    return pipeline

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/simplify', methods=['POST'])
def simplify_note():
    """API endpoint to simplify a medical note."""
    try:
        data = request.get_json()
        note_id = data.get('note_id', '').strip()
        hadm_id = data.get('hadm_id', '').strip()
        note_text = data.get('note_text', '').strip()  # For test mode
        
        # Test mode: if note_text is provided, use it directly
        if note_text:
            return simplify_text_directly(note_text)
        
        if not note_id or not hadm_id:
            return jsonify({
                'success': False,
                'error': 'Both Note ID and HADM ID are required. If you want to test with sample text, provide note_text instead.'
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
                    error_msg = "Hugging Face API free tier limit reached. Please add API credits or use Test Mode to see sample output."
                elif "402" in error_msg or "Payment Required" in error_msg:
                    error_msg = "Hugging Face API requires payment. Please add API credits or use Test Mode to see sample output."
                elif "empty response" in error_msg.lower():
                    error_msg = "Model returned empty response. Please try again or use Test Mode to see sample output."
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 400
        
        # Return simplified output (model returns plain text, not JSON)
        if not simplified_output or len(simplified_output.strip()) == 0:
            return jsonify({
                'success': False,
                'error': 'Model returned empty response. Please try again or use Test Mode to see sample output.'
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
        print(f"Error in simplify_note: {str(e)}")
        print(f"Traceback: {error_details}")
        return jsonify({
            'success': False,
            'error': str(e),
            'details': error_details if app.debug else None
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

def simplify_text_directly(note_text):
    """Simplify note text directly without Firestore (test mode)."""
    try:
        from src.prompts import PromptBuilder
        from src.model_client import HuggingFaceClient
        
        # Create simple sections from text
        sections = {
            "Diagnoses": note_text,
            "Hospital Course": "",
            "Discharge Medications": "",
            "Follow-up": "",
            "Allergies": "",
            "Pending Tests": "",
            "Diet/Activity": ""
        }
        
        # Build prompts
        prompt_builder = PromptBuilder()
        prompts = prompt_builder.build_full_prompt(sections)
        
        # Call LLM
        hf_client = HuggingFaceClient(
            model_name="johnsnowlabs/JSL-MedLlama-3-8B-v2.0",
            api_token=os.getenv("HF_TOKEN")
        )
        
        simplified_output = hf_client.simplify_note(
            system_prompt=prompts["system"],
            user_prompt=prompts["user"],
            max_tokens=900,
            temperature=0.2
        )
        
        # Try to parse JSON with multiple strategies
        output = None
        cleaned = simplified_output.strip()
        
        # Strategy 1: Remove markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        # Strategy 2: Try to find JSON object in the text
        try:
            # Try direct parsing first
            output = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            import re
            # Look for JSON object pattern
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    output = json.loads(json_match.group(0))
                except:
                    pass
            
            # If still no JSON, try to extract structured information from text
            if output is None:
                # Try to parse the text and extract information
                output = parse_text_to_structure(cleaned)
                output["_raw_output"] = simplified_output
                output["_note"] = "Model output was not in JSON format. Extracted information from text."
        
        return jsonify({
            'success': True,
            'data': output
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Test mode error: {str(e)}'
        }), 500

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

