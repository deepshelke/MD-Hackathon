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
    
    # Step 1: Generate a larger pool of indices for retry capability
    # Generate 3x the requested number to have backup patients if some fail
    pool_size = max(args.n * 3, 60)  # At least 60 patients in pool
    print(f"\nStep 1: Generating patient pool of {pool_size} indices for retry capability...")
    all_indices = generate_reproducible_indices(n=pool_size, max_val=args.max_val, seed=args.seed)
    print(f"Generated pool of {len(all_indices)} patient indices")
    
    # Step 2: Load patients list
    print("\nStep 2: Loading patients list...")
    patients_df = load_patients_list()
    
    # Verify we have enough patients
    if len(patients_df) < max(all_indices):
        print(f"Warning: patients_list.csv only has {len(patients_df)} rows, "
              f"but we need at least {max(all_indices)} rows")
        # Adjust indices to fit available data
        all_indices = [i for i in all_indices if i <= len(patients_df)]
        print(f"Adjusted indices to: {len(all_indices)} indices")
    
    # Create a pool of all available patients
    all_patients_pool = patients_df.iloc[[i-1 for i in all_indices]].copy()
    print(f"Created pool of {len(all_patients_pool)} patients for selection")
    
    # Filter out already processed patients if resuming
    if args.resume and processed_set:
        initial_count = len(all_patients_pool)
        all_patients_pool = all_patients_pool[
            ~all_patients_pool.apply(lambda row: (row['note_id'], row['hadm_id']) in processed_set, axis=1)
        ]
        skipped = initial_count - len(all_patients_pool)
        if skipped > 0:
            print(f"Skipping {skipped} already processed patients from pool")
            print(f"Remaining in pool: {len(all_patients_pool)} patients")
    
    if len(all_patients_pool) == 0:
        print("\n✅ All patients in pool have already been processed!")
        if existing_df is not None:
            print(f"Results available in: {args.output}")
        return
    
    # Calculate how many we need
    target_count = args.n
    # Count successful patients from existing results
    if existing_df is not None:
        # Filter out rows with errors
        successful_df = existing_df[existing_df['error'].isna() | (existing_df['error'] == '')]
        successful_count = len(successful_df)
    else:
        successful_count = 0
    needed_count = target_count - successful_count
    
    if needed_count <= 0:
        print(f"\n✅ Already have {successful_count} successful patients (target: {target_count})!")
        return
    
    print(f"\nTarget: {target_count} successful patients")
    print(f"Already have: {successful_count} successful patients")
    print(f"Need to process: {needed_count} more patients")
    print(f"Available in pool: {len(all_patients_pool)} patients")
    
    # Confirmation prompt
    if not args.yes:
        print(f"\n⚠️  WARNING: This will make up to {needed_count * 2} API calls to Hugging Face!")
        print(f"   (Processing {needed_count} patients with retry capability)")
        print(f"   Estimated cost: ~{needed_count * 2} API calls (some may fail and retry)")
        response = input(f"\nProceed with processing up to {needed_count} patients? (yes/no): ")
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
    
    # Step 4 & 5: Process patients with retry logic until we have enough successful results
    print("\nStep 4-5: Processing patients with retry capability...")
    results = list(existing_df.to_dict('records')) if existing_df is not None else []
    
    # Track which patients we've tried (to avoid duplicates)
    tried_patients = set()
    if existing_df is not None:
        tried_patients = set(zip(existing_df['note_id'], existing_df['hadm_id']))
    
    # Track successful vs failed
    # Count successful: rows where error is None, empty, or NaN
    def is_successful(result_row):
        error_val = result_row.get('error')
        if error_val is None:
            return True
        if isinstance(error_val, str):
            return len(error_val.strip()) == 0
        try:
            return pd.isna(error_val)
        except:
            return False
    
    successful_processed = len([r for r in results if is_successful(r)])
    failed_count = 0
    patient_num = 0
    
    # Process patients from pool until we have enough successful ones
    for idx, row in all_patients_pool.iterrows():
        # Check if we have enough successful patients
        if successful_processed >= target_count:
            print(f"\n✅ Reached target of {target_count} successful patients!")
            break
        
        note_id = row['note_id']
        hadm_id = row['hadm_id']
        patient_key = (note_id, hadm_id)
        
        # Skip if already tried
        if patient_key in tried_patients:
            continue
        
        patient_num += 1
        tried_patients.add(patient_key)
        
        print(f"\nProcessing patient {patient_num} (Successful so far: {successful_processed}/{target_count}): "
              f"note_id={note_id}, hadm_id={hadm_id}")
        
        try:
            # Get the original discharge note and simplified version
            result = pipeline.process_note(note_id=note_id, hadm_id=str(hadm_id))
            
            if 'error' in result and result['error']:
                error_msg = result['error']
                print(f"  ❌ Error processing note: {error_msg}")
                failed_count += 1
                results.append({
                    'note_id': note_id,
                    'hadm_id': hadm_id,
                    'original_flesch_reading_ease': None,
                    'original_gunning_fog': None,
                    'simplified_flesch_reading_ease': None,
                    'simplified_gunning_fog': None,
                    'has_placeholders': False,
                    'placeholder_count': 0,
                    'error': error_msg
                })
                # Save progress and continue to next patient
                results_df = pd.DataFrame(results)
                results_df.to_csv(args.output, index=False)
                print(f"  💾 Progress saved. Will try next patient from pool...")
                continue
            
            # Check if model refused (common refusal patterns)
            simplified_text = result.get('simplified_output', '')
            if simplified_text:
                refusal_patterns = [
                    "i'm sorry",
                    "i cannot",
                    "i can't",
                    "cannot simplify",
                    "too complex",
                    "beyond my capabilities",
                    "exceeds the character limit",
                    "would be best to consult"
                ]
                is_refusal = any(pattern in simplified_text.lower()[:200] for pattern in refusal_patterns)
                
                if is_refusal:
                    print(f"  ⚠️  Model refused to process this note. Will try next patient from pool...")
                    failed_count += 1
                    results.append({
                        'note_id': note_id,
                        'hadm_id': hadm_id,
                        'original_flesch_reading_ease': None,
                        'original_gunning_fog': None,
                        'simplified_flesch_reading_ease': None,
                        'simplified_gunning_fog': None,
                        'has_placeholders': False,
                        'placeholder_count': 0,
                        'error': 'Model refused to process note'
                    })
                    # Save progress and continue to next patient
                    results_df = pd.DataFrame(results)
                    results_df.to_csv(args.output, index=False)
                    print(f"  💾 Progress saved. Will try next patient from pool...")
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
            
            # Mark as successful
            successful_processed += 1
            
            # Save incrementally after each successful patient
            results_df = pd.DataFrame(results)
            results_df.to_csv(args.output, index=False)
            print(f"  ✅ Success! ({successful_processed}/{target_count} successful patients)")
            print(f"  💾 Progress saved to {args.output}")
            
            # Check if we've reached our target
            if successful_processed >= target_count:
                print(f"\n🎉 Reached target of {target_count} successful patients!")
                break
            
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            failed_count += 1
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
            print(f"  💾 Progress saved. Will try next patient from pool...")
            continue
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"Processing Complete:")
    print(f"  Successful: {successful_processed}/{target_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total attempted: {patient_num}")
    print(f"{'='*80}")
    
    if successful_processed < target_count:
        print(f"\n⚠️  Warning: Only {successful_processed} successful patients out of {target_count} target.")
        print(f"   You may want to run again with a larger pool or different seed.")
    
    # Step 6: Final save (redundant but ensures everything is saved)
    print("\nStep 6: Final save to CSV...")
    results_df = pd.DataFrame(results)
    results_df.to_csv(args.output, index=False)
    print(f"Results saved to: {args.output}")
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    # Filter successful patients (no error or empty error)
    successful = results_df[(results_df['error'].isna()) | (results_df['error'] == '')]
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
