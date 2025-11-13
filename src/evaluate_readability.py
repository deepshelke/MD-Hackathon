"""
Readability Evaluation Script for MD-Hackathon Project
This script:
1. Generates a reproducible list of patient indices (1-250)
2. Reads note_id and hadm_id from patients_list.csv
3. Calculates readability scores (Flesch Reading Ease & Gunning Fog) for original discharge notes
4. Runs notes through the simplification model
5. Calculates readability scores for model outputs
6. Outputs results to a CSV file

IMPROVEMENTS FOR LIMITED API CALLS:
- Resume from checkpoint if output file exists
- Incremental saving after each patient
- Configurable number of patients (default: 5 for testing)
- Confirmation prompt before starting
"""

import os
import sys
import random
import argparse
import pandas as pd
import textstat
from pathlib import Path

# Add parent directory to path to import project modules
# (script is in src/, so parent is project root)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pipeline import SimplificationPipeline
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def generate_reproducible_indices(n=20, max_val=250, seed=42):
    """
    Generate a reproducible list of random integers.
    
    Args:
        n (int): Number of integers to generate
        max_val (int): Maximum value (inclusive range is 1 to max_val)
        seed (int): Random seed for reproducibility
    
    Returns:
        list: List of random integers
    """
    random.seed(seed)
    indices = random.sample(range(1, max_val + 1), n)
    return sorted(indices)


def clean_text_for_evaluation(text):
    """
    Clean text for readability evaluation by removing emojis and formatting.
    This ensures fair comparison - emojis should stay on frontend but not affect scores.
    
    Args:
        text (str): Text to clean
    
    Returns:
        str: Cleaned text without emojis
    """
    if not text or not isinstance(text, str):
        return text
    
    import re
    # Remove emojis (common medical note emojis: 📋 ✅ 💊 ⚠️ 📖)
    # This regex removes most common emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"   # dingbats
        "\U000024C2-\U0001F251"   # enclosed characters
        "]+", flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub('', text)
    
    # Also remove common emoji-like symbols used in the format
    cleaned = cleaned.replace('📋', '').replace('✅', '').replace('💊', '').replace('⚠️', '').replace('📖', '')
    
    return cleaned.strip()


def check_for_placeholders(text):
    """
    Check if text contains unfilled placeholders like [condition], [treatment], etc.
    
    Args:
        text (str): Text to check
    
    Returns:
        dict: Dictionary with placeholder info
    """
    if not text or not isinstance(text, str):
        return {'has_placeholders': False, 'placeholder_count': 0, 'placeholders': []}
    
    import re
    # Look for patterns like [word], [condition], [treatment], etc.
    placeholder_pattern = re.compile(r'\[([^\]]+)\]')
    placeholders = placeholder_pattern.findall(text)
    
    # Filter out common section headers that are not placeholders
    non_placeholder_sections = ['Diagnoses', 'Hospital Course', 'Discharge Medications', 
                                'Follow-up', 'Allergies', 'Pending Tests', 'Diet/Activity',
                                'History of Present Illness', 'Chief Complaint', 
                                'Past Medical History', 'Physical Exam', 'Pertinent Results',
                                'Discharge Instructions', 'Summary', 'Actions Needed',
                                'Medications Explained', 'Safety Information', 'Glossary']
    
    actual_placeholders = [p for p in placeholders if p not in non_placeholder_sections]
    
    return {
        'has_placeholders': len(actual_placeholders) > 0,
        'placeholder_count': len(actual_placeholders),
        'placeholders': actual_placeholders
    }


