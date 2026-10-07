import warnings
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

warnings.filterwarnings("ignore", message='.*Field name "schema_json".*shadows an attribute in parent "BaseModel".*')

UUID4 = UUID

class ProfileBase(BaseModel):
    display_name: Optional[str] = Field(None, description="The user's display name.")
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Key-value user preferences (e.g. theme).")

class ProfileResponse(ProfileBase):
    id: UUID4 = Field(..., description="Corresponds to the Supabase Auth user ID (UUID).")
    created_at: datetime = Field(..., description="Timestamp when the profile was created.")

    model_config = {"from_attributes": True}


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=100, description="The name of the project.")
    description: Optional[str] = Field(None, max_length=500, description="Brief details about the project.")

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: UUID4
    owner_id: UUID4
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DatasetBase(BaseModel):
    original_filename: str = Field(..., description="Original name of the uploaded CSV/XLSX file.")
    source_format: str = Field(..., description="File format (e.g. 'csv' or 'xlsx').")
    sheet_name: Optional[str] = Field(None, description="Sheet name chosen for XLSX workbooks.")

class DatasetCreate(DatasetBase):
    project_id: UUID4
    original_storage_path: str = Field(..., description="Path to the original file in Supabase Storage.")

class DatasetResponse(DatasetBase):
    id: UUID4
    project_id: UUID4
    owner_id: UUID4
    original_storage_path: str
    active_version_id: Optional[UUID4] = None
    status: str = Field(..., description="Current processing status (e.g. 'processing', 'active', 'failed').")
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID4
    dataset_id: UUID4
    parent_version_id: Optional[UUID4] = None
    version_number: int = Field(..., description="Sequential version counter (starting at 1).")
    storage_path: str = Field(..., description="Path to the Parquet/CSV file representing this version in Storage.")
    row_count: int = Field(..., description="Number of rows in this version.")
    column_count: int = Field(..., description="Number of columns in this version.")
    schema_json: Dict[str, Any] = Field(..., description="JSON representation of inferred column types.")
    profile_json: Dict[str, Any] = Field(..., description="Statistical summary profile of the dataset.")
    checksum: str = Field(..., description="SHA-256 hash value of the version file.")
    status: str = Field(..., description="Status of this version (e.g. 'active', 'failed').")
    created_by: UUID4
    created_at: datetime


class DatasetProfileResponse(BaseModel):
    dataset_id: UUID4
    version_id: UUID4
    profile: Dict[str, Any] = Field(..., description="Comprehensive statistics, quantiles, and PII flags.")


class HealthIssue(BaseModel):
    code: str = Field(..., description="Machine readable issue code.")
    level: str = Field(..., description="Severity level: 'critical', 'warning', or 'info'.")
    column: Optional[str] = Field(None, description="Affected column name, if applicable.")
    message: str = Field(..., description="Human readable description of the issue.")
    metric_value: Optional[float] = Field(None, description="Associated metric numeric value.")
    recommendation: str = Field(..., description="Suggested cleaning or remediation action.")


class DatasetHealthResponse(BaseModel):
    dataset_id: UUID4
    version_id: UUID4
    health_score: int = Field(..., ge=0, le=100, description="Overall dataset health score from 0 to 100.")
    rating: str = Field(..., description="Health category: 'excellent', 'good', 'fair', or 'poor'.")
    total_issues: int = Field(..., description="Total count of detected quality issues.")
    issues: List[HealthIssue] = Field(default_factory=list, description="List of quality issues and recommendations.")


class OperationCreate(BaseModel):
    dataset_id: UUID4
    source_version_id: UUID4
    source: str = Field("manual", description="Source of the command: 'manual', 'ai', or 'system'.")
    operation_plan_json: Dict[str, Any] = Field(..., description="Structured JSON representation of operations to perform.")
    summary: str = Field(..., description="Plain-language description of the action.")

class OperationResponse(BaseModel):
    id: UUID4
    dataset_id: UUID4
    source_version_id: UUID4
    result_version_id: Optional[UUID4] = None
    initiated_by: UUID4
    source: str
    operation_plan_json: Dict[str, Any]
    summary: str
    status: str = Field(..., description="Execution status: 'pending', 'success', 'failed'.")
    impact_json: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TransformRequest(BaseModel):
    operations: List[Dict[str, Any]] = Field(..., min_length=1, description="List of sequential structured operations to execute.")
    summary: Optional[str] = Field(None, description="Human-readable description of this transformation batch.")
    source: str = Field("manual", description="Originator of the action: 'manual', 'ai', or 'system'.")


class TransformImpactSummary(BaseModel):
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    rows_removed: int
    columns_removed: int
    cells_modified: int
    affected_columns: List[str]
    execution_time_ms: float


class TransformResponse(BaseModel):
    dataset_id: UUID4
    source_version_id: UUID4
    result_version_id: UUID4
    version_number: int
    impact: TransformImpactSummary
    new_version: DatasetVersionResponse
    operation: OperationResponse


