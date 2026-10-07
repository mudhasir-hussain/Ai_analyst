// Comprehensive sample dataset showcasing all platform capabilities:
// - Realistic multi-dimensional retail and tech transactions (53 records).
// - Multi-category distribution (Hardware, Software, Cloud, Consulting, Peripherals).
// - Datetime distribution across 2024 for line trends.
// - Intentional missing values in discount_pct and customer_rating for missingness imputation.
// - Intentional duplicate row (ORD-2024-015 duplicated) for deduplication.
// - Outlier transaction for outlier clipping and anomaly detection.
// - Categorical columns for bar charts, frequency metrics, and one-hot encoding.
// - Statistically significant correlation between discount_pct and profit_margin.

export const SAMPLE_DATASET_NAME = 'global_enterprise_sales_2024.csv';

export const SAMPLE_DATASET_DESCRIPTION = 
  '53 enterprise sales records across 4 global regions, featuring pricing, dates, categories, intentional missing values, outliers, and duplicates to demonstrate AI profiling, cleaning, correlations, and reports.';

export const SAMPLE_DATASET_CSV = `order_id,order_date,region,customer_segment,category,units_sold,unit_price,discount_pct,order_total,profit_margin,customer_rating,payment_method
ORD-2024-001,2024-01-10,North America,Enterprise,Cloud Services,14,450.00,0.10,5670.00,0.42,4.8,Wire Transfer
ORD-2024-002,2024-01-14,Europe,SMB,Hardware,6,1200.00,0.05,6840.00,0.22,4.2,Credit Card
ORD-2024-003,2024-01-19,Asia-Pacific,Consumer,Peripherals,25,85.00,0.00,2125.00,0.35,3.9,PayPal
ORD-2024-004,2024-01-25,North America,Enterprise,Software Licenses,40,220.00,0.15,7480.00,0.52,4.6,Corporate Net30
ORD-2024-005,2024-02-02,Latin America,SMB,Consulting,18,175.00,,3150.00,0.38,4.1,Credit Card
ORD-2024-006,2024-02-08,Europe,Enterprise,Cloud Services,32,450.00,0.20,11520.00,0.36,4.7,Wire Transfer
ORD-2024-007,2024-02-14,Asia-Pacific,Consumer,Hardware,4,1450.00,0.00,5800.00,0.19,,Credit Card
ORD-2024-008,2024-02-21,North America,SMB,Software Licenses,15,220.00,0.05,3135.00,0.54,4.5,Credit Card
ORD-2024-009,2024-02-27,Europe,Government,Consulting,50,195.00,0.10,8775.00,0.40,4.9,Wire Transfer
ORD-2024-010,2024-03-05,Latin America,Consumer,Peripherals,12,95.00,0.00,1140.00,0.33,3.7,PayPal
ORD-2024-011,2024-03-12,Asia-Pacific,Enterprise,Hardware,8,1850.00,0.12,13024.00,0.21,4.4,Corporate Net30
ORD-2024-012,2024-03-18,North America,SMB,Cloud Services,20,450.00,,9000.00,0.44,4.3,Credit Card
ORD-2024-013,2024-03-24,Europe,Consumer,Peripherals,15,65.00,0.00,975.00,0.36,4.0,PayPal
ORD-2024-014,2024-04-02,Asia-Pacific,Enterprise,Software Licenses,60,210.00,0.25,9450.00,0.39,4.6,Wire Transfer
ORD-2024-015,2024-04-09,North America,Enterprise,Consulting,24,180.00,0.05,4104.00,0.41,4.8,Corporate Net30
ORD-2024-016,2024-04-15,Europe,SMB,Hardware,10,1150.00,0.08,10580.00,0.24,,Credit Card
ORD-2024-017,2024-04-22,Latin America,Government,Software Licenses,35,220.00,0.15,6545.00,0.48,4.5,Wire Transfer
ORD-2024-018,2024-04-29,North America,Consumer,Peripherals,8,120.00,0.00,960.00,0.32,3.8,PayPal
ORD-2024-019,2024-05-06,Asia-Pacific,SMB,Cloud Services,15,450.00,0.05,6412.50,0.45,4.4,Credit Card
ORD-2024-020,2024-05-13,Europe,Enterprise,Hardware,14,1600.00,0.15,19040.00,0.20,4.7,Corporate Net30
ORD-2024-021,2024-05-19,Latin America,SMB,Peripherals,22,75.00,,1650.00,0.35,3.9,Credit Card
ORD-2024-022,2024-05-27,North America,Government,Consulting,45,190.00,0.10,7695.00,0.42,4.9,Wire Transfer
ORD-2024-023,2024-06-03,Asia-Pacific,Consumer,Software Licenses,8,220.00,0.00,1760.00,0.55,4.3,PayPal
ORD-2024-024,2024-06-10,Europe,SMB,Cloud Services,28,450.00,0.18,10332.00,0.37,4.2,Credit Card
ORD-2024-025,2024-06-17,North America,Enterprise,Hardware,200,950.00,0.30,133000.00,0.14,4.5,Corporate Net30
ORD-2024-026,2024-06-24,Latin America,Consumer,Peripherals,16,80.00,0.00,1280.00,0.34,,PayPal
ORD-2024-027,2024-07-02,Europe,Enterprise,Software Licenses,55,220.00,0.20,9680.00,0.44,4.7,Wire Transfer
ORD-2024-015,2024-04-09,North America,Enterprise,Consulting,24,180.00,0.05,4104.00,0.41,4.8,Corporate Net30
ORD-2024-029,2024-07-15,North America,SMB,Hardware,12,1300.00,0.05,14820.00,0.25,4.3,Credit Card
ORD-2024-030,2024-07-22,Latin America,Government,Cloud Services,22,450.00,0.10,8910.00,0.43,4.6,Wire Transfer
ORD-2024-031,2024-07-29,Asia-Pacific,Consumer,Peripherals,30,60.00,0.00,1800.00,0.37,4.1,PayPal
ORD-2024-032,2024-08-05,North America,Enterprise,Consulting,36,185.00,0.12,5860.80,0.39,4.8,Corporate Net30
ORD-2024-033,2024-08-12,Europe,SMB,Software Licenses,18,220.00,,3960.00,0.53,4.4,Credit Card
ORD-2024-034,2024-08-19,Asia-Pacific,Enterprise,Hardware,9,1750.00,0.10,14175.00,0.22,4.6,Wire Transfer
ORD-2024-035,2024-08-26,Latin America,Consumer,Peripherals,14,90.00,0.00,1260.00,0.33,3.6,PayPal
ORD-2024-036,2024-09-02,North America,SMB,Cloud Services,16,450.00,0.05,6840.00,0.46,4.5,Credit Card
ORD-2024-037,2024-09-09,Europe,Government,Consulting,40,195.00,0.15,6630.00,0.38,4.9,Wire Transfer
ORD-2024-038,2024-09-16,Asia-Pacific,Consumer,Hardware,5,1350.00,0.00,6750.00,0.20,,Credit Card
ORD-2024-039,2024-09-23,North America,Enterprise,Software Licenses,48,220.00,0.18,8659.20,0.45,4.7,Corporate Net30
ORD-2024-040,2024-09-30,Europe,SMB,Peripherals,20,70.00,0.00,1400.00,0.35,4.2,Credit Card
ORD-2024-041,2024-10-07,Latin America,Enterprise,Hardware,7,1900.00,0.15,11305.00,0.19,4.4,Wire Transfer
ORD-2024-042,2024-10-14,North America,Government,Cloud Services,35,450.00,0.10,14175.00,0.43,4.8,Wire Transfer
ORD-2024-043,2024-10-21,Asia-Pacific,SMB,Consulting,20,180.00,0.05,3420.00,0.41,4.3,Credit Card
ORD-2024-044,2024-10-28,Europe,Consumer,Peripherals,18,85.00,0.00,1530.00,0.34,3.9,PayPal
ORD-2024-045,2024-11-04,North America,Enterprise,Hardware,15,1500.00,0.20,18000.00,0.18,4.7,Corporate Net30
ORD-2024-046,2024-11-11,Latin America,SMB,Software Licenses,25,220.00,0.08,5060.00,0.50,4.4,Credit Card
ORD-2024-047,2024-11-18,Asia-Pacific,Government,Consulting,30,190.00,,5700.00,0.41,4.8,Wire Transfer
ORD-2024-048,2024-11-25,Europe,Enterprise,Cloud Services,45,450.00,0.22,15795.00,0.35,4.6,Wire Transfer
ORD-2024-049,2024-12-02,North America,Consumer,Peripherals,10,110.00,0.00,1100.00,0.33,4.1,PayPal
ORD-2024-050,2024-12-09,Asia-Pacific,SMB,Hardware,11,1250.00,0.06,12925.00,0.23,4.2,Credit Card
ORD-2024-051,2024-12-16,Europe,Enterprise,Software Licenses,50,220.00,0.15,9350.00,0.47,4.8,Corporate Net30
ORD-2024-052,2024-12-23,Latin America,Consumer,Peripherals,12,75.00,0.00,900.00,0.35,3.8,PayPal
ORD-2024-053,2024-12-28,North America,Government,Cloud Services,50,450.00,0.15,19125.00,0.40,4.9,Wire Transfer`;

