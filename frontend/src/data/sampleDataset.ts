// Consolidated single benchmark dataset for the AI Data Analyst platform:
// 146 SaaS customer subscription records with tenure, charges, contracts, support tickets,
// intentional missing values, outliers, and duplicates.
// Calibrated for comprehensive data health profiling, cleaning, statistical analysis,
// and ML Studio modeling (binary classification on 'churn', regression on 'lifetime_value').

export const SAMPLE_DATASET_NAME = 'saas_customer_churn_benchmark.csv';

export const SAMPLE_DATASET_DESCRIPTION = 
  '146 SaaS customer subscription records with tenure, contracts, support tickets, intentional missing values, outliers, and duplicates, specifically calibrated for Data Health Profiling, Cleaning, Visualizations, and ML Studio.';

export const SAMPLE_DATASET_CSV = `customer_id,tenure_months,monthly_charges,total_charges,contract_type,internet_service,tech_support,support_tickets,lifetime_value,churn
CUST-1001,29,37.56,1089.24,One year,Fiber optic,Yes,0,1307.09,0
CUST-1002,61,27.68,1688.48,Two year,Fiber optic,Yes,1,2026.18,0
CUST-1003,24,88.12,2114.88,One year,No,No,2,2537.86,0
CUST-1004,22,55.62,1223.64,One year,Fiber optic,Yes,2,1468.37,0
CUST-1005,17,57.31,974.27,One year,Fiber optic,No,1,1169.12,0
CUST-1006,53,112.58,5966.74,Two year,No,No,1,7160.09,1
CUST-1007,20,57.55,1151.00,Month-to-month,No,Yes,3,920.80,1
CUST-1008,10,101.98,1019.80,Month-to-month,Fiber optic,Yes,5,815.84,1
CUST-1009,6,43.86,263.16,Month-to-month,DSL,No,1,210.53,0
CUST-1010,22,47.03,1034.66,One year,Fiber optic,No,1,1241.59,0
CUST-1011,68,86.62,5890.16,Two year,No,Yes,1,7068.19,0
CUST-1012,13,,845.00,Month-to-month,DSL,No,0,676.00,1
CUST-1013,15,37.57,563.55,Month-to-month,No,No,0,450.84,0
CUST-1014,13,114.76,1491.88,Month-to-month,No,Yes,1,1193.50,1
CUST-1015,4,39.40,157.60,Month-to-month,Fiber optic,No,0,126.08,0
CUST-1016,15,112.40,1686.00,Month-to-month,No,Yes,1,1348.80,0
CUST-1017,9,55.62,500.58,Month-to-month,No,No,2,400.46,1
CUST-1018,24,70.05,1681.20,Month-to-month,No,Yes,0,1344.96,1
CUST-1019,10,70.69,706.90,Month-to-month,No,,3,565.52,1
CUST-1020,45,78.91,3550.95,One year,No,No,4,4261.14,1
CUST-1021,39,104.02,4056.78,Two year,DSL,Yes,0,4868.14,0
CUST-1022,18,36.56,658.08,Month-to-month,Fiber optic,No,2,526.46,0
CUST-1023,20,44.06,881.20,Month-to-month,No,Yes,1,704.96,0
CUST-1024,21,105.97,2225.37,Month-to-month,No,No,1,1780.30,1
CUST-1025,1,45.71,45.71,Month-to-month,DSL,Yes,1,36.57,1
CUST-1026,26,27.83,723.58,One year,Fiber optic,No,0,868.30,1
CUST-1027,16,36.91,590.56,Month-to-month,No,No,0,472.45,1
CUST-1028,7,,455.00,Month-to-month,DSL,No,0,364.00,1
CUST-1029,2,113.57,227.14,Month-to-month,No,Yes,2,181.71,1
CUST-1030,27,73.27,1978.29,One year,Fiber optic,Yes,0,2373.95,0
CUST-1031,3,102.52,307.56,Month-to-month,Fiber optic,Yes,1,246.05,1
CUST-1032,29,101.38,2940.02,Two year,Fiber optic,Yes,4,3528.02,0
CUST-1033,2,25.19,50.38,Month-to-month,DSL,No,0,40.30,1
CUST-1034,30,111.16,3334.80,One year,DSL,No,1,4001.76,1
CUST-1035,19,30.49,579.31,Month-to-month,Fiber optic,No,48,463.45,1
CUST-1036,45,111.47,5016.15,One year,No,Yes,0,6019.38,0
CUST-1037,22,61.34,1349.48,Month-to-month,Fiber optic,Yes,3,1079.58,1
CUST-1038,14,75.87,1062.18,Month-to-month,Fiber optic,No,2,849.74,0
CUST-1039,11,60.62,666.82,Month-to-month,No,No,0,533.46,1
CUST-1040,24,114.86,2756.64,Two year,Fiber optic,Yes,1,3307.97,1
CUST-1041,5,104.28,521.40,Month-to-month,DSL,Yes,4,417.12,1
CUST-1042,23,113.55,2611.65,Month-to-month,No,Yes,1,2089.32,0
CUST-1043,18,37.09,667.62,One year,No,Yes,4,801.14,0
CUST-1044,29,43.96,1274.84,One year,Fiber optic,No,0,1529.81,0
CUST-1045,44,,2860.00,One year,DSL,Yes,1,3432.00,1
CUST-1046,2,94.40,188.80,Month-to-month,DSL,No,0,151.04,1
CUST-1047,14,35.07,490.98,Month-to-month,No,Yes,1,392.78,1
CUST-1048,59,36.47,2151.73,Two year,No,No,0,2582.08,0
CUST-1049,46,47.46,2183.16,Two year,Fiber optic,Yes,0,2619.79,0
CUST-1050,21,46.31,972.51,One year,DSL,Yes,4,1167.01,0
CUST-1051,25,108.20,2705.00,Two year,DSL,No,0,3246.00,0
CUST-1052,41,88.12,3612.92,Two year,Fiber optic,No,0,4335.50,0
CUST-1053,36,66.43,2391.48,Two year,Fiber optic,No,3,2869.78,0
CUST-1054,25,60.86,1521.50,Two year,Fiber optic,No,2,1825.80,0
CUST-1055,46,60.97,2804.62,Two year,DSL,No,2,3365.54,0
CUST-1056,6,113.52,681.12,Month-to-month,DSL,Yes,1,544.90,1
CUST-1057,11,113.58,1249.38,Month-to-month,No,Yes,1,999.50,1
CUST-1058,14,25.15,352.10,One year,DSL,Yes,2,422.52,0
CUST-1059,11,84.70,931.70,Month-to-month,No,Yes,2,745.36,0
CUST-1060,22,61.22,1346.84,Month-to-month,DSL,No,1,1077.47,0
CUST-1061,13,106.25,1381.25,Month-to-month,No,No,2,1105.00,1
CUST-1062,42,95.72,4020.24,Two year,DSL,,0,4824.29,0
CUST-1063,17,106.11,1803.87,Month-to-month,Fiber optic,Yes,1,1443.10,0
CUST-1064,21,33.40,701.40,Month-to-month,No,Yes,2,561.12,0
CUST-1065,5,47.04,235.20,Month-to-month,Fiber optic,No,0,188.16,0
CUST-1066,38,76.81,2918.78,One year,DSL,No,3,3502.54,0
CUST-1067,23,92.59,2129.57,Month-to-month,No,Yes,0,1703.66,0
CUST-1068,17,75.17,1277.89,Month-to-month,No,Yes,1,1022.31,1
CUST-1069,57,78.59,4479.63,Two year,No,No,5,5375.56,0
CUST-1070,39,74.31,2898.09,One year,No,Yes,3,3477.71,0
CUST-1071,8,49.96,399.68,Month-to-month,DSL,No,3,319.74,1
CUST-1072,23,49.45,1137.35,Month-to-month,Fiber optic,No,0,909.88,0
CUST-1073,8,38.75,310.00,Month-to-month,Fiber optic,Yes,1,248.00,1
CUST-1074,15,43.62,654.30,Month-to-month,No,No,1,523.44,1
CUST-1075,13,93.90,1220.70,One year,No,No,3,1464.84,0
CUST-1076,72,105.25,7578.00,Two year,DSL,No,1,9093.60,0
CUST-1077,26,49.56,1288.56,One year,No,No,1,1546.27,1
CUST-1078,13,100.65,1308.45,Month-to-month,No,Yes,2,1046.76,0
CUST-1079,19,27.44,521.36,Month-to-month,DSL,No,1,417.09,1
CUST-1080,9,,585.00,Month-to-month,Fiber optic,No,1,468.00,1
CUST-1081,72,62.94,4531.68,Two year,DSL,Yes,4,5438.02,0
CUST-1082,34,31.18,1060.12,One year,Fiber optic,Yes,0,1272.14,0
CUST-1083,25,46.47,1161.75,Two year,Fiber optic,No,2,1394.10,0
CUST-1084,41,94.02,3854.82,One year,Fiber optic,Yes,2,4625.78,0
CUST-1085,31,39.74,1231.94,Two year,No,No,2,1478.33,0
CUST-1086,19,111.24,2113.56,Month-to-month,DSL,No,2,1690.85,0
CUST-1087,23,46.86,1077.78,Month-to-month,No,No,3,862.22,0
CUST-1088,48,56.25,2700.00,One year,Fiber optic,No,72,3240.00,0
CUST-1089,11,62.81,690.91,Month-to-month,No,No,0,552.73,1
CUST-1090,53,64.19,3402.07,Two year,No,No,2,4082.48,0
CUST-1091,53,90.79,4811.87,Two year,DSL,No,1,5774.24,0
CUST-1092,9,46.95,422.55,Month-to-month,Fiber optic,No,3,338.04,1
CUST-1093,13,54.25,705.25,One year,DSL,No,1,846.30,0
CUST-1094,29,88.11,2555.19,One year,DSL,,3,3066.23,0
CUST-1095,3,61.58,184.74,Month-to-month,Fiber optic,Yes,0,147.79,0
CUST-1096,40,33.37,1334.80,One year,DSL,Yes,2,1601.76,0
CUST-1097,19,74.81,1421.39,Month-to-month,No,No,1,1137.11,1
CUST-1098,34,49.38,1678.92,One year,DSL,No,2,2014.70,0
CUST-1099,19,110.58,2101.02,One year,DSL,Yes,2,2521.22,1
CUST-1100,45,113.25,5096.25,One year,DSL,Yes,1,6115.50,0
CUST-1101,1,36.39,36.39,Month-to-month,DSL,Yes,2,29.11,0
CUST-1102,20,92.75,1855.00,One year,No,Yes,2,2226.00,0
CUST-1103,42,41.59,1746.78,One year,DSL,Yes,1,2096.14,0
CUST-1104,28,31.67,886.76,Two year,Fiber optic,Yes,1,1064.11,0
CUST-1105,29,,1885.00,Two year,DSL,No,5,2262.00,0
CUST-1106,45,106.77,4804.65,One year,Fiber optic,No,1,5765.58,0
CUST-1107,60,79.87,4792.20,Two year,DSL,Yes,2,5750.64,0
CUST-1108,9,39.14,352.26,Month-to-month,Fiber optic,Yes,2,281.81,0
CUST-1109,15,67.29,1009.35,Month-to-month,DSL,Yes,2,807.48,1
CUST-1110,41,46.01,1886.41,One year,No,No,0,2263.69,0
CUST-1111,24,74.01,1776.24,One year,No,Yes,1,2131.49,0
CUST-1112,27,52.69,1422.63,Two year,Fiber optic,No,0,1707.16,0
CUST-1113,23,49.50,1138.50,Month-to-month,DSL,No,1,910.80,1
CUST-1114,32,27.33,874.56,One year,DSL,Yes,2,1049.47,0
CUST-1115,61,114.96,7012.56,Two year,No,No,4,8415.07,0
CUST-1116,42,64.80,2721.60,One year,Fiber optic,No,1,3265.92,1
CUST-1117,43,67.30,2893.90,One year,No,No,4,3472.68,1
CUST-1118,33,69.59,2296.47,One year,Fiber optic,No,1,2755.76,0
CUST-1119,17,54.09,919.53,One year,DSL,No,1,1103.44,0
CUST-1120,66,66.58,4394.28,Two year,Fiber optic,Yes,3,5273.14,1
CUST-1121,21,29.65,622.65,Month-to-month,DSL,No,1,498.12,1
CUST-1122,68,27.60,1876.80,Two year,DSL,Yes,1,2252.16,0
CUST-1123,18,45.22,813.96,Month-to-month,Fiber optic,Yes,1,651.17,1
CUST-1124,16,51.27,820.32,Month-to-month,Fiber optic,No,4,656.26,1
CUST-1125,8,38.02,304.16,Month-to-month,DSL,Yes,1,243.33,0
CUST-1126,3,96.10,288.30,Month-to-month,Fiber optic,No,0,230.64,1
CUST-1127,12,51.87,622.44,One year,DSL,No,0,746.93,0
CUST-1128,12,93.66,1123.92,Month-to-month,DSL,No,1,899.14,1
CUST-1129,23,59.47,1367.81,Month-to-month,Fiber optic,No,0,1094.25,1
CUST-1130,36,84.73,3050.28,One year,No,Yes,1,3660.34,0
CUST-1131,19,34.03,646.57,Month-to-month,No,No,1,517.26,1
CUST-1132,70,103.38,7236.60,Two year,Fiber optic,Yes,0,8683.92,1
CUST-1133,33,60.77,2005.41,One year,DSL,Yes,2,2406.49,0
CUST-1134,48,81.41,3907.68,Two year,No,No,4,4689.22,0
CUST-1135,8,107.88,863.04,Month-to-month,Fiber optic,Yes,2,690.43,0
CUST-1136,21,34.05,715.05,Month-to-month,Fiber optic,Yes,2,572.04,0
CUST-1137,44,51.40,2261.60,Two year,Fiber optic,No,2,2713.92,0
CUST-1138,19,41.21,782.99,Month-to-month,DSL,Yes,2,626.39,1
CUST-1139,67,107.15,7179.05,Two year,No,Yes,0,8614.86,0
CUST-1140,28,105.90,2965.20,One year,DSL,No,2,3558.24,0
CUST-1011,68,86.62,5890.16,Two year,No,Yes,1,7068.19,0
CUST-1011,68,86.62,5890.16,Two year,No,Yes,1,7068.19,0
CUST-1026,26,27.83,723.58,One year,Fiber optic,No,0,868.30,1
CUST-1043,18,37.09,667.62,One year,No,Yes,4,801.14,0
CUST-1071,8,49.96,399.68,Month-to-month,DSL,No,3,319.74,1
CUST-1096,40,33.37,1334.80,One year,DSL,Yes,2,1601.76,0`;

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
// Single authoritative SaaS Customer Churn & LTV benchmark dataset (146 records).
// Designed for end-to-end platform workflows:
//   - Data Health Profiling (identifies nulls, duplicates, outliers)
//   - Transformation Engine (deduplication, imputation, clipping)
//   - Visualizations & Statistical Summaries
//   - ML Studio (predicting binary 'churn' and continuous 'lifetime_value')
// ==============================================================================
