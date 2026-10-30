import React, { useState } from 'react';
import type { ReportResponse } from '../types/api';

interface ReportsTabProps {
  report: ReportResponse | null;
  activeVersionNumber?: number;
  onGenerateReport: (format: 'markdown' | 'html' | 'json', title?: string) => Promise<void>;
  onExportDataset: (format: 'csv' | 'xlsx') => Promise<void>;
  isGenerating: boolean;
  isExporting: boolean;
}

export const ReportsTab: React.FC<ReportsTabProps> = ({
  report,
  activeVersionNumber,
  onGenerateReport,
  onExportDataset,
  isGenerating,
  isExporting
}) => {
  const [selectedFormat, setSelectedFormat] = useState<'markdown' | 'html' | 'json'>('markdown');
  const isOutdated = Boolean(report && activeVersionNumber && report.version_number !== activeVersionNumber);

  return (
    <div className="animate-fade-in" style={{ padding: '24px 0' }}>
      {/* Action Header & Format Controls */}
      <div className="glass-panel" style={{ padding: '20px 24px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              Executive Narrative Reports & File Exports
            </h2>
            {activeVersionNumber && (
              <span className="badge badge-numeric" title="Active preprocessed dataset version">
                Active: v{activeVersionNumber}
              </span>
            )}
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px', marginBottom: 0 }}>
            Synthesized analytical findings, health audits, and downloadable dataset versions
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Format Picker */}
          <div style={{ display: 'flex', background: 'rgba(30, 41, 59, 0.6)', padding: '3px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            {(['markdown', 'html', 'json'] as const).map(fmt => (
              <button
                key={fmt}
                onClick={() => {
                  setSelectedFormat(fmt);
                  onGenerateReport(fmt);
                }}
                disabled={isGenerating}
                style={{
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  border: 'none',
                  cursor: isGenerating ? 'not-allowed' : 'pointer',
                  background: selectedFormat === fmt ? 'var(--brand-primary)' : 'transparent',
                  color: selectedFormat === fmt ? '#FFFFFF' : 'var(--text-muted)'
                }}
              >
                {fmt}
              </button>
            ))}
          </div>

          {/* Quick Refresh / Regenerate Button */}
          <button
            onClick={() => onGenerateReport(selectedFormat)}
            disabled={isGenerating}
            className="btn-primary"
            style={{
              padding: '7px 14px',
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
            title="Compile a fresh executive report for current dataset"
          >
            <svg
              className={isGenerating ? "animate-spin" : ""}
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            {isGenerating ? 'Compiling...' : 'Refresh Report'}
          </button>

          {/* Export Dataset Buttons */}
          <button
            onClick={() => onExportDataset('csv')}
            disabled={isExporting}
            className="btn-secondary"
            style={{ padding: '8px 14px', fontSize: '0.82rem' }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export CSV
          </button>

          <button
            onClick={() => onExportDataset('xlsx')}
            disabled={isExporting}
            className="btn-secondary"
            style={{ padding: '8px 14px', fontSize: '0.82rem' }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export Excel (.xlsx)
          </button>
        </div>
      </div>

      {/* Outdated Version Notice */}
      {isOutdated && (
        <div style={{
          padding: '14px 20px',
          background: 'rgba(234, 179, 8, 0.1)',
          border: '1px solid rgba(234, 179, 8, 0.45)',
          borderRadius: 'var(--radius-md)',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '1.3rem' }}>⚠️</span>
            <div>
              <div style={{ fontWeight: 700, color: '#FACC15', fontSize: '0.9rem' }}>
                Dataset Preprocessed: Active Version is v{activeVersionNumber} (Report is v{report?.version_number})
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                New preprocessing transformations were applied to this dataset. Compile an updated report to reflect fresh metrics and health audits.
              </div>
            </div>
          </div>
          <button
            onClick={() => onGenerateReport(selectedFormat)}
            disabled={isGenerating}
            className="btn-primary"
            style={{ padding: '8px 16px', fontSize: '0.82rem', whiteSpace: 'nowrap' }}
          >
            {isGenerating ? 'Compiling v' + activeVersionNumber + '...' : `Update Report to v${activeVersionNumber}`}
          </button>
        </div>
      )}

      {isGenerating ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '60px', color: 'var(--accent-cyan)' }}>
          <svg className="animate-pulse-subtle" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ margin: '0 auto 12px auto' }}>
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          <p style={{ fontWeight: 600 }}>
            Synthesizing multi-format executive insights {activeVersionNumber ? `for Version ${activeVersionNumber}` : ''}...
          </p>
        </div>
      ) : !report ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '60px 24px', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '10px' }}>📊</div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
            No Executive Report Loaded
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '440px', margin: '0 auto 20px auto' }}>
            Compile an executive analytical report {activeVersionNumber ? `for Version ${activeVersionNumber}` : ''} synthesizing data health, statistical summaries, and observations.
          </p>
          <button
            onClick={() => onGenerateReport(selectedFormat)}
            className="btn-primary"
            style={{ padding: '10px 20px', fontSize: '0.88rem' }}
          >
            Compile Executive Report
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Executive Summary Card */}
          <div className="glass-panel" style={{ padding: '28px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {report.title}
              </h3>
              <div style={{ display: 'flex', gap: '8px' }}>
                <span className="badge badge-numeric">Version {report.version_number}</span>
                <span className="badge badge-excellent">Health: {report.health_score}/100</span>
              </div>
            </div>
            <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-line' }}>
              {report.executive_summary}
            </p>
          </div>

          {/* Categorized Insights Grid */}
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '16px', color: 'var(--text-primary)' }}>
              Synthesized Findings & Observations ({report.insights.length})
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: '16px' }}>
              {report.insights.map((item, idx) => {
                const badgeColor =
                  item.category === 'risk' ? '#F43F5E' :
                  item.category === 'correlation' ? '#8B5CF6' :
                  item.category === 'trend' ? '#06B6D4' :
                  item.category === 'distribution' ? '#10B981' : '#6366F1';

                return (
                  <div key={idx} className="glass-panel" style={{ padding: '20px', borderLeft: `3px solid ${badgeColor}` }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span style={{ fontSize: '0.7rem', fontWeight: 700, color: badgeColor, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        {item.category}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        Confidence: {item.confidence}
                      </span>
                    </div>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                      {item.title}
                    </h4>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px', lineHeight: 1.4 }}>
                      {item.observation}
                    </p>
                    {item.implication && (
                      <p style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)', background: 'rgba(6, 182, 212, 0.08)', padding: '6px 10px', borderRadius: 'var(--radius-sm)' }}>
                        💡 <strong>Analytical Implication: </strong>{item.implication}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Formatted Content Preview */}
          {report.content && (
            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  {report.format.toUpperCase()} Document Source Preview
                </span>
              </div>
              <pre style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)',
                background: '#0B0F19',
                padding: '16px',
                borderRadius: 'var(--radius-md)',
                overflowX: 'auto',
                maxHeight: '340px'
              }}>
                {report.content}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};


// ==============================================================================
// FILE SUMMARY: frontend/src/components/ReportsTab.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This component provides the Executive Report & Data Download Hub:
//   1. Displays the generated narrative executive summary and health KPI badges.
//   2. Presents categorized insight cards (quality, correlation, distribution, trend, risk)
//      with non-causal statistical interpretations and analytical implications.
//   3. Supports multi-format report previews across Markdown, HTML, and JSON.
//   4. Provides instant binary download actions for CSV and Excel (.xlsx) dataset exports.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Rendered in 'frontend/src/App.tsx' under the 'Executive Report' tab.
// - Triggers report generation via 'api.generateReport' and file downloads via 'api.exportDataset'.
// ==============================================================================