class TransformPreviewResponse(BaseModel):
    dataset_id: UUID4
    source_version_id: UUID4
    impact: TransformImpactSummary
    sample_preview: List[Dict[str, Any]]


class AIPlanCreate(BaseModel):
    user_prompt: str = Field(..., description="The user's natural language request.")

class AIPlanResponse(BaseModel):
    id: UUID4
    plan_id: Optional[UUID4] = None
    dataset_id: UUID4
    version_id: UUID4
    requested_by: UUID4
    user_prompt: str
    provider: str
    model: str
    summary: Optional[str] = None
    operations: Optional[List[Dict[str, Any]]] = None
    warnings: Optional[List[str]] = None
    plan_json: Dict[str, Any]
    validation_status: str = Field(..., description="Validation outcome: 'validated', 'invalid', 'rejected'.")
    warnings_json: List[str] = Field(default_factory=list, description="Warnings generated during validation checks.")
    created_at: datetime

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    id: UUID4
    owner_id: UUID4
    dataset_id: Optional[UUID4] = None
    version_id: Optional[UUID4] = None
    job_type: str = Field(..., description="Type of job, e.g. 'profile', 'operation', 'export'.")
    status: str = Field(..., description="Current progress status: 'queued', 'running', 'completed', 'failed'.")
    progress: int = Field(0, ge=0, le=100, description="Percentage of progress (0 to 100).")
    payload_json: Optional[Dict[str, Any]] = None
    result_json: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DatasetStatisticsResponse(BaseModel):
    dataset_id: UUID4
    version_id: UUID4
    row_count: int
    column_count: int
    numeric_summary: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Detailed statistics (mean, median, std, min, max, skew, kurtosis, quantiles).")
    categorical_summary: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Categorical distributions (uniques, frequencies, top categories).")
    correlations: Dict[str, Any] = Field(default_factory=dict, description="Pearson correlation matrix and significant correlated pairs.")
    temporal_trends: List[Dict[str, Any]] = Field(default_factory=list, description="Trend analysis for datetime and sequential features.")


class ChartRecommendation(BaseModel):
    chart_type: str = Field(..., description="Chart type: 'bar', 'line', 'scatter', 'box', 'histogram', 'heatmap'.")
    title: str = Field(..., description="Suggested chart title.")
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    aggregation: Optional[str] = None
    reason: str = Field(..., description="Explanation of why this visualization is informative.")
    config: Dict[str, Any] = Field(default_factory=dict, description="Frontend rendering configuration.")


class VisualizationRequest(BaseModel):
    chart_type: str = Field(..., description="Chart type: 'bar', 'line', 'scatter', 'box', 'histogram', 'heatmap'.")
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    group_by_column: Optional[str] = None
    aggregation: Optional[str] = Field("sum", description="Aggregation function: 'sum', 'mean', 'count', 'min', 'max', 'median', 'none'.")
    limit: Optional[int] = Field(20, ge=1, le=1000, description="Max data items to return.")


class VisualizationResponse(BaseModel):
    chart_type: str
    title: str
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    data: List[Dict[str, Any]] = Field(..., description="Aggregated series ready for chart rendering.")
    insights: List[str] = Field(default_factory=list, description="Statistical insights extracted from the visualization.")
    warnings: List[str] = Field(default_factory=list, description="Quality warnings (e.g. high cardinality, missing values).")


class DatasetVisualizationsResponse(BaseModel):
    dataset_id: UUID4
    version_id: UUID4
    recommended_charts: List[ChartRecommendation] = Field(default_factory=list)
    previews: List[VisualizationResponse] = Field(default_factory=list)


class InsightItem(BaseModel):
    category: str = Field(..., description="Category: 'quality', 'correlation', 'distribution', 'trend', 'risk'.")
    title: str = Field(..., description="Short finding headline.")
    observation: str = Field(..., description="Factual statistical observation.")
    implication: Optional[str] = Field(None, description="Analytical interpretation or actionable advice.")
    supporting_metrics: Dict[str, Any] = Field(default_factory=dict, description="Related numbers and metrics.")
    confidence: str = Field("high", description="Confidence level: 'high', 'medium', 'low'.")


class ReportCreateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Optional custom report title.")
    format: str = Field("json", description="Output format: 'json', 'markdown', or 'html'.")
    include_charts: bool = Field(True, description="Whether to include visualization recommendations.")
    include_transform_history: bool = Field(True, description="Whether to include audit history of transformations.")


class ReportResponse(BaseModel):
    id: UUID4
    dataset_id: UUID4
    version_id: UUID4
    version_number: int
    title: str
    format: str
    executive_summary: str
    health_score: int
    insights: List[InsightItem] = Field(default_factory=list)
    content: Optional[str] = Field(None, description="Formatted Markdown or HTML document string if requested.")
    created_at: datetime
    created_by: UUID4

    model_config = {"from_attributes": True}


