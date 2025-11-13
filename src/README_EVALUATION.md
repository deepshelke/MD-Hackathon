# Readability Evaluation Script

This script evaluates the readability of medical discharge notes before and after simplification using the MD-Hackathon model.

## What It Does

1. **Generates reproducible patient selection**: Creates a consistent list of 20 patient indices (1-250) using a fixed random seed
2. **Loads patient data**: Reads `note_id` and `hadm_id` from `patients_list.csv`
3. **Calculates original readability scores**: Uses textstat to compute:
   - Flesch Reading Ease score
   - Gunning Fog Index
4. **Processes notes through model**: Runs each discharge note through the MedLlama-3 simplification pipeline
5. **Calculates simplified readability scores**: Computes the same metrics for model outputs
6. **Outputs CSV file**: Saves all scores and comparisons

## Prerequisites

### 1. Environment Setup

Make sure you have the MD-Hackathon repository cloned and set up:

```bash
git clone https://github.com/deepshelke/MD-Hackathon.git
cd MD-Hackathon
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
pip install textstat --break-system-packages
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory with:

```env
FIREBASE_CREDENTIALS_PATH=./credentials/firebase-service-account.json
HF_TOKEN=your_huggingface_token_here
```

### 4. Ensure patients_list.csv Exists

Make sure `src/patients_list.csv` exists and contains at least these columns:
- `note_id`: The unique identifier for each discharge note
- `hadm_id`: The hospital admission ID

## Usage

### Basic Usage

```bash
python evaluate_readability.py
```

### Expected Output Structure

The script will create a CSV file named `readability_evaluation_results.csv` with the following columns:

| Column | Description |
|--------|-------------|
| `note_id` | Unique note identifier |
| `hadm_id` | Hospital admission ID |
| `original_flesch_reading_ease` | Flesch score for original note (0-100, higher = easier) |
| `original_gunning_fog` | Gunning Fog index for original note (grade level) |
| `simplified_flesch_reading_ease` | Flesch score for simplified note |
| `simplified_gunning_fog` | Gunning Fog index for simplified note |
| `error` | Any errors encountered (null if successful) |

## Understanding Readability Scores

### Flesch Reading Ease Score (0-100)
- **90-100**: Very easy (5th grade)
- **80-90**: Easy (6th grade)
- **70-80**: Fairly easy (7th grade)
- **60-70**: Standard (8th-9th grade)
- **50-60**: Fairly difficult (10th-12th grade)
- **30-50**: Difficult (college)
- **0-30**: Very difficult (college graduate)

**Higher scores = easier to read**

### Gunning Fog Index
- Represents the years of formal education needed to understand the text
- **Score of 8**: Readable by 8th graders
- **Score of 12**: Readable by high school seniors
- **Score of 16**: Readable by college graduates
- **Score of 20+**: Very complex, post-graduate level

**Lower scores = easier to read**

## Sample Output

```
Processing patient 1/20: note_id=10000032-DS-21, hadm_id=22595853
  Calculating scores for original note...
  Calculating scores for simplified note...
  Original - Flesch: 45.23, Gunning Fog: 14.56
  Simplified - Flesch: 72.18, Gunning Fog: 8.34

SUMMARY STATISTICS
==================
Successfully processed: 20/20 patients

Original Notes:
  Mean Flesch Reading Ease: 43.56
  Mean Gunning Fog: 15.23

Simplified Notes:
  Mean Flesch Reading Ease: 71.42
  Mean Gunning Fog: 8.67

Improvements:
  Flesch Reading Ease: +27.86 (easier to read)
  Gunning Fog: -6.56 (simpler)
```

## Reproducibility

The script uses a fixed random seed (42) to ensure the same 20 patients are selected every time you run it. This makes results reproducible across different runs.

To change the seed or number of patients, modify these parameters in the `generate_reproducible_indices()` function call:

```python
indices = generate_reproducible_indices(n=20, max_val=250, seed=42)
```

## Troubleshooting

### Error: "Could not find src/patients_list.csv"
- Ensure the file exists in the `src/` directory
- Check that you're running the script from the MD-Hackathon root directory

### Error: "Error initializing pipeline"
- Verify your `.env` file has valid credentials
- Check that `FIREBASE_CREDENTIALS_PATH` points to a valid JSON file
- Ensure your `HF_TOKEN` is valid and has access to the MedLlama-3 model

### Error: "API request failed"
- Check your internet connection
- Verify Hugging Face API is accessible
- Check if you've hit API rate limits

### Low success rate
- Verify that the note_ids and hadm_ids in patients_list.csv are valid
- Check Firebase database connectivity
- Ensure notes exist in Firestore for the selected patients

## Customization

### Change the Number of Patients

```python
indices = generate_reproducible_indices(n=50, max_val=250, seed=42)
```

### Use Different Random Seed

```python
indices = generate_reproducible_indices(n=20, max_val=250, seed=123)
```

### Modify Output Path

```python
output_path = 'custom_results.csv'
results_df.to_csv(output_path, index=False)
```

## Alternative: Standalone Version

If you don't have access to Firebase/Firestore or want to test with local data, see the `evaluate_readability_standalone.py` script which works with local CSV files containing the actual note text.

## Notes

- Processing 20 patients may take 10-30 minutes depending on API response times
- The script prints progress for each patient
- Failed patients are logged with error messages
- All results (successful and failed) are saved to the output CSV
