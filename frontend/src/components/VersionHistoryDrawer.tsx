import React, { useState, useEffect } from 'react';
import type { DatasetVersion, VersionDiffResponse, AuditTimelineResponse } from '../types/api';

interface VersionHistoryDrawerProps {
  versions: DatasetVersion[];
  timeline: AuditTimelineResponse | null;
  activeVersionId?: string;
  onDiffVersions: (sourceVersionId: string, targetVersionId?: string) => Promise<VersionDiffResponse>;
  onRollbackVersion: (versionId: string, reason?: string) => Promise<void>;
  isProcessing: boolean;
}

export const VersionHistoryDrawer: React.FC<VersionHistoryDrawerProps> = ({
  versions,
  timeline,
  activeVersionId,
  onDiffVersions,
  onRollbackVersion,
  isProcessing
}) => {
  const [selectedVersionId, setSelectedVersionId] = useState<string>(activeVersionId || versions[versions.length - 1]?.id || '');
  const [diffResult, setDiffResult] = useState<VersionDiffResponse | null>(null);
  const [isDiffing, setIsDiffing] = useState(false);

  // Sync selectedVersionId when activeVersionId or versions change
  useEffect(() => {
    const targetId = activeVersionId || versions[versions.length - 1]?.id || '';
    if (targetId) {
      setSelectedVersionId(targetId);
      handleInspectDiff(targetId);
    }
  }, [activeVersionId, versions.length]);

  const handleInspectDiff = async (vId: string) => {
    try {
      setIsDiffing(true);
      setSelectedVersionId(vId);
      const res = await onDiffVersions(vId);
      setDiffResult(res);
    } catch (err) {
      console.error("Diff computation error:", err);
    } finally {
      setIsDiffing(false);
    }
  };

  const handleRollback = async (vId: string, verNum?: number) => {
    const numLabel = verNum !== undefined ? `Version ${verNum}` : 'this version';
    if (!window.confirm(`Are you sure you want to restore the dataset to ${numLabel}? This will restore all rows and columns from that snapshot as the new active version.`)) {
      return;
    }
    await onRollbackVersion(vId, `Restored to ${numLabel}`);
    setDiffResult(null);
  };

  const selectedVersion = versions.find(v => v.id === selectedVersionId);
  const isSelectedActive = selectedVersionId === activeVersionId;

  return (
    <div className="animate-fade-in" style={{ padding: '24px 0' }}>
      <div className="history-grid" style={{ gap: '24px' }}>
        {/* Left: Versions Lineage Tree */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              Dataset Versions ({versions.length})
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Click card to inspect diff
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Show versions in reverse chronological order (newest first) */}
            {[...versions].reverse().map((ver) => {
              const isCurrent = ver.id === activeVersionId;
              const isSelected = ver.id === selectedVersionId;

              return (
                <div
                  key={ver.id}
                  onClick={() => handleInspectDiff(ver.id)}
                  style={{
                    padding: '14px',
                    borderRadius: 'var(--radius-md)',
                    background: isSelected ? 'rgba(37, 99, 235, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                    border: `1px solid ${isSelected ? '#2563EB' : 'var(--border-subtle)'}`,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="badge badge-numeric" style={{ fontSize: '0.78rem', fontWeight: 700 }}>
                        Version {ver.version_number}
                      </span>
                      {isCurrent ? (
                        <span style={{ fontSize: '0.68rem', background: '#059669', color: '#ffffff', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
                          ACTIVE
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                          Snapshot
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {ver.row_count} rows • {ver.column_count} cols
                    </span>
                  </div>

                  <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', margin: '4px 0' }}>
                    SHA: {ver.checksum.slice(0, 12)}...
                  </p>
                  <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', margin: '2px 0 6px 0' }}>
                    {new Date(ver.created_at).toLocaleString()}
                  </p>

                  {/* Explicit Rollback action per version card */}
                  {!isCurrent ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRollback(ver.id, ver.version_number);
                      }}
                      disabled={isProcessing}
                      className="btn-secondary"
                      style={{
                        width: '100%',
                        marginTop: '8px',
                        padding: '6px 12px',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        color: '#d97706',
                        borderColor: '#d97706',
                        background: 'rgba(217, 119, 6, 0.08)'
                      }}
                    >
                      {isProcessing ? 'Restoring...' : `Rollback to Version ${ver.version_number}`}
                    </button>
                  ) : (
                    <div style={{ marginTop: '8px', padding: '5px 8px', fontSize: '0.72rem', color: 'var(--accent-emerald)', background: 'rgba(5, 150, 105, 0.08)', borderRadius: '4px', textAlign: 'center', fontWeight: 600 }}>
                      Current active dataset state
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Version Diff & Rollback Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Diff Viewer Card */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                  Semantic Version Comparison {selectedVersion ? `(v${selectedVersion.version_number})` : ''}
                </h3>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Structural changes relative to parent version
                </p>
              </div>

              {selectedVersionId && (
                isSelectedActive ? (
                  <button
                    disabled
                    className="btn-secondary"
                    style={{ opacity: 0.6, cursor: 'not-allowed', fontSize: '0.82rem' }}
                  >
                    Active Version (Current State)
                  </button>
                ) : (
                  <button
                    onClick={() => handleRollback(selectedVersionId, selectedVersion?.version_number)}
                    disabled={isProcessing}
                    className="btn-secondary"
                    style={{ borderColor: '#d97706', color: '#d97706', background: 'rgba(217, 119, 6, 0.1)', fontSize: '0.82rem', fontWeight: 600 }}
                  >
                    {isProcessing ? 'Restoring...' : `Rollback to Version ${selectedVersion?.version_number || ''}`}
                  </button>
                )
              )}
            </div>

            {isDiffing ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#2563EB' }}>
                Comparing schema snapshots...
              </div>
            ) : !diffResult ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                Select a version on the left to inspect its diff with predecessor.
              </div>
            ) : (
              <div>
                {/* Summary Banner */}
                <div style={{ padding: '14px 18px', background: 'rgba(37, 99, 235, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(37, 99, 235, 0.25)', marginBottom: '20px' }}>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', lineHeight: 1.5, margin: 0 }}>
                    {diffResult.summary}
                  </p>
                </div>

                {/* Metrics Comparison Pills */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 130px), 1fr))', gap: '12px', marginBottom: '20px' }}>
                  <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Row Shift</span>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: diffResult.rows_diff < 0 ? 'var(--accent-rose)' : 'var(--text-primary)' }}>
                      {diffResult.rows_diff > 0 ? `+${diffResult.rows_diff}` : diffResult.rows_diff}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Columns Added</span>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
                      +{diffResult.added_columns.length}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Columns Dropped</span>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-rose)' }}>
                      -{diffResult.removed_columns.length}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Type Conversions</span>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#2563EB' }}>
                      {diffResult.type_changed_columns.length}
                    </div>
                  </div>
                </div>

                {/* Column Level Changes Table */}
                <div style={{ overflowX: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
                    <thead>
                      <tr style={{ background: 'rgba(15, 23, 42, 0.8)', borderBottom: '1px solid var(--border-subtle)' }}>
                        <th style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>Column</th>
                        <th style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>Change Type</th>
                        <th style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>Data Type Transition</th>
                        <th style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>Null Delta</th>
                      </tr>
                    </thead>
                    <tbody>
                      {diffResult.column_changes.map((c, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                          <td style={{ padding: '8px 14px', fontWeight: 600, color: 'var(--text-primary)' }}>{c.column}</td>
                          <td style={{ padding: '8px 14px' }}>
                            <span className={`badge badge-${c.change_type === 'added' ? 'categorical' : c.change_type === 'removed' ? 'poor' : 'numeric'}`}>
                              {c.change_type}
                            </span>
                          </td>
                          <td style={{ padding: '8px 14px', color: 'var(--text-secondary)' }}>
                            {c.source_type && c.target_type && c.source_type !== c.target_type ? `${c.source_type} ➔ ${c.target_type}` : c.target_type || c.source_type || '—'}
                          </td>
                          <td style={{ padding: '8px 14px', color: (c.null_delta || 0) < 0 ? 'var(--accent-emerald)' : 'var(--text-secondary)' }}>
                            {c.null_delta !== undefined && c.null_delta !== 0 ? (c.null_delta > 0 ? `+${c.null_delta}` : c.null_delta) : '0'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Audit Timeline Card */}
          {timeline && (
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '14px', color: 'var(--text-primary)' }}>
                Chronological Audit Trail ({timeline.total_events} Events)
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {timeline.events.map((evt) => (
                  <div
                    key={evt.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      background: 'rgba(255, 255, 255, 0.02)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.82rem'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span className={`badge badge-${evt.source === 'ai' ? 'boolean' : evt.source === 'rollback' ? 'datetime' : 'numeric'}`}>
                        {evt.event_type}
                      </span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{evt.summary}</span>
                    </div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {new Date(evt.timestamp).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};


// ==============================================================================
// FILE SUMMARY: frontend/src/components/VersionHistoryDrawer.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This component provides the Dataset Lineage, Diff Viewer, and Rollback Hub:
//   1. Displays the sequential, immutable version tree (v1, v2, v3, ...) with checksums.
//   2. Interactive semantic diff viewer identifying row count deltas, added/removed columns,
//      type conversions, and null value reductions.
//   3. Safe one-click rollback trigger restoring the dataset state to a previous snapshot
//      by committing a new active version (vNext).
//   4. Comprehensive chronological audit timeline listing all operations and initiators.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Rendered in 'frontend/src/App.tsx' under the 'Audit History' tab.
// - Interacts with 'api.diffVersions', 'api.rollbackVersion', and 'api.getTimeline'.
// ==============================================================================