def calculate_readability_scores(text):
    """
    Calculate Flesch Reading Ease and Gunning Fog Index for given text.
    
    Args:
        text (str): Text to analyze
    
    Returns:
        dict: Dictionary containing readability scores
    """
    if not text or not isinstance(text, str) or len(text.strip()) == 0:
        return {
            'flesch_reading_ease': None,
            'gunning_fog': None
        }
    
    try:
        # Clean text before calculating (remove emojis for fair evaluation)
        cleaned_text = clean_text_for_evaluation(text)
        
        if not cleaned_text or len(cleaned_text.strip()) == 0:
            return {
                'flesch_reading_ease': None,
                'gunning_fog': None
            }
        
        flesch_score = textstat.flesch_reading_ease(cleaned_text)
        gunning_fog_score = textstat.gunning_fog(cleaned_text)
        
        return {
            'flesch_reading_ease': flesch_score,
            'gunning_fog': gunning_fog_score
        }
    except Exception as e:
        print(f"Error calculating readability scores: {e}")
        return {
            'flesch_reading_ease': None,
            'gunning_fog': None
        }


def load_patients_list(csv_path=None):
    """
    Load the patients list CSV file.
    
    Args:
        csv_path (str): Path to patients_list.csv (default: checks root and src/ directories)
    
    Returns:
        pd.DataFrame: DataFrame containing patient information
    """
    if csv_path is None:
        # Check multiple locations: root directory first, then src/
        project_root = Path(__file__).parent.parent
        possible_paths = [
            project_root / 'patients_list.csv',  # Root directory
            project_root / 'src' / 'patients_list.csv'  # src/ directory
        ]
        
        for path in possible_paths:
            if path.exists():
                csv_path = path
                break
        else:
            # If neither exists, default to src/ and let it fail with clear error
            csv_path = project_root / 'src' / 'patients_list.csv'
    
    try:
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} patients from {csv_path}")
        return df
    except FileNotFoundError:
        print(f"Error: Could not find {csv_path}")
        print("Please ensure patients_list.csv exists in either:")
        print("  - Root directory: patients_list.csv")
        print("  - src/ directory: src/patients_list.csv")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading patients list: {e}")
        sys.exit(1)


def load_existing_results(output_path):
    """
    Load existing results from CSV if it exists.
    
    Returns:
        pd.DataFrame: Existing results, or None if file doesn't exist
        set: Set of (note_id, hadm_id) tuples that are already processed
    """
    if os.path.exists(output_path):
        try:
            df = pd.read_csv(output_path)
            processed = set(zip(df['note_id'], df['hadm_id']))
            print(f"Found existing results: {len(df)} patients already processed")
            return df, processed
        except Exception as e:
            print(f"Warning: Could not load existing results: {e}")
            return None, set()
    return None, set()


