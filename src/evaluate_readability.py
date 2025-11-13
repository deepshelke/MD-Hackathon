"""
Readability Evaluation Script for MD-Hackathon Project
This script:
1. Generates a reproducible list of 20 patient indices (1-250)
2. Reads note_id and hadm_id from patients_list.csv
3. Calculates readability scores (Flesch Reading Ease & Gunning Fog) for original discharge notes
4. Runs notes through the simplification model
5. Calculates readability scores for model outputs
6. Outputs results to a CSV file
"""

import os
import sys
import random
import pandas as pd
import textstat
from pathlib import Path

# Add src directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent / 'src'))

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
        flesch_score = textstat.flesch_reading_ease(text)
        gunning_fog_score = textstat.gunning_fog(text)
        
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


def load_patients_list(csv_path='src/patients_list.csv'):
    """
    Load the patients list CSV file.
    
    Args:
        csv_path (str): Path to patients_list.csv
    
    Returns:
        pd.DataFrame: DataFrame containing patient information
    """
    try:
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} patients from {csv_path}")
        return df
    except FileNotFoundError:
        print(f"Error: Could not find {csv_path}")
        print("Please ensure patients_list.csv is in the src/ directory")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading patients list: {e}")
        sys.exit(1)


def main():
    """
    Main function to execute the readability evaluation pipeline.
    """
    print("=" * 80)
    print("Medical Note Readability Evaluation")
    print("=" * 80)
    
    # Step 1: Generate reproducible list of 20 indices
    print("\nStep 1: Generating reproducible list of 20 patient indices...")
    indices = generate_reproducible_indices(n=20, max_val=250, seed=42)
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
    results = []
    
    for idx, row in selected_patients.iterrows():
        note_id = row['note_id']
        hadm_id = row['hadm_id']
        
        print(f"\nProcessing patient {idx + 1}/{len(selected_patients)}: "
              f"note_id={note_id}, hadm_id={hadm_id}")
        
        try:
            # Get the original discharge note and simplified version
            result = pipeline.process_note(note_id=note_id, hadm_id=str(hadm_id))
            
            if 'error' in result:
                print(f"  Error processing note: {result['error']}")
                results.append({
                    'note_id': note_id,
                    'hadm_id': hadm_id,
                    'original_flesch_reading_ease': None,
                    'original_gunning_fog': None,
                    'simplified_flesch_reading_ease': None,
                    'simplified_gunning_fog': None,
                    'error': result['error']
                })
                continue
            
            # Extract original and simplified text
            original_text = result.get('original_note', '')
            simplified_text = result.get('simplified_output', '')
            
            # Calculate readability scores for original note
            print("  Calculating scores for original note...")
            original_scores = calculate_readability_scores(original_text)
            
            # Calculate readability scores for simplified note
            print("  Calculating scores for simplified note...")
            simplified_scores = calculate_readability_scores(simplified_text)
            
            # Store results
            results.append({
                'note_id': note_id,
                'hadm_id': hadm_id,
                'original_flesch_reading_ease': original_scores['flesch_reading_ease'],
                'original_gunning_fog': original_scores['gunning_fog'],
                'simplified_flesch_reading_ease': simplified_scores['flesch_reading_ease'],
                'simplified_gunning_fog': simplified_scores['gunning_fog'],
                'error': None
            })
            
            print(f"  Original - Flesch: {original_scores['flesch_reading_ease']:.2f}, "
                  f"Gunning Fog: {original_scores['gunning_fog']:.2f}")
            print(f"  Simplified - Flesch: {simplified_scores['flesch_reading_ease']:.2f}, "
                  f"Gunning Fog: {simplified_scores['gunning_fog']:.2f}")
            
        except Exception as e:
            print(f"  Unexpected error: {e}")
            results.append({
                'note_id': note_id,
                'hadm_id': hadm_id,
                'original_flesch_reading_ease': None,
                'original_gunning_fog': None,
                'simplified_flesch_reading_ease': None,
                'simplified_gunning_fog': None,
                'error': str(e)
            })
    
    # Step 6: Output results to CSV
    print("\nStep 6: Saving results to CSV...")
    results_df = pd.DataFrame(results)
    output_path = 'readability_evaluation_results.csv'
    results_df.to_csv(output_path, index=False)
    print(f"Results saved to: {output_path}")
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    successful = results_df[results_df['error'].isna()]
    if len(successful) > 0:
        print(f"\nSuccessfully processed: {len(successful)}/{len(results)} patients")
        print("\nOriginal Notes:")
        print(f"  Mean Flesch Reading Ease: {successful['original_flesch_reading_ease'].mean():.2f}")
        print(f"  Mean Gunning Fog: {successful['original_gunning_fog'].mean():.2f}")
        print("\nSimplified Notes:")
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
