import React from 'react';

interface NavbarProps {
  activeTab: 'table' | 'health' | 'visualizations' | 'reports' | 'history' | 'ml';
  setActiveTab: (tab: 'table' | 'health' | 'visualizations' | 'reports' | 'history' | 'ml') => void;
  datasetName?: string;
  versionNumber?: number;
  onOpenUpload: () => void;
  onToggleAIAssistant: () => void;
  isAIAssistantOpen: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  datasetName,
  versionNumber = 1,
  onOpenUpload,
  onToggleAIAssistant,
  isAIAssistantOpen
}) => {
  return (
    <header className="navbar-header">
      {/* Brand & Dataset Info */}
      <div className="navbar-brand-section">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--brand-primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
              <line x1="12" y1="22.08" x2="12" y2="12" />
            </svg>
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '1rem', letterSpacing: '-0.2px', color: '#FFFFFF' }}>
              Data Analyst
            </div>
            <div className="brand-subtitle" style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px', fontWeight: 500 }}>
              Analytics Workspace
            </div>
          </div>
        </div>

        {datasetName && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingLeft: '16px', borderLeft: '1px solid var(--border-subtle)' }}>
            <span className="dataset-name-text" style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {datasetName}
            </span>
            <span className="badge badge-numeric" style={{ fontSize: '0.7rem' }}>
              v{versionNumber}
            </span>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <nav className="navbar-tabs-container">
        {[
          { id: 'table', label: 'Data Table', icon: 'M3 3h18v18H3z M3 9h18 M9 21V9' },
          { id: 'health', label: 'Health Score', icon: 'M22 12h-4l-3 9L9 3l-3 9H2' },
          { id: 'visualizations', label: 'Visualizations', icon: 'M18 20V10 M12 20V4 M6 20v-6' },
          { id: 'reports', label: 'Executive Report', icon: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6' },
          { id: 'history', label: 'Audit History', icon: 'M12 8v4l3 3 M3.05 11a9 9 0 1 1 .5 4' },
          { id: 'ml', label: 'ML Studio', icon: 'M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5' }
        ].map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? '#FFFFFF' : 'var(--text-secondary)',
                background: isActive ? 'var(--brand-primary)' : 'transparent',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: isActive ? '0 2px 10px rgba(99, 102, 241, 0.4)' : 'none'
              }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d={tab.icon} />
              </svg>
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Action Controls */}
      <div className="navbar-actions-section">
        <button
          onClick={onOpenUpload}
          className="btn-secondary"
          style={{ padding: '8px 14px', fontSize: '0.85rem' }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          Upload Dataset
        </button>

        <button
          onClick={onToggleAIAssistant}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            borderRadius: 'var(--radius-md)',
            background: isAIAssistantOpen ? 'var(--brand-gradient)' : 'rgba(99, 102, 241, 0.15)',
            color: isAIAssistantOpen ? '#FFFFFF' : 'var(--accent-cyan)',
            border: `1px solid ${isAIAssistantOpen ? 'transparent' : 'rgba(6, 182, 212, 0.4)'}`,
            fontWeight: 600,
            fontSize: '0.85rem',
            cursor: 'pointer',
            boxShadow: isAIAssistantOpen ? 'var(--brand-glow)' : 'none',
            transition: 'all 0.2s ease'
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
          AI Assistant
        </button>
      </div>
    </header>
  );
};


// ==============================================================================
// FILE SUMMARY: frontend/src/components/Navbar.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This component renders the top navigation and application header bar:
//   1. Displays platform branding ("AI Data Analyst") with gradient insignia.
//   2. Shows the currently loaded dataset name and sequential version badge ('v1', 'v2').
//   3. Provides tab switching across Data Table, Health Score, Visualizations, Reports, and History.
//   4. Includes triggers for the Dataset Upload Modal and the AI Assistant Slide-over drawer.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Mounted at the top level of 'frontend/src/App.tsx'.
// - Updates active tab selection and drawer visibility in the root application state.
// ==============================================================================