class ExportRequest(BaseModel):
    format: str = Field("csv", description="File format to download: 'csv' or 'xlsx'.")


class VersionDiffColumnChange(BaseModel):
    column: str = Field(..., description="Column name evaluated in diff.")
    change_type: str = Field(..., description="Change category: 'added', 'removed', 'type_changed', 'modified', or 'unchanged'.")
    source_type: Optional[str] = Field(None, description="Inferred data type in source version.")
    target_type: Optional[str] = Field(None, description="Inferred data type in target version.")
    source_null_count: Optional[int] = Field(None, description="Null count in source version.")
    target_null_count: Optional[int] = Field(None, description="Null count in target version.")
    null_delta: Optional[int] = Field(None, description="Change in null count (target - source).")
    stats_delta: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Numerical metric differences (mean, min, max deltas).")


class VersionDiffResponse(BaseModel):
    dataset_id: UUID4
    source_version_id: UUID4
    source_version_number: int
    target_version_id: UUID4
    target_version_number: int
    rows_source: int
    rows_target: int
    rows_diff: int
    columns_source: int
    columns_target: int
    columns_diff: int
    added_columns: List[str] = Field(default_factory=list)
    removed_columns: List[str] = Field(default_factory=list)
    type_changed_columns: List[str] = Field(default_factory=list)
    column_changes: List[VersionDiffColumnChange] = Field(default_factory=list)
    summary: str = Field(..., description="Plain-English explanation of differences between the two versions.")


class RollbackRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Optional note or explanation for the rollback action.")


class RollbackResponse(BaseModel):
    dataset_id: UUID4
    restored_from_version_id: UUID4
    restored_from_version_number: int
    new_version: DatasetVersionResponse
    impact: TransformImpactSummary
    message: str


class AuditTimelineEvent(BaseModel):
    id: UUID4
    event_type: str = Field(..., description="Type of audit event: 'upload', 'transformation', 'ai_plan', 'rollback'.")
    source: str = Field("system", description="Initiator: 'system', 'manual', 'ai', or 'rollback'.")
    timestamp: datetime
    version_id: Optional[UUID4] = None
    version_number: Optional[int] = None
    summary: str = Field(..., description="Plain-language event description.")
    user_id: UUID4
    impact: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditTimelineResponse(BaseModel):
    dataset_id: UUID4
    total_events: int
    events: List[AuditTimelineEvent] = Field(default_factory=list)


# ==============================================================================
# FILE SUMMARY: backend/models/schemas.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file defines the core Pydantic data models (Data Transfer Objects and database
# row representations) for the entire platform:
#   1. Profile schemas ('ProfileBase', 'ProfileResponse'): User metadata and theme preferences.
#   2. Project schemas ('ProjectBase', 'ProjectCreate', 'ProjectResponse'): User project workspaces.
#   3. Dataset schemas ('DatasetBase', 'DatasetCreate', 'DatasetResponse'): Tabular file upload records.
#   4. Version & Health schemas ('DatasetVersionResponse', 'DatasetProfileResponse', 'HealthIssue',
#      'DatasetHealthResponse'): Immutable dataset snapshot versions, statistical profiles,
#      and quality health audit scorecards.
#   5. Operations & Transformations ('OperationCreate', 'OperationResponse', 'TransformRequest',
#      'TransformImpactSummary', 'TransformResponse', 'TransformPreviewResponse'): Auditable data
#      transformations, cleaning actions, and before/after impact summaries.
#   6. AI Plan schemas ('AIPlanCreate', 'AIPlanResponse'): Natural language prompts and validated
#      JSON structured cleaning plans generated by the LLM.
#   7. Statistics & Visualizations ('DatasetStatisticsResponse', 'ChartRecommendation',
#      'VisualizationRequest', 'VisualizationResponse', 'DatasetVisualizationsResponse'):
#      Descriptive stats, correlation matrices, chart recommendations, and frontend chart series.
#   8. Reports & Exports ('InsightItem', 'ReportCreateRequest', 'ReportResponse', 'ExportRequest'):
#      Executive summaries, structured narrative insights, and multi-format downloadable reports.
#   9. History, Versioning & Timeline ('VersionDiffColumnChange', 'VersionDiffResponse',
#      'RollbackRequest', 'RollbackResponse', 'AuditTimelineEvent', 'AuditTimelineResponse'):
#      Dataset version comparison diffs, safe rollback restore payloads, and chronological audit history.
#   10. Job schemas ('JobResponse'): Asynchronous task tracking, progress %, and execution status.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Serves as the central data contract between the API routers, domain services, and database.
# - Imported by 'backend/api/datasets.py', 'backend/services/reports/', and 'backend/services/history/'
#   for typing endpoint request/response models.
# - Configures Pydantic's 'from_attributes = True' to allow ORM/dictionary conversion
#   directly from Supabase query results.
# ==============================================================================