def main():
    """
    Main function to execute the readability evaluation pipeline.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Evaluate readability of medical notes')
    parser.add_argument('--n', type=int, default=5, 
                       help='Number of patients to process (default: 5 for testing)')
    parser.add_argument('--max-val', type=int, default=250,
                       help='Maximum patient index (default: 250)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')
    parser.add_argument('--output', type=str, default='readability_evaluation_results.csv',
                       help='Output CSV file path (default: readability_evaluation_results.csv)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from existing results file (skip already processed patients)')
    parser.add_argument('--yes', action='store_true',
                       help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Medical Note Readability Evaluation")
    print("=" * 80)
    
    # Check for existing results
    existing_df, processed_set = load_existing_results(args.output) if args.resume else (None, set())
    
    # Step 1: Generate reproducible list of indices
    print(f"\nStep 1: Generating reproducible list of {args.n} patient indices...")
    indices = generate_reproducible_indices(n=args.n, max_val=args.max_val, seed=args.seed)
    print(f"Selected indices: {indices}")
    
    # Step 2: Load patients list
    print("\nStep 2: Loading patients list...")
    patients_df = load_patients_list()
    
    # Verify we have enough patients
    if len(patients_df) < max(indices):
        print(f"Warning: patients_list.csv only has {len(patients_df)} rows, "
              f"but we need at least {max(indices)} rows")
        # Adjust indices to fit available data
        indices = [i for i in indices if i <= len(patients_df)]
        print(f"Adjusted indices to: {indices}")
    
    # Select patients based on indices (adjusting for 0-based indexing)
    selected_patients = patients_df.iloc[[i-1 for i in indices]].copy()
    print(f"Selected {len(selected_patients)} patients")
    
    # Filter out already processed patients if resuming
    if args.resume and processed_set:
        initial_count = len(selected_patients)
        selected_patients = selected_patients[
            ~selected_patients.apply(lambda row: (row['note_id'], row['hadm_id']) in processed_set, axis=1)
        ]
        skipped = initial_count - len(selected_patients)
        if skipped > 0:
            print(f"Skipping {skipped} already processed patients")
            print(f"Remaining: {len(selected_patients)} patients to process")
    
    if len(selected_patients) == 0:
        print("\n✅ All patients have already been processed!")
        if existing_df is not None:
            print(f"Results available in: {args.output}")
        return
    
    # Confirmation prompt
    if not args.yes:
        print(f"\n⚠️  WARNING: This will make {len(selected_patients)} API calls to Hugging Face!")
        print(f"   Estimated cost: ~{len(selected_patients)} API calls")
        response = input(f"\nProceed with processing {len(selected_patients)} patients? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return
    
    # Step 3: Initialize the simplification pipeline
    print("\nStep 3: Initializing simplification pipeline...")
    try:
        pipeline = SimplificationPipeline(
            firestore_credentials_path=os.getenv("FIREBASE_CREDENTIALS_PATH"),
            hf_api_token=os.getenv("HF_TOKEN")
        )
        print("Pipeline initialized successfully")
    except Exception as e:
        print(f"Error initializing pipeline: {e}")
        print("Make sure your .env file contains valid FIREBASE_CREDENTIALS_PATH and HF_TOKEN")
        sys.exit(1)
    
    # Step 4 & 5: Process each patient and calculate readability scores
    print("\nStep 4-5: Processing patients and calculating readability scores...")
    results = list(existing_df.to_dict('records')) if existing_df is not None else []
    
    for patient_num, (idx, row) in enumerate(selected_patients.iterrows(), 1):
        note_id = row['note_id']
        hadm_id = row['hadm_id']
        
        print(f"\nProcessing patient {patient_num}/{len(selected_patients)}: "
              f"note_id={note_id}, hadm_id={hadm_id}")
        
        try:
            # Get the original discharge note and simplified version
            result = pipeline.process_note(note_id=note_id, hadm_id=str(hadm_id))
            
            if 'error' in result and result['error']:
                print(f"  Error processing note: {result['error']}")
                results.append({
                    'note_id': note_id,
                    'hadm_id': hadm_id,
                    'original_flesch_reading_ease': None,
                    'original_gunning_fog': None,
                    'simplified_flesch_reading_ease': None,
                    'simplified_gunning_fog': None,
                    'has_placeholders': False,
                    'placeholder_count': 0,
                    'error': result['error']
                })
                continue
            
            # Extract original and simplified text
            # Build original_note from input_sections if original_note not available
            if 'original_note' in result and result['original_note']:
                original_text = result['original_note']
            elif 'input_sections' in result and result['input_sections']:
                # Concatenate all sections to form the original note
                sections = result['input_sections']
                original_text = '\n\n'.join([
                    f"[{section_name}]\n{section_content}"
                    for section_name, section_content in sections.items()
                    if section_content and str(section_content).strip()
                ])
            else:
                original_text = ''
            
            simplified_text = result.get('simplified_output', '')
            
            # Check for placeholders in simplified output
            placeholder_info = check_for_placeholders(simplified_text)
            if placeholder_info['has_placeholders']:
                print(f"  ⚠️  Warning: Found {placeholder_info['placeholder_count']} unfilled placeholders: {placeholder_info['placeholders'][:5]}")
            
            # Calculate readability scores for original note
            print("  Calculating scores for original note...")
            original_scores = calculate_readability_scores(original_text)
            
            # Calculate readability scores for simplified note (emojis removed for fair evaluation)
            print("  Calculating scores for simplified note (emojis removed for evaluation)...")
            simplified_scores = calculate_readability_scores(simplified_text)
            
            # Store results
            results.append({
                'note_id': note_id,
                'hadm_id': hadm_id,
                'original_flesch_reading_ease': original_scores['flesch_reading_ease'],
                'original_gunning_fog': original_scores['gunning_fog'],
                'simplified_flesch_reading_ease': simplified_scores['flesch_reading_ease'],
                'simplified_gunning_fog': simplified_scores['gunning_fog'],
                'has_placeholders': placeholder_info['has_placeholders'],
                'placeholder_count': placeholder_info['placeholder_count'],
                'error': None
            })
            
            print(f"  Original - Flesch: {original_scores['flesch_reading_ease']:.2f}, "
                  f"Gunning Fog: {original_scores['gunning_fog']:.2f}")
            print(f"  Simplified - Flesch: {simplified_scores['flesch_reading_ease']:.2f}, "
                  f"Gunning Fog: {simplified_scores['gunning_fog']:.2f}")
            
            # Save incrementally after each successful patient
            results_df = pd.DataFrame(results)
            results_df.to_csv(args.output, index=False)
            print(f"  💾 Progress saved to {args.output}")
            
        except Exception as e:
            print(f"  Unexpected error: {e}")
            results.append({
                'note_id': note_id,
                'hadm_id': hadm_id,
                'original_flesch_reading_ease': None,
                'original_gunning_fog': None,
                'simplified_flesch_reading_ease': None,
                'simplified_gunning_fog': None,
                'has_placeholders': False,
                'placeholder_count': 0,
                'error': str(e)
            })
            # Save even on error to preserve progress
            results_df = pd.DataFrame(results)
            results_df.to_csv(args.output, index=False)
            print(f"  💾 Progress saved (with error) to {args.output}")
    
    # Step 6: Final save (redundant but ensures everything is saved)
    print("\nStep 6: Final save to CSV...")
    results_df = pd.DataFrame(results)
    results_df.to_csv(args.output, index=False)
    print(f"Results saved to: {args.output}")
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    successful = results_df[results_df['error'].isna()]
    if len(successful) > 0:
        print(f"\nSuccessfully processed: {len(successful)}/{len(results)} patients")
        
        # Check for placeholders
        if 'has_placeholders' in successful.columns:
            placeholder_count = successful['has_placeholders'].sum()
            if placeholder_count > 0:
                print(f"\n⚠️  Placeholder Warning: {placeholder_count}/{len(successful)} notes contain unfilled placeholders")
                avg_placeholders = successful[successful['has_placeholders']]['placeholder_count'].mean()
                print(f"   Average placeholders per note: {avg_placeholders:.1f}")
        
        print("\nOriginal Notes:")
        print(f"  Mean Flesch Reading Ease: {successful['original_flesch_reading_ease'].mean():.2f}")
        print(f"  Mean Gunning Fog: {successful['original_gunning_fog'].mean():.2f}")
        print("\nSimplified Notes (emojis removed for evaluation):")
        print(f"  Mean Flesch Reading Ease: {successful['simplified_flesch_reading_ease'].mean():.2f}")
        print(f"  Mean Gunning Fog: {successful['simplified_gunning_fog'].mean():.2f}")
        
        # Calculate improvements
        flesch_improvement = (successful['simplified_flesch_reading_ease'].mean() - 
                             successful['original_flesch_reading_ease'].mean())
        fog_improvement = (successful['original_gunning_fog'].mean() - 
                          successful['simplified_gunning_fog'].mean())
        
        print(f"\nImprovements:")
        print(f"  Flesch Reading Ease: {flesch_improvement:+.2f} "
              f"({'easier to read' if flesch_improvement > 0 else 'harder to read'})")
        print(f"  Gunning Fog: {fog_improvement:+.2f} "
              f"({'simpler' if fog_improvement > 0 else 'more complex'})")
    else:
        print(f"\nNo patients were successfully processed.")
        print(f"Failed: {len(results_df[results_df['error'].notna()])}/{len(results)}")
    
    print("\n" + "=" * 80)
    print("Evaluation complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
