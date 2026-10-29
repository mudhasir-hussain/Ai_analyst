import type {
  Dataset,
  DatasetHealth,
  DatasetProfile,
  DatasetVersion,
  DatasetVisualizationsResponse,
  VisualizationResponse,
  TransformResponse,
  TransformPreviewResponse,
  AIPlanResponse,
  ReportResponse,
  VersionDiffResponse,
  RollbackResponse,
  AuditTimelineResponse,
  MLTargetCandidate,
  MLTrainRequest,
  MLTrainResponse,
  MLCompareRequest,
  MLCompareResponse,
  MLPredictResponse,
  AIAskResponse
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('ai_analyst_token') || 'mock-token';
  return {
    Authorization: `Bearer ${token}`
  };
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorJson.message || errorDetail;
    } catch {
      // Fallback to text
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // 1. Dataset Upload
  async uploadDataset(
    file: File,
    projectId: string = '00000000-0000-0000-0000-000000000000',
    sheetName?: string
  ): Promise<Dataset> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', projectId);
    if (sheetName) {
      formData.append('sheet_name', sheetName);
    }

    const res = await fetch(`${API_BASE}/datasets/upload`, {
      method: 'POST',
      headers: {
        ...getAuthHeader()
      },
      body: formData
    });
    return handleResponse<Dataset>(res);
  },

  // 2. Profile
  async getDatasetProfile(datasetId: string): Promise<DatasetProfile> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/profile`, {
      headers: { ...getAuthHeader() }
    });
    const data = await handleResponse<any>(res);
    const p = data.profile || data;
    return {
      ...p,
      row_count: p.row_count ?? 0,
      column_count: p.column_count ?? 0,
      total_cells: p.total_cells ?? ((p.row_count ?? 0) * (p.column_count ?? 0)),
      total_nulls: p.total_nulls ?? p.total_null_cells ?? 0,
      null_percentage: p.null_percentage ?? 0,
      duplicate_rows: p.duplicate_rows ?? 0,
      duplicate_percentage: p.duplicate_percentage ?? 0,
      memory_bytes: p.memory_bytes ?? p.estimated_memory_bytes ?? 0,
      candidate_keys: Array.isArray(p.candidate_keys) ? p.candidate_keys : [],
      columns: p.columns || {}
    };
  },

  // 3. Health Scorecard
  async getDatasetHealth(datasetId: string): Promise<DatasetHealth> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/health`, {
      headers: { ...getAuthHeader() }
    });
    const data = await handleResponse<any>(res);
    return {
      ...data,
      health_score: data.health_score ?? 100,
      rating: data.rating || 'good',
      total_issues: data.total_issues ?? (Array.isArray(data.issues) ? data.issues.length : 0),
      issues: Array.isArray(data.issues) ? data.issues : []
    };
  },

  // 4. Preview Data (Rows & Columns)
  async getDatasetPreview(
    datasetId: string,
    limit: number = 50
  ): Promise<{ columns: string[]; rows: Record<string, any>[]; total_rows: number }> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/preview?limit=${limit}`, {
      headers: { ...getAuthHeader() }
    });
    return handleResponse<any>(res);
  },

  // 5. Statistics
  async getDatasetStatistics(datasetId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/statistics`, {
      headers: { ...getAuthHeader() }
    });
    return handleResponse<any>(res);
  },

  // 6. Visualizations Recommendations & Previews
  async getDatasetVisualizations(datasetId: string): Promise<DatasetVisualizationsResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/visualizations`, {
      method: 'GET',
      headers: {
        ...getAuthHeader()
      }
    });
    return handleResponse<DatasetVisualizationsResponse>(res);
  },

  // 7. Custom Visualization Request
  async requestVisualization(
    datasetId: string,
    req: {
      chart_type: string;
      x_column?: string;
      y_column?: string;
      group_by_column?: string;
      aggregation?: string;
      limit?: number;
    }
  ): Promise<VisualizationResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/visualizations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      },
      body: JSON.stringify(req)
    });
    return handleResponse<VisualizationResponse>(res);
  },

  // 8. Transform Preview
  async previewTransform(
    datasetId: string,
    operations: Record<string, any>[]
  ): Promise<TransformPreviewResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/transform/preview`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      },
      body: JSON.stringify({ operations })
    });
    return handleResponse<TransformPreviewResponse>(res);
  },

  // 9. Apply Transform
  async applyTransform(
    datasetId: string,
    operations: Record<string, any>[],
    summary?: string,
    source: string = 'manual'
  ): Promise<TransformResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/transform`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      },
      body: JSON.stringify({ operations, summary, source })
    });
    return handleResponse<TransformResponse>(res);
  },

  // 10. AI Operation Planner
  async createAIPlan(datasetId: string, userPrompt: string): Promise<AIPlanResponse> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 75000);
    try {
      const res = await fetch(`${API_BASE}/datasets/${datasetId}/ai/plan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader()
        },
        body: JSON.stringify({ user_prompt: userPrompt }),
        signal: controller.signal
      });
      const raw = await handleResponse<any>(res);
      const planJson = raw.plan_json || {};
      return {
        id: raw.id || raw.plan_id,
        plan_id: raw.plan_id || raw.id,
        dataset_id: raw.dataset_id,
        version_id: raw.version_id,
        user_prompt: raw.user_prompt,
        summary: raw.summary || planJson.summary || 'Proposed Transformation Plan',
        operations: raw.operations || planJson.operations || [],
        requires_confirmation: raw.requires_confirmation ?? planJson.requires_confirmation ?? true,
        warnings: raw.warnings || raw.warnings_json || planJson.warnings || [],
        expected_effect: raw.expected_effect || {},
        validation_status: raw.validation_status || 'validated',
        rejection_reason: raw.rejection_reason,
        provider: raw.provider,
        model: raw.model,
        created_at: raw.created_at
      };
    } catch (err: any) {
      if (err.name === 'AbortError') {
        throw new Error('AI planning request timed out after 75s. The AI model took too long to respond.');
      }
      throw err;
    } finally {
      clearTimeout(timeoutId);
    }
  },

  // 11. Approve AI Plan
  async approveAIPlan(datasetId: string, planId: string): Promise<TransformResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/ai/plan/${planId}/approve`, {
      method: 'POST',
      headers: {
        ...getAuthHeader()
      }
    });
    return handleResponse<TransformResponse>(res);
  },

  // 12. Create Executive Report
  async generateReport(
    datasetId: string,
    format: 'json' | 'markdown' | 'html' = 'json',
    title?: string
  ): Promise<ReportResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/reports`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      },
      body: JSON.stringify({ format, title, include_charts: true, include_transform_history: true })
    });
    return handleResponse<ReportResponse>(res);
  },

  // 13. Get Report by ID
  async getReport(reportId: string): Promise<ReportResponse> {
    const res = await fetch(`${API_BASE}/reports/${reportId}`, {
      headers: { ...getAuthHeader() }
    });
    return handleResponse<ReportResponse>(res);
  },

  // 14. Export Dataset Download
  async exportDataset(datasetId: string, format: 'csv' | 'xlsx'): Promise<Blob> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      },
      body: JSON.stringify({ format })
    });
    if (!res.ok) {
      throw new Error(`Export failed with status ${res.status}`);
    }
    return res.blob();
  },

  // 15. Version History & Diffing
  async listVersions(datasetId: string): Promise<DatasetVersion[]> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/versions`, {
      headers: { ...getAuthHeader() }
    });
    return handleResponse<DatasetVersion[]>(res);
  },

  async getVersion(datasetId: string, versionId: string): Promise<DatasetVersion> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/versions/${versionId}`, {
      headers: { ...getAuthHeader() }
    });
    return handleResponse<DatasetVersion>(res);
  },

  async diffVersions(
    datasetId: string,
    versionId: string,
    targetVersionId?: string
  ): Promise<VersionDiffResponse> {
    const url = targetVersionId
      ? `${API_BASE}/datasets/${datasetId}/versions/${versionId}/diff?target_version_id=${targetVersionId}`
      : `${API_BASE}/datasets/${datasetId}/versions/${versionId}/diff`;
    const res = await fetch(url, {
      headers: { ...getAuthHeader() }
    });
    return handleResponse<VersionDiffResponse>(res);
  },

  async rollbackVersion(
    datasetId: string,
    versionId: string,
    reason?: string
  ): Promise<RollbackResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/versions/${versionId}/rollback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      },
      body: JSON.stringify({ reason })
    });
    return handleResponse<RollbackResponse>(res);
  },

  // 16. Audit Timeline
  async getTimeline(datasetId: string): Promise<AuditTimelineResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/timeline`, {
      headers: { ...getAuthHeader() }
    });
    return handleResponse<AuditTimelineResponse>(res);
  },

  // 17. ML Impact Lab & Pedagogical Model Engine
  async getMLTargets(datasetId: string): Promise<MLTargetCandidate[]> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/ml/targets`, {
      headers: { ...getAuthHeader() }
    });
    const data = await handleResponse<any>(res);
    return Array.isArray(data) ? data : (data?.candidates || []);
  },

  async trainMLModel(datasetId: string, req: MLTrainRequest): Promise<MLTrainResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/ml/train`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      },
      body: JSON.stringify(req)
    });
    return handleResponse<MLTrainResponse>(res);
  },

  async compareMLVersions(datasetId: string, req: MLCompareRequest): Promise<MLCompareResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/ml/compare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      },
      body: JSON.stringify(req)
    });
    return handleResponse<MLCompareResponse>(res);
  },

  // 17. ML Single-Record Live Prediction
  async predictMLModel(datasetId: string, features: Record<string, any>): Promise<MLPredictResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/ml/predict`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      },
      body: JSON.stringify({ features })
    });
    return handleResponse<MLPredictResponse>(res);
  },

  // 18. Export Standalone ML Inference Code
  async exportMLCode(datasetId: string): Promise<{ code: string; filename: string }> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/ml/export-code`, {
      headers: getAuthHeader()
    });
    return handleResponse<{ code: string; filename: string }>(res);
  },

  // 19. 1-Click AI Auto-Heal Dataset Health
  async autoHealDataset(datasetId: string): Promise<TransformResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/ai/auto-heal`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      }
    });
    return handleResponse<TransformResponse>(res);
  },

  // 20. 'Talk to Your Data' Analytical Q&A
  async askAIAboutDataset(datasetId: string, question: string): Promise<AIAskResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/ai/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader()
      },
      body: JSON.stringify({ question })
    });
    return handleResponse<AIAskResponse>(res);
  }
};


// ==============================================================================
// FILE SUMMARY: frontend/src/services/api.ts
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This file is the primary HTTP client service connecting the React frontend to the FastAPI backend:
//   1. Manages authentication credentials ('Bearer mock-token' or stored Supabase JWT).
//   2. Wraps fetch calls with centralized status verification and error parsing ('handleResponse').
//   3. Provides typed methods for all 16 backend platform endpoints:
//      - Ingestion: uploadDataset.
//      - Inspection: getDatasetProfile, getDatasetHealth, getDatasetPreview.
//      - Analysis: getDatasetStatistics, getDatasetVisualizations, requestVisualization.
//      - Transformations: previewTransform, applyTransform.
//      - AI Planning: createAIPlan, approveAIPlan.
//      - Reporting & Export: generateReport, getReport, exportDataset.
//      - Lineage & Versions: listVersions, getVersion, diffVersions, rollbackVersion, getTimeline.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Imports typed response models from 'frontend/src/types/api.ts'.
// - Imported by 'frontend/src/App.tsx' and UI components in 'frontend/src/components/'
//   to perform real-time data fetching and transformations.
// ==============================================================================