export function getSampleDatasetFile(): File {
  const blob = new Blob([SAMPLE_DATASET_CSV], { type: 'text/csv' });
  return new File([blob], SAMPLE_DATASET_NAME, { type: 'text/csv' });
}


// ==============================================================================
// FILE SUMMARY: frontend/src/data/sampleDataset.ts
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This module provides a rich, multi-dimensional benchmark dataset designed to
// exercise and showcase every feature of the AI Data Analyst platform:
//   1. 53 carefully calibrated enterprise sales records across 4 global regions.
//   2. High correlation between discount rates and profit margins for statistical discovery.
//   3. Intentional missing values in 'discount_pct' and 'customer_rating' to trigger
//      health scorecard warnings and test missingness imputation (mean/median).
//   4. An intentional duplicate record (ORD-2024-015) to demonstrate deduplication.
//   5. Statistical outliers in 'units_sold' and 'order_total' to demonstrate clipping.
//   6. Balanced categorical data ('region', 'category', 'payment_method') for bar charts
//      and one-hot/label encoding.
//   7. Chronological datetime distribution across all of 2024 for line charts.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Imported by 'frontend/src/App.tsx' and 'frontend/src/components/UploadModal.tsx'
//   to provide zero-setup, 1-click demo dataset loading for new users.
// ==============================================================================
