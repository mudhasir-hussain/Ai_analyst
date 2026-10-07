import React, { useState, useRef } from 'react';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (file: File, sheetName?: string) => Promise<void>;
  onLoadSample?: () => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
  onLoadSample
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sheetName, setSheetName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateAndSetFile = (file: File) => {
    setErrorMessage(null);
    const validExtensions = ['.csv', '.xlsx'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some(ext => fileName.endsWith(ext));

    if (!isValid) {
      setErrorMessage("Unsupported file format. Please upload a CSV (.csv) or Excel (.xlsx) file.");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setErrorMessage("File exceeds 25 MB limit. Please select a smaller file.");
      return;
    }

    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    try {
      setIsUploading(true);
      setErrorMessage(null);
      await onUploadSuccess(selectedFile, sheetName.trim() || undefined);
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to upload and parse dataset.");
    } finally {
      setIsUploading(false);
    }
  };

  const isExcel = selectedFile?.name.toLowerCase().endsWith('.xlsx');

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 50,
      padding: '20px'
    }}>
      <div className="glass-panel animate-fade-in" style={{
        width: '100%',
        maxWidth: '540px',
        padding: '32px',
        background: '#111827',
        border: '1px solid rgba(255, 255, 255, 0.12)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)' }}>Upload Dataset</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Supports CSV and Excel files up to 25 MB</p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--radius-sm)'
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        {errorMessage && (
          <div style={{
            background: 'rgba(244, 63, 94, 0.15)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 16px',
            marginBottom: '20px',
            color: '#FB7185',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${dragActive ? 'var(--brand-primary)' : selectedFile ? 'var(--accent-emerald)' : 'rgba(255, 255, 255, 0.15)'}`,
              borderRadius: 'var(--radius-lg)',
              padding: '40px 20px',
              textAlign: 'center',
              cursor: 'pointer',
              background: dragActive ? 'rgba(99, 102, 241, 0.08)' : selectedFile ? 'rgba(16, 185, 129, 0.05)' : 'rgba(30, 41, 59, 0.4)',
              transition: 'all 0.2s ease',
              marginBottom: '20px'
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />

            <div style={{
              width: '54px',
              height: '54px',
              borderRadius: '50%',
              background: selectedFile ? 'rgba(16, 185, 129, 0.2)' : 'rgba(99, 102, 241, 0.15)',
              color: selectedFile ? 'var(--accent-emerald)' : 'var(--brand-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto'
            }}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
            </div>

            {selectedFile ? (
              <div>
                <p style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>{selectedFile.name}</p>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '4px' }}>
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to ingest
                </p>
              </div>
            ) : (
              <div>
                <p style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
                  Click to select or drag and drop your file here
                </p>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '4px' }}>
                  Supported formats: CSV, Excel (.xlsx)
                </p>
              </div>
            )}
          </div>

          {isExcel && (
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                Sheet Name (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. SalesData (leave empty for first sheet)"
                value={sheetName}
                onChange={(e) => setSheetName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  outline: 'none'
                }}
              />
            </div>
          )}

          {onLoadSample && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: '16px 0' }}>
                <div style={{ flex: 1, height: '1px', background: 'var(--border-subtle)' }} />
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600 }}>
                  Or Try Demo Benchmark
                </span>
                <div style={{ flex: 1, height: '1px', background: 'var(--border-subtle)' }} />
              </div>
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onLoadSample();
                }}
                className="btn-secondary"
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  background: 'rgba(99, 102, 241, 0.08)',
                  borderColor: 'rgba(99, 102, 241, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  textAlign: 'left'
                }}
              >
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
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                  </svg>
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.88rem', color: '#FFFFFF' }}>
                    Load Global Enterprise Sales Demo (53 rows)
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                    Contains missing values, skew, outliers, and duplicates to test all AI functions
                  </div>
                </div>
              </button>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              disabled={isUploading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={!selectedFile || isUploading}
            >
              {isUploading ? (
                <>
                  <svg className="animate-pulse-subtle" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                  </svg>
                  Processing & Profiling...
                </>
              ) : (
                'Upload & Inspect'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};


// ==============================================================================
// FILE SUMMARY: frontend/src/components/UploadModal.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This component provides the interactive file upload dialog:
//   1. Drag-and-drop file ingestion zone with visual hover feedback.
//   2. Pre-flight file validation restricting extensions (.csv, .xlsx) and sizes (<25MB).
//   3. Sheet name input for targeted multi-worksheet Excel files.
//   4. Clean loading progress state during parser ingestion and profiling.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Rendered by 'frontend/src/App.tsx' when the user clicks 'Upload Dataset'.
// - Delegates upload execution to 'api.uploadDataset' in 'frontend/src/services/api.ts'.
// ==============================================================================
