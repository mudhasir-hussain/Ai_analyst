export type ColumnType = 'numeric' | 'categorical' | 'boolean' | 'datetime' | 'text' | 'identifier';

export interface ColumnProfile {
  name: string;
  inferred_type: ColumnType;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  unique_percentage: number;
  min?: number;
  max?: number;
  mean?: number;
  median?: number;
  std?: number;
  q25?: number;
  q75?: number;
  skewness?: number;
  top_categories?: Record<string, number>;
  pii_detected?: string[];
}

export interface DatasetProfile {
  row_count: number;
  column_count: number;
  total_cells: number;
  total_nulls: number;
  null_percentage: number;
  duplicate_rows: number;
  duplicate_percentage: number;
  memory_bytes: number;
  candidate_keys: string[];
  columns: Record<string, ColumnProfile>;
}

export interface HealthIssue {
  code: string;
  level: 'critical' | 'warning' | 'info';
  column?: string;
  message: string;
  metric_value?: number;
  recommendation: string;
}

export interface DatasetHealth {
  dataset_id: string;
  version_id: string;
  health_score: number;
  rating: 'excellent' | 'good' | 'fair' | 'poor';
  total_issues: number;
  issues: HealthIssue[];
}

export interface DatasetVersion {
  id: string;
  dataset_id: string;
  parent_version_id?: string;
  version_number: number;
  storage_path: string;
  row_count: number;
  column_count: number;
  schema_json: Record<string, string>;
  profile_json: Record<string, any>;
  checksum: string;
  status: string;
  created_by: string;
  created_at: string;
}

export interface Dataset {
  id: string;
  project_id: string;
  owner_id: string;
  original_filename: string;
  source_format: string;
  sheet_name?: string;
  original_storage_path: string;
  active_version_id?: string;
  status: string;
  created_at: string;
}

export interface TransformImpactSummary {
  rows_before: number;
  rows_after: number;
  columns_before: number;
  columns_after: number;
  rows_removed: number;
  columns_removed: number;
  cells_modified: number;
  affected_columns: string[];
  execution_time_ms: number;
}

export interface TransformResponse {
  dataset_id: string;
  source_version_id: string;
  result_version_id: string;
  version_number: number;
  impact: TransformImpactSummary;
  new_version: DatasetVersion;
  operation: any;
}

export interface TransformPreviewResponse {
  dataset_id: string;
  source_version_id: string;
  impact: TransformImpactSummary;
  preview_rows: Record<string, any>[];
  total_preview_count: number;
}

export interface AIPlanOperation {
  type: string;
  column?: string;
  columns?: string[];
  [key: string]: any;
}

export interface AIPlanResponse {
  id?: string;
  plan_id: string;
  dataset_id: string;
  version_id: string;
  user_prompt: string;
  summary: string;
  operations: AIPlanOperation[];
  requires_confirmation: boolean;
  warnings: string[];
  expected_effect: Record<string, any>;
  validation_status: 'valid' | 'rejected';
  rejection_reason?: string;
  provider: string;
  model: string;
  created_at: string;
}

export interface ChartRecommendation {
  chart_type: 'bar' | 'line' | 'scatter' | 'box' | 'histogram' | 'heatmap';
  title: string;
  x_column?: string;
  y_column?: string;
  aggregation?: string;
  reason: string;
  config: Record<string, any>;
}

export interface VisualizationResponse {
  chart_type: string;
  title: string;
  x_column?: string;
  y_column?: string;
  data: Record<string, any>[];
  insights: string[];
  warnings: string[];
}

export interface DatasetVisualizationsResponse {
  dataset_id: string;
  version_id: string;
  recommended_charts: ChartRecommendation[];
  previews: VisualizationResponse[];
}

export interface InsightItem {
  category: 'quality' | 'correlation' | 'distribution' | 'trend' | 'risk';
  title: string;
  observation: string;
  implication?: string;
  supporting_metrics: Record<string, any>;
  confidence: 'high' | 'medium' | 'low';
}

export interface ReportResponse {
  id: string;
  dataset_id: string;
  version_id: string;
  version_number: number;
  title: string;
  format: 'json' | 'markdown' | 'html';
  executive_summary: string;
  health_score: number;
  insights: InsightItem[];
  content?: string;
  created_at: string;
  created_by: string;
}

export interface VersionDiffColumnChange {
  column: string;
  change_type: 'added' | 'removed' | 'type_changed' | 'modified' | 'unchanged';
  source_type?: string;
  target_type?: string;
  source_null_count?: number;
  target_null_count?: number;
  null_delta?: number;
  stats_delta?: Record<string, any>;
}

