import React, { useState, useMemo } from 'react';
import type { ColumnType } from '../types/api';

interface DataTableProps {
  columns: string[];
  rows: Record<string, any>[];
  columnTypes?: Record<string, ColumnType | string>;
  totalRows?: number;
  isLoading?: boolean;
}

export const DataTable: React.FC<DataTableProps> = ({
  columns,
  rows,
  columnTypes = {},
  totalRows = rows.length,
  isLoading = false
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Filter rows
  const filteredRows = useMemo(() => {
    if (!searchTerm.trim()) return rows;
    const term = searchTerm.toLowerCase();
    return rows.filter(row =>
      columns.some(col => {
        const val = row[col];
        return val !== null && val !== undefined && String(val).toLowerCase().includes(term);
      })
    );
  }, [rows, columns, searchTerm]);

  // Sort rows
  const sortedRows = useMemo(() => {
    if (!sortCol) return filteredRows;
    return [...filteredRows].sort((a, b) => {
      const valA = a[sortCol];
      const valB = b[sortCol];
      if (valA === valB) return 0;
      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortDirection === 'asc' ? valA - valB : valB - valA;
      }
      return sortDirection === 'asc'
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA));
    });
  }, [filteredRows, sortCol, sortDirection]);

  // Paginate
  const totalPages = Math.max(1, Math.ceil(sortedRows.length / pageSize));
  const paginatedRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedRows.slice(start, start + pageSize);
  }, [sortedRows, page, pageSize]);

  const handleSort = (col: string) => {
    if (sortCol === col) {
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else {
        setSortCol(null);
      }
    } else {
      setSortCol(col);
      setSortDirection('asc');
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginTop: '20px' }}>
      {/* Search & Meta Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', gap: '16px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', width: '320px' }}>
          <input
            type="text"
            placeholder="Search all cells..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(1);
            }}
            style={{
              width: '100%',
              padding: '9px 14px 9px 36px',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              outline: 'none'
            }}
          />
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-muted)"
            strokeWidth="2"
            style={{ position: 'absolute', left: '12px', top: '10px' }}
          >
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          <span>
            Showing <strong>{sortedRows.length}</strong> of <strong>{totalRows}</strong> records
          </span>
          {sortCol && (
            <span style={{ background: 'rgba(99, 102, 241, 0.15)', color: 'var(--brand-primary)', padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem' }}>
              Sorted by: {sortCol} ({sortDirection})
            </span>
          )}
        </div>
      </div>

      {/* Table Container */}
      <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ background: 'rgba(15, 23, 42, 0.8)', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '12px 16px', width: '50px', color: 'var(--text-muted)', fontWeight: 600 }}>#</th>
              {columns.map((col) => {
                const colType = columnTypes[col] || 'text';
                const isSorted = sortCol === col;
                return (
                  <th
                    key={col}
                    onClick={() => handleSort(col)}
                    style={{
                      padding: '12px 16px',
                      cursor: 'pointer',
                      userSelect: 'none',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{col}</span>
                      <span className={`badge badge-${colType}`} style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                        {colType}
                      </span>
                      {isSorted && (
                        <span style={{ color: 'var(--brand-primary)', fontSize: '0.8rem' }}>
                          {sortDirection === 'asc' ? '▲' : '▼'}
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={columns.length + 1} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  Loading table data...
                </td>
              </tr>
            ) : paginatedRows.length === 0 ? (
              <tr>
                <td colSpan={Math.max(1, columns.length + 1)} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  {columns.length === 0
                    ? 'No dataset loaded yet. Load sample data or upload a CSV/Excel file to inspect records.'
                    : 'No matching records found.'}
                </td>
              </tr>
            ) : (
              paginatedRows.map((row, rIdx) => {
                const absoluteIdx = (page - 1) * pageSize + rIdx + 1;
                return (
                  <tr
                    key={rIdx}
                    style={{
                      borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                      background: rIdx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.015)',
                      transition: 'background 0.15s ease'
                    }}
                  >
                    <td style={{ padding: '10px 16px', color: 'var(--text-muted)', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
                      {absoluteIdx}
                    </td>
                    {columns.map((col) => {
                      const val = row[col];
                      const isNull = val === null || val === undefined || val === '';
                      return (
                        <td
                          key={col}
                          style={{
                            padding: '10px 16px',
                            color: isNull ? 'rgba(244, 63, 94, 0.6)' : 'var(--text-primary)',
                            fontStyle: isNull ? 'italic' : 'normal',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {isNull ? '<null>' : typeof val === 'number' ? val.toLocaleString() : String(val)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Page {page} of {totalPages}
        </span>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.8rem' }}
          >
            Previous
          </button>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.8rem' }}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};


// ==============================================================================
// FILE SUMMARY: frontend/src/components/DataTable.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This component provides the Spreadsheet-style Tabular Data Viewer:
//   1. Renders tabular data with column header type badges (numeric, categorical, datetime).
//   2. Implements real-time text search filtering across all table cells.
//   3. Supports interactive column sorting (ascending, descending) for numbers and strings.
//   4. Provides client-side pagination with row index counting.
//   5. Highlights missing/null cells with distinct italic styling.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Rendered in 'frontend/src/App.tsx' under the 'Data Table' tab.
// - Receives rows and columns fetched via 'api.getDatasetPreview'.
// ==============================================================================
