import React, { useState } from 'react';
import type { TransformImpactSummary } from '../types/api';

interface TransformToolbarProps {
  columns: string[];
  onApplyTransform: (operations: any[], summary: string) => Promise<void>;
  onPreviewTransform: (operations: any[]) => Promise<TransformImpactSummary | null>;
  isProcessing: boolean;
}

export const TransformToolbar: React.FC<TransformToolbarProps> = ({
  columns,
  onApplyTransform,
  onPreviewTransform,
  isProcessing
}) => {
  const [selectedOp, setSelectedOp] = useState<string>('fill_missing');
  const [targetColumn, setTargetColumn] = useState<string>(columns[0] || '');
  const [strategy, setStrategy] = useState<string>('mean');
  const [fillValue, setFillValue] = useState<string>('');
  const [targetType, setTargetType] = useState<string>('numeric');
  const [caseType, setCaseType] = useState<string>('lower');
  const [decimals, setDecimals] = useState<number>(2);
  const [datePart, setDatePart] = useState<string>('year');
  const [previewImpact, setPreviewImpact] = useState<TransformImpactSummary | null>(null);

  React.useEffect(() => {
    if (columns.length > 0 && (!targetColumn || !columns.includes(targetColumn))) {
      setTargetColumn(columns[0]);
    }
  }, [columns, targetColumn]);

  const buildCurrentOperation = () => {
    switch (selectedOp) {
      case 'fill_missing':
        return {
          type: 'fill_missing',
          column: targetColumn,
          strategy: strategy,
          value: fillValue,
          fill_value: fillValue
        };
      case 'drop_missing_rows':
        return {
          type: 'drop_missing_rows',
          column: targetColumn,
          columns: targetColumn ? [targetColumn] : undefined,
          how: 'any'
        };
      case 'remove_duplicates':
        return {
          type: 'remove_duplicates',
          keep: 'first'
        };
      case 'trim_text':
        return {
          type: 'trim_text',
          column: targetColumn,
          columns: [targetColumn]
        };
      case 'normalize_case':
        return {
          type: 'normalize_case',
          column: targetColumn,
          columns: [targetColumn],
          case: caseType,
          case_type: caseType
        };
      case 'convert_type':
        return {
          type: 'convert_type',
          column: targetColumn,
          target_type: targetType
        };
      case 'drop_columns':
        return {
          type: 'drop_columns',
          column: targetColumn,
          columns: [targetColumn]
        };
      case 'numeric_round':
        return {
          type: 'numeric_round',
          column: targetColumn,
          columns: [targetColumn],
          decimals: Number(decimals)
        };
      case 'handle_outliers':
        return {
          type: 'handle_outliers',
          column: targetColumn,
          action: 'clip',
          method: 'clip_iqr',
          factor: 1.5
        };
      case 'create_date_part':
        return {
          type: 'create_date_part',
          column: targetColumn,
          part: datePart,
          new_column_name: `${targetColumn}_${datePart}`,
          new_column: `${targetColumn}_${datePart}`
        };
      default:
        return null;
    }
  };

  const handlePreview = async () => {
    const op = buildCurrentOperation();
    if (!op) return;
    const impact = await onPreviewTransform([op]);
    setPreviewImpact(impact);
  };

  const handleApply = async () => {
    const op = buildCurrentOperation();
    if (!op) return;
    const summary = `Applied ${selectedOp.replace('_', ' ')} on ${targetColumn || 'dataset'}`;
    await onApplyTransform([op], summary);
    setPreviewImpact(null);
  };

  return (
    <div className="glass-panel" style={{ padding: '20px 24px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--brand-primary)" strokeWidth="2">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
          </svg>
          <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
            Deterministic Data Operations
          </span>
          <span className="badge badge-numeric" style={{ fontSize: '0.68rem' }}>
            15 Safe Handlers
          </span>
        </div>

        {previewImpact && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.8rem', background: 'rgba(99, 102, 241, 0.1)', padding: '4px 12px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
            <span>Preview: <strong>{previewImpact.rows_after}</strong> rows</span>
            <span>Modified: <strong>{previewImpact.cells_modified}</strong> cells</span>
            {previewImpact.rows_removed > 0 && <span style={{ color: 'var(--accent-rose)' }}>-{previewImpact.rows_removed} rows</span>}
          </div>
        )}
      </div>

      {/* Operation Selection Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        {/* Action Type */}
        <select
          value={selectedOp}
          onChange={(e) => {
            setSelectedOp(e.target.value);
            setPreviewImpact(null);
          }}
          style={{
            padding: '9px 12px',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--text-primary)',
            fontSize: '0.85rem',
            outline: 'none',
            fontWeight: 500
          }}
        >
          <optgroup label="Missing Values">
            <option value="fill_missing">Fill Missing Values</option>
            <option value="drop_missing_rows">Drop Missing Rows</option>
          </optgroup>
          <optgroup label="Data Hygiene">
            <option value="remove_duplicates">Remove Duplicate Rows</option>
            <option value="trim_text">Trim Whitespace</option>
            <option value="normalize_case">Normalize Text Case</option>
          </optgroup>
          <optgroup label="Schema Adjustments">
            <option value="convert_type">Convert Data Type</option>
            <option value="drop_columns">Drop Column</option>
          </optgroup>
          <optgroup label="Numeric & Outliers">
            <option value="numeric_round">Round Decimals</option>
            <option value="handle_outliers">Handle Outliers (IQR Clip)</option>
          </optgroup>
          <optgroup label="Date Extraction">
            <option value="create_date_part">Extract Date Part</option>
          </optgroup>
        </select>

        {/* Column Target */}
        {selectedOp !== 'remove_duplicates' && (
          <select
            value={targetColumn}
            onChange={(e) => {
              setTargetColumn(e.target.value);
              setPreviewImpact(null);
            }}
            style={{
              padding: '9px 12px',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              outline: 'none'
            }}
          >
            {columns.map(col => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
        )}

        {/* Dynamic Parameter: Fill Missing Strategy */}
        {selectedOp === 'fill_missing' && (
          <>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              style={{
                padding: '9px 12px',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-primary)',
                fontSize: '0.85rem'
              }}
            >
              <option value="mean">Mean (Average)</option>
              <option value="median">Median</option>
              <option value="mode">Mode (Most Frequent)</option>
              <option value="constant">Constant Value</option>
            </select>
            {strategy === 'constant' && (
              <input
                type="text"
                placeholder="Value..."
                value={fillValue}
                onChange={(e) => setFillValue(e.target.value)}
                style={{
                  padding: '9px 12px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem',
                  width: '110px'
                }}
              />
            )}
          </>
        )}

        {/* Dynamic Parameter: Convert Type */}
        {selectedOp === 'convert_type' && (
          <select
            value={targetType}
            onChange={(e) => setTargetType(e.target.value)}
            style={{
              padding: '9px 12px',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem'
            }}
          >
            <option value="numeric">Numeric (Float/Int)</option>
            <option value="text">Text / String</option>
            <option value="datetime">Datetime</option>
            <option value="boolean">Boolean</option>
            <option value="categorical">Categorical</option>
          </select>
        )}

        {/* Dynamic Parameter: Normalize Case */}
        {selectedOp === 'normalize_case' && (
          <select
            value={caseType}
            onChange={(e) => setCaseType(e.target.value)}
            style={{
              padding: '9px 12px',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem'
            }}
          >
            <option value="lower">lowercase</option>
            <option value="upper">UPPERCASE</option>
            <option value="title">Title Case</option>
          </select>
        )}

        {/* Dynamic Parameter: Numeric Round */}
        {selectedOp === 'numeric_round' && (
          <input
            type="number"
            min="0"
            max="6"
            value={decimals}
            onChange={(e) => setDecimals(Number(e.target.value))}
            style={{
              padding: '9px 12px',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              width: '80px'
            }}
          />
        )}

        {/* Dynamic Parameter: Date Part */}
        {selectedOp === 'create_date_part' && (
          <select
            value={datePart}
            onChange={(e) => setDatePart(e.target.value)}
            style={{
              padding: '9px 12px',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem'
            }}
          >
            <option value="year">Year</option>
            <option value="month">Month</option>
            <option value="day">Day</option>
            <option value="dayofweek">Day of Week</option>
            <option value="hour">Hour</option>
          </select>
        )}

        {/* Execution Buttons */}
        <div style={{ display: 'flex', gap: '8px', marginLeft: 'auto' }}>
          <button
            type="button"
            onClick={handlePreview}
            disabled={isProcessing}
            className="btn-secondary"
            style={{ padding: '8px 14px', fontSize: '0.82rem' }}
          >
            Preview Impact
          </button>
          <button
            type="button"
            onClick={handleApply}
            disabled={isProcessing}
            className="btn-primary"
            style={{ padding: '8px 16px', fontSize: '0.82rem' }}
          >
            {isProcessing ? 'Executing...' : 'Apply & Version'}
          </button>
        </div>
      </div>

      {/* Expanded Preview Impact Panel */}
      {previewImpact && (
        <div style={{
          marginTop: '16px',
          padding: '12px 18px',
          background: 'rgba(37, 99, 235, 0.08)',
          border: '1px solid rgba(37, 99, 235, 0.3)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }} className="animate-fade-in">
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              🔍 Preview Result:
            </span>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Rows: <strong>{previewImpact.rows_before}</strong> → <strong>{previewImpact.rows_after}</strong>
            </span>
            <span style={{ fontSize: '0.82rem', color: previewImpact.cells_modified > 0 ? '#38BDF8' : 'var(--text-muted)' }}>
              Cells Modified: <strong>{previewImpact.cells_modified}</strong>
            </span>
            {previewImpact.rows_removed > 0 && (
              <span style={{ fontSize: '0.82rem', color: '#FB7185' }}>
                Rows Removed: <strong>{previewImpact.rows_removed}</strong>
              </span>
            )}
            {previewImpact.affected_columns.length > 0 && (
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Target: <strong>[{previewImpact.affected_columns.join(', ')}]</strong>
              </span>
            )}
            <span style={{ fontSize: '0.78rem', color: previewImpact.cells_modified > 0 ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>
              {previewImpact.cells_modified > 0
                ? `Ready to transform ${previewImpact.cells_modified} cell(s)`
                : `0 cells modified — column is already clean`}
            </span>
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              type="button"
              onClick={handleApply}
              disabled={isProcessing}
              className="btn-primary"
              style={{ padding: '5px 12px', fontSize: '0.78rem' }}
            >
              Apply Change
            </button>
            <button
              type="button"
              onClick={() => setPreviewImpact(null)}
              className="btn-secondary"
              style={{ padding: '5px 10px', fontSize: '0.78rem' }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
};


// ==============================================================================
// FILE SUMMARY: frontend/src/components/TransformToolbar.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This component provides the Spreadsheet-like Transformation & Cleaning Control Panel:
//   1. Exposes manual controls for the platform's 15 safe deterministic operations:
//      - Missing values: fill_missing (mean, median, mode, constant), drop_missing_rows.
//      - Data hygiene: remove_duplicates, trim_text, normalize_case.
//      - Schema modifications: convert_type, drop_columns.
//      - Numeric & Outliers: numeric_round, handle_outliers (IQR method).
//      - Temporal features: create_date_part.
//   2. Implements a safe 'Preview Impact' workflow showing expected row/cell modifications
//      before committing changes.
//   3. Commits approved operations, creating a new immutable DatasetVersion snapshot (vNext).
//
// HOW IT CONNECTS TO OTHER FILES:
// - Mounted above the DataTable in 'frontend/src/App.tsx'.
// - Invokes 'api.previewTransform' and 'api.applyTransform' in 'frontend/src/services/api.ts'.
// ==============================================================================