export interface VersionDiffResponse {
  dataset_id: string;
  source_version_id: string;
  source_version_number: number;
  target_version_id: string;
  target_version_number: number;
  rows_source: number;
  rows_target: number;
  rows_diff: number;
  columns_source: number;
  columns_target: number;
  columns_diff: number;
  added_columns: string[];
  removed_columns: string[];
  type_changed_columns: string[];
  column_changes: VersionDiffColumnChange[];
  summary: string;
}

export interface RollbackResponse {
  dataset_id: string;
  restored_from_version_id: string;
  restored_from_version_number: number;
  new_version: DatasetVersion;
  impact: TransformImpactSummary;
  message: string;
}

export interface AuditTimelineEvent {
  id: string;
  event_type: 'upload' | 'transformation' | 'ai_plan' | 'rollback';
  source: 'system' | 'manual' | 'ai' | 'rollback';
  timestamp: string;
  version_id?: string;
  version_number?: number;
  summary: string;
  user_id: string;
  impact?: Record<string, any>;
  metadata: Record<string, any>;
}

export interface AuditTimelineResponse {
  dataset_id: string;
  total_events: number;
  events: AuditTimelineEvent[];
}

export interface MLTargetCandidate {
  column: string;
  task_type: 'regression' | 'classification';
  data_type: string;
  unique_values: number;
  null_count: number;
}

export interface MLLossEpochPoint {
  epoch: number;
  loss: number;
  val_loss?: number;
}

export interface MLPredictionPoint {
  actual: number;
  predicted: number;
  residual?: number;
}

export interface MLFeatureImportance {
  feature: string;
  importance: number;
}

export interface MLConfusionMatrix {
  labels: string[];
  matrix: number[][];
  total_samples: number;
}

export interface MLEvaluationMetrics {
  task_type: 'regression' | 'classification';
  train_score: number;
  test_score: number;
  overfitting_score: number;
  overfitting_status: 'healthy_generalization' | 'moderate_overfitting' | 'severe_overfitting' | 'underfitting';
  overfitting_explanation: string;
  regression_metrics?: {
    r2_score: number;
    rmse: number;
    mae: number;
    mape_percent: number;
  };
  classification_metrics?: {
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
  };
  confusion_matrix?: MLConfusionMatrix;
}

export interface MLTrainResponse {
  model_name: string;
  model_type: string;
  target_column: string;
  task_type: 'regression' | 'classification';
  version_number: number;
  total_samples: number;
  feature_count: number;
  metrics: MLEvaluationMetrics;
  feature_importance: MLFeatureImportance[];
  loss_curve: MLLossEpochPoint[];
  predictions: MLPredictionPoint[];
  educational_takeaways: string[];
}

export interface MLTrainRequest {
  target_column: string;
  model_type: string;
  test_size?: number;
  hyperparameters?: Record<string, any>;
  version_id?: string;
  selected_features?: string[];
}

export interface MLCompareResponse {
  model_type: string;
  target_column: string;
  task_type: 'regression' | 'classification';
  base_version: MLTrainResponse;
  target_version: MLTrainResponse;
  score_delta: number;
  rmse_delta?: number;
  overfitting_gap_reduction: number;
  summary: string;
}

export interface MLCompareRequest {
  target_column: string;
  model_type: string;
  base_version_number?: number;
  target_version_number?: number;
  hyperparameters?: Record<string, any>;
  selected_features?: string[];
}


// ==============================================================================
// FILE SUMMARY: frontend/src/types/api.ts
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This file defines all TypeScript types and interfaces mirroring the backend
// Pydantic schemas:
//   1. Core Dataset & Profile schemas (Dataset, DatasetVersion, DatasetProfile, ColumnProfile).
//   2. Health scorecard schemas (DatasetHealth, HealthIssue).
//   3. Transformation & Operation schemas (TransformImpactSummary, TransformResponse, TransformPreviewResponse).
//   4. AI Plan schemas (AIPlanOperation, AIPlanResponse).
//   5. Visualization schemas (ChartRecommendation, VisualizationResponse, DatasetVisualizationsResponse).
//   6. Narrative report schemas (InsightItem, ReportResponse).
//   7. Versioning, Lineage & Rollback schemas (VersionDiffColumnChange, VersionDiffResponse, RollbackResponse).
//   8. Audit Timeline schemas (AuditTimelineEvent, AuditTimelineResponse).
//
// HOW IT CONNECTS TO OTHER FILES:
// - Imported by 'frontend/src/services/api.ts' to strictly type all API network requests and responses.
// - Imported by all UI components in 'frontend/src/components/' for prop contracts and state management.
// ==============================================================================
