import titanicRaw from './titanic.csv?raw';

export const SAMPLE_DATASET_NAME = 'titanic.csv';

export const SAMPLE_DATASET_DESCRIPTION = 
  'Titanic Passenger Survival dataset (891 passenger records with demographics, passenger class, ticket fare, cabin, embarkation ports, and survival outcomes). Calibrated for Data Health Profiling, Cleaning, Visualizations, and ML Studio modeling.';

export const SAMPLE_DATASET_CSV = titanicRaw;

export function getSampleDatasetFile(): File {
  const blob = new Blob([SAMPLE_DATASET_CSV], { type: 'text/csv' });
  return new File([blob], SAMPLE_DATASET_NAME, { type: 'text/csv' });
}

// Aliases for compatibility
export const getMLBenchmarkDatasetFile = getSampleDatasetFile;
export const ML_BENCHMARK_DATASET_NAME = SAMPLE_DATASET_NAME;
export const ML_BENCHMARK_DATASET_CSV = SAMPLE_DATASET_CSV;

// ==============================================================================
// FILE SUMMARY: frontend/src/data/sampleDataset.ts
// ==============================================================================
// WHAT THIS FILE CONTAINS:
// Authoritative Titanic Passenger Survival benchmark dataset (891 records).
// Designed for end-to-end platform workflows:
//   - Data Health Profiling (identifies nulls in Age and Cabin, categorical dimensions)
//   - Transformation Engine (missing value imputation, text normalization)
//   - Visualizations & Statistical Summaries (Fare distributions, survival rates by class)
//   - ML Studio (predicting binary 'Survived' and continuous 'Fare')
// ==============================================================================
