import { useState, useEffect } from 'react';
import { api } from './services/api';
import type {
  Dataset,
  DatasetHealth,
  DatasetProfile,
  DatasetVersion,
  DatasetVisualizationsResponse,
  ReportResponse,
  VersionDiffResponse,
  AuditTimelineResponse,
  TransformImpactSummary
} from './types/api';

import { Navbar } from './components/Navbar';
import { UploadModal } from './components/UploadModal';
import { HealthScorecard } from './components/HealthScorecard';
import { DataTable } from './components/DataTable';
import { TransformToolbar } from './components/TransformToolbar';
import { AIAssistantPanel } from './components/AIAssistantPanel';
import { VisualizationsTab } from './components/VisualizationsTab';
import { ReportsTab } from './components/ReportsTab';
import { VersionHistoryDrawer } from './components/VersionHistoryDrawer';
import { MLLabTab } from './components/MLLabTab';
import { getSampleDatasetFile, getMLBenchmarkDatasetFile } from './data/sampleDataset';

export function App() {
  const [activeTab, setActiveTab] = useState<'table' | 'health' | 'visualizations' | 'reports' | 'history' | 'ml'>('table');
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [versions, setVersions] = useState<DatasetVersion[]>([]);
  const [activeVersion, setActiveVersion] = useState<DatasetVersion | null>(null);
  const [previewData, setPreviewData] = useState<{ columns: string[]; rows: any[]; total_rows: number }>({
    columns: [],
    rows: [],
    total_rows: 0
  });
  const [health, setHealth] = useState<DatasetHealth | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [visualizations, setVisualizations] = useState<DatasetVisualizationsResponse | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [reportFormat, setReportFormat] = useState<'markdown' | 'html' | 'json'>('markdown');
  const [timeline, setTimeline] = useState<AuditTimelineResponse | null>(null);

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isAIAssistantOpen, setIsAIAssistantOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isGeneratingAIPlan, setIsGeneratingAIPlan] = useState(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const refreshDatasetDetails = async (datasetId: string) => {
    try {
      const [prev, hlth, prof, vis, vers, tline] = await Promise.all([
        api.getDatasetPreview(datasetId, 50).catch(() => ({ columns: [], rows: [], total_rows: 0 })),
        api.getDatasetHealth(datasetId).catch(() => null),
        api.getDatasetProfile(datasetId).catch(() => null),
        api.getDatasetVisualizations(datasetId).catch(() => null),
        api.listVersions(datasetId).catch(() => []),
        api.getTimeline(datasetId).catch(() => null)
      ]);

      setPreviewData(prev);
      setHealth(hlth);
      setProfile(prof);
      setVisualizations(vis);
      setVersions(vers);
      setTimeline(tline);

      if (vers.length > 0) {
        setActiveVersion(vers[vers.length - 1]);
      }
    } catch (err: any) {
      console.error("Error refreshing dataset details:", err);
    }
  };

  // Upload handler
  const handleUploadSuccess = async (file: File, sheetName?: string) => {
    setIsProcessing(true);
    setReport(null);
    try {
      const newDataset = await api.uploadDataset(file, undefined, sheetName);
      setDataset(newDataset);
      await refreshDatasetDetails(newDataset.id);
      showToast(`Dataset '${file.name}' successfully uploaded and profiled!`, 'success');
      setActiveTab('table');
    } catch (err: any) {
      showToast(err.message || 'Upload failed', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Sample data loader for quick demo
  const handleLoadSample = async () => {
    setIsProcessing(true);
    try {
      const file = getSampleDatasetFile();
      await handleUploadSuccess(file);
      showToast('Loaded Global Enterprise Sales benchmark dataset!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Sample load failed', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleLoadMLBenchmark = async () => {
    setIsProcessing(true);
    try {
      const file = getMLBenchmarkDatasetFile();
      await handleUploadSuccess(file);
      showToast('Loaded SaaS Customer Churn ML benchmark (146 records, churn & LTV targets)!', 'success');
      setActiveTab('ml');
    } catch (err: any) {
      showToast(err.message || 'ML benchmark load failed', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Manual transform application
  const handleApplyTransform = async (operations: any[], summary: string) => {
    if (!dataset) {
      showToast('Please upload a dataset or load the sample data first.', 'info');
      return;
    }
    setIsProcessing(true);
    try {
      const res = await api.applyTransform(dataset.id, operations, summary);
      showToast(`Committed Version ${res.version_number}: ${summary}`, 'success');
      await refreshDatasetDetails(dataset.id);
    } catch (err: any) {
      showToast(err.message || 'Transform failed', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Manual transform preview
  const handlePreviewTransform = async (operations: any[]): Promise<TransformImpactSummary | null> => {
    if (!dataset) {
      showToast('Please upload a dataset or load the sample data first.', 'info');
      return null;
    }
    try {
      const res = await api.previewTransform(dataset.id, operations);
      return res.impact;
    } catch (err: any) {
      showToast(err.message || 'Preview failed', 'error');
      return null;
    }
  };

  // AI plan submission
  const handleSubmitAIPrompt = async (prompt: string) => {
    if (!dataset) {
      showToast('Please upload a dataset or load the sample data first.', 'info');
      throw new Error("Please upload a dataset or load the sample data first.");
    }
    setIsGeneratingAIPlan(true);
    try {
      return await api.createAIPlan(dataset.id, prompt);
    } finally {
      setIsGeneratingAIPlan(false);
    }
  };

  // AI plan approval
  const handleApproveAIPlan = async (planId: string) => {
    if (!dataset) {
      showToast('Please upload a dataset or load the sample data first.', 'info');
      return;
    }
    setIsProcessing(true);
    try {
      const res = await api.approveAIPlan(dataset.id, planId);
      showToast(`AI Plan approved! Created Version ${res.version_number}.`, 'success');
      await refreshDatasetDetails(dataset.id);
    } catch (err: any) {
      showToast(err.message || 'AI plan execution failed', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Executive report generator
  const handleGenerateReport = async (
    format: 'markdown' | 'html' | 'json' = reportFormat,
    title?: string,
    showNotification = true
  ) => {
    if (!dataset) {
      if (showNotification) showToast('Please upload a dataset or load the sample data first.', 'info');
      return;
    }
    setIsGeneratingReport(true);
    try {
      const res = await api.generateReport(dataset.id, format, title);
      setReport(res);
      setReportFormat(format);
      if (showNotification) {
        showToast(`Generated ${format.toUpperCase()} executive report for v${res.version_number}!`, 'success');
      }
    } catch (err: any) {
      if (showNotification) {
        showToast(err.message || 'Report generation failed', 'error');
      }
    } finally {
      setIsGeneratingReport(false);
    }
  };

  // Automatically refresh or generate executive report when on the 'reports' tab
  // whenever the active preprocessed dataset version changes or if no report is loaded
  useEffect(() => {
    if (activeTab === 'reports' && dataset && activeVersion && !isGeneratingReport) {
      if (!report || report.version_number !== activeVersion.version_number) {
        handleGenerateReport(reportFormat, undefined, false);
      }
    }
  }, [activeTab, activeVersion?.version_number, activeVersion?.id, dataset?.id]);

  // File export download
  const handleExportDataset = async (format: 'csv' | 'xlsx') => {
    if (!dataset) {
      showToast('Please upload a dataset or load the sample data first.', 'info');
      return;
    }
    setIsProcessing(true);
    try {
      const blob = await api.exportDataset(dataset.id, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${dataset.original_filename.replace(/\.[^/.]+$/, "")}_v${activeVersion?.version_number || 1}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast(`Exported active version as ${format.toUpperCase()}`, 'success');
    } catch (err: any) {
      showToast(err.message || 'Export failed', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Version diffing
  const handleDiffVersions = async (sourceVersionId: string, targetVersionId?: string): Promise<VersionDiffResponse> => {
    if (!dataset) {
      showToast('Please upload a dataset or load the sample data first.', 'info');
      throw new Error("No dataset loaded.");
    }
    return await api.diffVersions(dataset.id, sourceVersionId, targetVersionId);
  };

  // Version rollback
  const handleRollbackVersion = async (versionId: string, reason?: string) => {
    if (!dataset) {
      showToast('Please upload a dataset or load the sample data first.', 'info');
      return;
    }
    setIsProcessing(true);
    try {
      const res = await api.rollbackVersion(dataset.id, versionId, reason);
      showToast(res.message, 'success');
      await refreshDatasetDetails(dataset.id);
      setActiveTab('table');
    } catch (err: any) {
      showToast(err.message || 'Rollback failed', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Issue remediation helper
  const handleRemediateIssue = (issue: any) => {
    setIsAIAssistantOpen(true);
    if (issue.recommendation) {
      showToast(`Recommendation copied to AI Assistant: ${issue.recommendation}`, 'info');
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        datasetName={dataset?.original_filename}
        versionNumber={activeVersion?.version_number}
        onOpenUpload={() => setIsUploadModalOpen(true)}
        onToggleAIAssistant={() => setIsAIAssistantOpen(!isAIAssistantOpen)}
        isAIAssistantOpen={isAIAssistantOpen}
      />

      {/* Toast Notification */}
      {toast && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 60,
          background: toast.type === 'error' ? '#E11D48' : toast.type === 'success' ? '#059669' : '#4F46E5',
          color: '#FFFFFF',
          padding: '12px 20px',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-lg)',
          fontSize: '0.88rem',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }} className="animate-fade-in">
          <span>{toast.message}</span>
        </div>
      )}

      {/* Main Workspace Area */}
      <main className="app-container" style={{ flex: 1 }}>
        {!dataset && (
          <div style={{
            margin: '20px 0 16px 0',
            padding: '12px 18px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                No active dataset loaded. Browsing interface in preview mode.
              </span>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="btn-primary"
                style={{ padding: '6px 14px', fontSize: '0.82rem' }}
              >
                Upload File
              </button>
              <button
                onClick={handleLoadSample}
                className="btn-secondary"
                disabled={isProcessing}
                style={{ padding: '6px 14px', fontSize: '0.82rem' }}
              >
                Load Sample Data
              </button>
            </div>
          </div>
        )}

        <div style={{ marginTop: dataset ? '20px' : '4px' }}>
          {/* Tab: Data Table & Manual Transforms */}
          {activeTab === 'table' && (
            <>
              <TransformToolbar
                columns={previewData.columns}
                onApplyTransform={handleApplyTransform}
                onPreviewTransform={handlePreviewTransform}
                isProcessing={isProcessing}
              />
              <DataTable
                columns={previewData.columns}
                rows={previewData.rows}
                columnTypes={activeVersion?.schema_json}
                totalRows={previewData.total_rows}
                isLoading={isProcessing}
              />
            </>
          )}

          {/* Tab: Health & Profiling */}
          {activeTab === 'health' && (
            <HealthScorecard
              health={health}
              profile={profile}
              onRemediateIssue={handleRemediateIssue}
            />
          )}

          {/* Tab: Visualizations */}
          {activeTab === 'visualizations' && (
            <VisualizationsTab
              columns={previewData.columns}
              recommendations={visualizations?.recommended_charts || []}
              previews={visualizations?.previews || []}
              onRequestCustomChart={(req) => {
                if (!dataset) {
                  showToast('Please upload a dataset or load the sample data first.', 'info');
                  throw new Error('No dataset loaded.');
                }
                return api.requestVisualization(dataset.id, req);
              }}
            />
          )}

            {/* Tab: Executive Reports */}
            {activeTab === 'reports' && (
              <ReportsTab
                report={report}
                activeVersionNumber={activeVersion?.version_number}
                onGenerateReport={handleGenerateReport}
                onExportDataset={handleExportDataset}
                isGenerating={isGeneratingReport}
                isExporting={isProcessing}
              />
            )}

            {/* Tab: Version History & Audit */}
            {activeTab === 'history' && (
              <VersionHistoryDrawer
                versions={versions}
                timeline={timeline}
                activeVersionId={activeVersion?.id}
                onDiffVersions={handleDiffVersions}
                onRollbackVersion={handleRollbackVersion}
                isProcessing={isProcessing}
              />
            )}

            {/* Tab: ML Studio */}
            {activeTab === 'ml' && (
              <MLLabTab
                datasetId={dataset?.id}
                versions={versions}
                activeVersionNumber={activeVersion?.version_number}
                onLoadSample={handleLoadSample}
                onLoadMLBenchmark={handleLoadMLBenchmark}
                showToast={showToast}
              />
            )}
          </div>
        </main>

      {/* Slide-over AI Assistant */}
      <AIAssistantPanel
        isOpen={isAIAssistantOpen}
        onClose={() => setIsAIAssistantOpen(false)}
        onSubmitPrompt={handleSubmitAIPrompt}
        onApprovePlan={handleApproveAIPlan}
        isGeneratingPlan={isGeneratingAIPlan}
        isExecutingPlan={isProcessing}
      />

      {/* Ingestion Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
        onLoadSample={handleLoadSample}
        onLoadMLBenchmark={handleLoadMLBenchmark}
      />
    </div>
  );
}

export default App;


// ==============================================================================
// FILE SUMMARY: frontend/src/App.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This is the root React application orchestrator:
//   1. Manages top-level state: active dataset, sequential versions, health audit,
//      statistical profile, chart visualizations, executive reports, and audit timeline.
//   2. Coordinates navigation across 6 core views:
//      - 'table': Spreadsheet DataTable and TransformToolbar (15 deterministic operations).
//      - 'health': Radial 0-100 quality scorecard and remediation recommendations.
//      - 'visualizations': Smart chart recommendations and custom SVG chart builder.
//      - 'reports': Executive narrative reports and binary CSV/XLSX file downloads.
//      - 'history': Version lineage tree, semantic diff viewer, and safe rollback restore.
//      - 'ml': Machine Learning Impact Studio (model training, loss curve, overfitting diagnosis, cross-version benchmark).
//   3. Embeds the slide-over Conversational AI Assistant Drawer and Ingestion Upload Modal.
//   4. Provides instant Benchmark Sample loading for zero-setup demonstration.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Imports typed client methods from 'frontend/src/services/api.ts'.
// - Imports types from 'frontend/src/types/api.ts'.
// - Imports components from 'frontend/src/components/'.
// - Rendered into the DOM root via 'frontend/src/main.tsx'.
// ==============================================================================
