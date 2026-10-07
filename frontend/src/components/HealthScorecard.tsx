import React from 'react';
import type { DatasetHealth, DatasetProfile } from '../types/api';

interface HealthScorecardProps {
  health: DatasetHealth | null;
  profile: DatasetProfile | null;
  onRemediateIssue?: (issue: any) => void;
}

export const HealthScorecard: React.FC<HealthScorecardProps> = ({
  health,
  profile,
  onRemediateIssue
}) => {
  const isLoaded = Boolean(health && profile);
  const score = health?.health_score ?? 0;
  const ratingColor = !isLoaded ? '#64748B' :
    score >= 90 ? '#10B981' :
    score >= 75 ? '#06B6D4' :
    score >= 60 ? '#F59E0B' : '#F43F5E';

  return (
    <div className="animate-fade-in" style={{ padding: '24px 0' }}>
      {/* Top Health Overview Hero */}
      <div className="glass-panel health-hero-panel">
        {/* Radial Score Gauge */}
        <div style={{ position: 'relative', width: '140px', height: '140px' }}>
          <svg width="140" height="140" viewBox="0 0 140 140" style={{ transform: 'rotate(-90deg)' }}>
            <circle
              cx="70"
              cy="70"
              r="58"
              fill="none"
              stroke="rgba(255, 255, 255, 0.08)"
              strokeWidth="12"
            />
            <circle
              cx="70"
              cy="70"
              r="58"
              fill="none"
              stroke={ratingColor}
              strokeWidth="12"
              strokeDasharray={364.4}
              strokeDashoffset={isLoaded ? 364.4 - (364.4 * score) / 100 : 364.4}
              strokeLinecap="round"
              style={{ transition: 'stroke-dashoffset 1s ease-out' }}
            />
          </svg>
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <span style={{ fontSize: '2.4rem', fontWeight: 800, color: '#FFFFFF', lineHeight: 1 }}>
              {isLoaded ? score : '--'}
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginTop: '4px' }}>
              / 100
            </span>
          </div>
        </div>

        {/* Narrative & Rating */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Dataset Health Scorecard
            </h1>
            <span className={`badge badge-${health?.rating || 'fair'}`} style={{ fontSize: '0.8rem', padding: '4px 10px' }}>
              {isLoaded ? `${health?.rating} Quality` : 'Preview Mode'}
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', maxWidth: '640px', lineHeight: 1.5 }}>
            {isLoaded ? (
              score >= 90
                ? 'This dataset is clean with minimal missing values, consistent schemas, and no severe distribution anomalies.'
                : score >= 75
                ? 'Good overall quality with a few hygiene warnings or missing values to address.'
                : score >= 60
                ? 'Moderate data hygiene risks detected. Recommended cleaning operations include filling missing values, deduplication, and outlier trimming.'
                : 'Severe quality issues detected. Review the remediation steps below.'
            ) : (
              'Upload a dataset or load the benchmark sample to run automated profiling, missingness calculation, duplicate detection, and health scoring.'
            )}
          </p>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '16px',
        marginBottom: '28px'
      }}>
        {[
          { 
            label: 'Total Rows', 
            val: profile ? (profile.row_count ?? 0).toLocaleString() : '--' 
          },
          { 
            label: 'Total Columns', 
            val: profile ? (profile.column_count ?? 0).toString() : '--' 
          },
          { 
            label: 'Missing Values', 
            val: profile ? `${(profile.null_percentage ?? 0).toFixed(1)}%` : '--', 
            sub: profile 
              ? `${(profile.total_nulls ?? (profile as any).total_null_cells ?? 0).toLocaleString()} cells` 
              : 'No data' 
          },
          { 
            label: 'Duplicate Rows', 
            val: profile ? `${(profile.duplicate_percentage ?? 0).toFixed(1)}%` : '--', 
            sub: profile 
              ? `${(profile.duplicate_rows ?? 0).toLocaleString()} rows` 
              : 'No data' 
          },
          { 
            label: 'Memory Footprint', 
            val: profile 
              ? `${(((profile.memory_bytes ?? (profile as any).estimated_memory_bytes ?? 0) / 1024)).toFixed(1)} KB` 
              : '--' 
          },
          { 
            label: 'Candidate Keys', 
            val: profile && Array.isArray(profile.candidate_keys) && profile.candidate_keys.length > 0 
              ? profile.candidate_keys.join(', ') 
              : '--' 
          }
        ].map((kpi, idx) => (
          <div key={idx} className="glass-panel" style={{ padding: '16px 18px' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.5px' }}>
              {kpi.label}
            </span>
            <div style={{ fontSize: '1.3rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
              {kpi.val}
            </div>
            {kpi.sub && (
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {kpi.sub}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Issues & Remediation List */}
      {(() => {
        const issues = Array.isArray(health?.issues) ? health.issues : [];

        return (
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                  Detected Issues & Actionable Recommendations
                </h2>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                  {isLoaded ? `Found ${health?.total_issues ?? issues.length} diagnostic check(s) requiring attention` : 'Auditing checks run automatically upon dataset load'}
                </p>
              </div>
            </div>

            {!health ? (
              <div style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                <p>No dataset loaded yet. Load data to view diagnostic quality checks.</p>
              </div>
            ) : issues.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '36px', color: 'var(--accent-emerald)' }}>
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ margin: '0 auto 12px auto' }}>
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <p style={{ fontWeight: 600 }}>No critical or warning quality issues detected!</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {issues.map((issue, idx) => {
                  const isCrit = issue.level === 'critical';
                  const isWarn = issue.level === 'warning';
                  const borderCol = isCrit ? 'rgba(244, 63, 94, 0.4)' : isWarn ? 'rgba(245, 158, 11, 0.4)' : 'rgba(6, 182, 212, 0.4)';
                  const badgeBg = isCrit ? 'rgba(244, 63, 94, 0.15)' : isWarn ? 'rgba(245, 158, 11, 0.15)' : 'rgba(6, 182, 212, 0.15)';
                  const textCol = isCrit ? '#FB7185' : isWarn ? '#FBBF24' : '#38BDF8';

                  return (
                    <div
                      key={idx}
                      style={{
                        background: 'rgba(17, 24, 39, 0.6)',
                        border: `1px solid ${borderCol}`,
                        borderRadius: 'var(--radius-md)',
                        padding: '16px 20px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '16px'
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                          <span style={{
                            background: badgeBg,
                            color: textCol,
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: 'var(--radius-sm)',
                            textTransform: 'uppercase'
                          }}>
                            {issue.level || 'info'}
                          </span>
                          {issue.column && (
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                              [{issue.column}]
                            </span>
                          )}
                          <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
                            {issue.message || 'Data quality check'}
                          </span>
                        </div>
                        {issue.recommendation && (
                          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            <strong style={{ color: 'var(--text-muted)' }}>Recommendation: </strong>
                            {issue.recommendation}
                          </p>
                        )}
                      </div>

                      {onRemediateIssue && (
                        <button
                          onClick={() => onRemediateIssue(issue)}
                          className="btn-secondary"
                          style={{
                            padding: '8px 14px',
                            fontSize: '0.8rem',
                            whiteSpace: 'nowrap',
                            borderColor: borderCol
                          }}
                        >
                          Remediate
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
};


// ==============================================================================
// FILE SUMMARY: frontend/src/components/HealthScorecard.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This component provides the Interactive Data Health & Quality Evaluation View:
//   1. Dynamic radial gauge displaying the 0-100 heuristic health score with status coloring.
//   2. Overall quality narrative and health rating badge ('excellent', 'good', 'fair', 'poor').
//   3. Summary KPI grid displaying Row Count, Columns, Missingness %, Duplicate %, and Memory.
//   4. Diagnostic issues list with severity badges ('critical', 'warning', 'info'), affected
//      columns, and actionable remediation recommendations.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Rendered in 'frontend/src/App.tsx' when the user selects the 'Health Score' tab.
// - Receives 'DatasetHealth' and 'DatasetProfile' objects populated via 'api.getDatasetHealth'.
// ==============================================================================
