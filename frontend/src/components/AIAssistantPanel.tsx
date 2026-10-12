import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { AIPlanResponse } from '../types/api';

interface AIAssistantPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmitPrompt: (prompt: string) => Promise<AIPlanResponse>;
  onApprovePlan: (planId: string) => Promise<void>;
  isGeneratingPlan: boolean;
  isExecutingPlan: boolean;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  plan?: AIPlanResponse;
  timestamp: string;
}

export const AIAssistantPanel: React.FC<AIAssistantPanelProps> = ({
  isOpen,
  onClose,
  onSubmitPrompt,
  onApprovePlan,
  isGeneratingPlan,
  isExecutingPlan
}) => {
  const [inputPrompt, setInputPrompt] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: "Hello! I am your AI Data Analyst. Ask me to clean data, handle missing values, resolve outliers, extract dates, or format schemas. I will formulate a safe, deterministic plan for you to review before anything is applied.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);

  // Scalable/Resizable Drawer Width state (persisted to localStorage)
  const [panelWidth, setPanelWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('ai_analyst_panel_width');
      if (saved) {
        const parsed = parseInt(saved, 10);
        if (!isNaN(parsed) && parsed >= 360 && parsed <= window.innerWidth - 48) {
          return parsed;
        }
      }
    } catch {
      // ignore
    }
    return 480;
  });
  const [isResizing, setIsResizing] = useState(false);
  const [isHoveringResizer, setIsHoveringResizer] = useState(false);
  const panelWidthRef = useRef(panelWidth);
  panelWidthRef.current = panelWidth;

  const startResizing = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const calculatedWidth = window.innerWidth - e.clientX;
      const minWidth = 360;
      const maxWidth = Math.max(minWidth, window.innerWidth - 40);
      const clamped = Math.max(minWidth, Math.min(maxWidth, calculatedWidth));
      panelWidthRef.current = clamped;
      setPanelWidth(clamped);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      try {
        localStorage.setItem('ai_analyst_panel_width', String(panelWidthRef.current));
      } catch {
        // ignore
      }
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: false });
    window.addEventListener('mouseup', handleMouseUp);
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isResizing]);


  const toggleExpand = () => {
    setPanelWidth(prev => {
      const next = prev > 620 ? 480 : Math.min(840, window.innerWidth - 60);
      try {
        localStorage.setItem('ai_analyst_panel_width', String(next));
      } catch {
        // ignore
      }
      return next;
    });
  };

  if (!isOpen) return null;

  const quickPrompts = [
    "Fill missing values in revenue with the column median",
    "Remove duplicate rows and trim text columns",
    "Clip statistical outliers using the 1.5x IQR method",
    "Convert date column to datetime and extract year"
  ];

  const handleSend = async (promptToSend?: string) => {
    const text = (promptToSend || inputPrompt).trim();
    if (!text || isGeneratingPlan) return;

    const userMsgId = Date.now().toString();
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    setMessages(prev => [
      ...prev,
      { id: userMsgId, sender: 'user', text, timestamp: nowTime }
    ]);
    setInputPrompt('');

    try {
      const plan = await onSubmitPrompt(text);
      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: plan.summary,
          plan: plan,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: `Error formulating plan: ${err.message || 'Validation failed.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    }
  };

  return (
    <>
      {/* Fullscreen transparent backdrop during resizing to guarantee mouse capture */}
      {isResizing && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99999,
            cursor: 'col-resize',
            userSelect: 'none'
          }}
        />
      )}

      <div
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: `${panelWidth}px`,
          maxWidth: 'calc(100vw - 32px)',
          background: '#111827',
          borderLeft: '1px solid var(--border-subtle)',
          boxShadow: '-10px 0 36px rgba(0, 0, 0, 0.6)',
          zIndex: 45,
          display: 'flex',
          flexDirection: 'column',
          transition: isResizing ? 'none' : 'width 0.18s cubic-bezier(0.16, 1, 0.3, 1)'
        }}
        className="side-drawer animate-slide-in"
      >
        {/* Antigravity IDE-Style Draggable Resizer Edge */}
        <div
          onMouseDown={startResizing}
          onDoubleClick={toggleExpand}
          onMouseEnter={() => setIsHoveringResizer(true)}
          onMouseLeave={() => setIsHoveringResizer(false)}
          title="Click & drag to scale AI Assistant width. Double-click to toggle wide view."
          style={{
            position: 'absolute',
            left: -8,
            top: 0,
            bottom: 0,
            width: '16px',
            cursor: 'col-resize',
            zIndex: 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            userSelect: 'none'
          }}
        >
          {/* Full-height glow accent line */}
          <div
            style={{
              position: 'absolute',
              left: '7px',
              top: 0,
              bottom: 0,
              width: isResizing || isHoveringResizer ? '3px' : '1px',
              background: isResizing
                ? 'var(--brand-primary)'
                : isHoveringResizer
                ? 'rgba(99, 102, 241, 0.8)'
                : 'rgba(255, 255, 255, 0.08)',
              boxShadow: isResizing || isHoveringResizer ? '0 0 10px rgba(99, 102, 241, 0.7)' : 'none',
              transition: 'all 0.15s ease'
            }}
          />

          {/* Grip pill handle */}
          <div
            style={{
              width: '16px',
              height: '44px',
              borderRadius: '999px',
              background: isResizing
                ? 'var(--brand-primary)'
                : isHoveringResizer
                ? '#1E293B'
                : 'rgba(30, 41, 59, 0.75)',
              border: `1px solid ${isResizing || isHoveringResizer ? 'var(--brand-primary)' : 'rgba(255, 255, 255, 0.18)'}`,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '3px',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
              transition: 'all 0.15s ease',
              zIndex: 2
            }}
          >
            <span style={{ width: '3px', height: '3px', borderRadius: '50%', background: isResizing || isHoveringResizer ? '#FFFFFF' : 'rgba(255, 255, 255, 0.5)' }} />
            <span style={{ width: '3px', height: '3px', borderRadius: '50%', background: isResizing || isHoveringResizer ? '#FFFFFF' : 'rgba(255, 255, 255, 0.5)' }} />
            <span style={{ width: '3px', height: '3px', borderRadius: '50%', background: isResizing || isHoveringResizer ? '#FFFFFF' : 'rgba(255, 255, 255, 0.5)' }} />
          </div>

          {/* Live width tooltip floating to the left during resize/hover */}
          {(isResizing || isHoveringResizer) && (
            <div
              style={{
                position: 'absolute',
                left: '-68px',
                background: 'rgba(15, 23, 42, 0.95)',
                border: '1px solid var(--brand-primary)',
                borderRadius: '6px',
                padding: '3px 8px',
                fontSize: '0.68rem',
                fontWeight: 700,
                color: '#FFFFFF',
                whiteSpace: 'nowrap',
                pointerEvents: 'none',
                boxShadow: '0 4px 14px rgba(0, 0, 0, 0.5)'
              }}
            >
              {Math.round(panelWidth)} px
            </div>
          )}
        </div>

        {/* Header */}
        <div style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(17, 24, 39, 0.95)',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--brand-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
            </div>
            <div style={{ minWidth: 0 }}>
              <h3 style={{ fontSize: '0.96rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, whiteSpace: 'nowrap' }}>
                AI Assistant
              </h3>
              <span style={{ fontSize: '0.70rem', color: 'var(--text-muted)', fontWeight: 500, whiteSpace: 'nowrap' }}>
                Autonomous Cleaning & Gemini AI
              </span>
            </div>
          </div>

          {/* Panel Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>

            {/* Quick Toggle Expand */}
            <button
              onClick={toggleExpand}
              title={panelWidth > 620 ? "Collapse to standard width" : "Expand to wide view"}
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: '5px 7px',
                fontSize: '0.72rem',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              {panelWidth > 620 ? (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="4 14 10 14 10 20" />
                  <polyline points="20 10 14 10 14 4" />
                  <line x1="14" y1="10" x2="21" y2="3" />
                  <line x1="3" y1="21" x2="10" y2="14" />
                </svg>
              ) : (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 3 21 3 21 9" />
                  <polyline points="9 21 3 21 3 15" />
                  <line x1="21" y1="3" x2="14" y2="10" />
                  <line x1="3" y1="21" x2="10" y2="14" />
                </svg>
              )}
            </button>

          <button
            onClick={onClose}
            title="Close Assistant"
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '6px' }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>

      {/* Chat Messages Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          return (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: isUser ? 'flex-end' : 'flex-start'
              }}
            >
              <div
                style={{
                  maxWidth: '88%',
                  padding: '12px 16px',
                  borderRadius: isUser ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                  background: isUser ? 'var(--brand-primary)' : 'rgba(30, 41, 59, 0.7)',
                  color: '#FFFFFF',
                  fontSize: '0.88rem',
                  lineHeight: 1.5,
                  border: isUser ? 'none' : '1px solid var(--border-subtle)'
                }}
              >
                {msg.text}

                {/* Plan Card */}
                {msg.plan && (() => {
                  const planObj = msg.plan as any;
                  const operations: any[] = Array.isArray(planObj.operations)
                    ? planObj.operations
                    : Array.isArray(planObj.plan_json?.operations)
                    ? planObj.plan_json.operations
                    : [];
                  const warnings: string[] = Array.isArray(planObj.warnings)
                    ? planObj.warnings
                    : Array.isArray(planObj.warnings_json)
                    ? planObj.warnings_json
                    : Array.isArray(planObj.plan_json?.warnings)
                    ? planObj.plan_json.warnings
                    : [];
                  const planId = planObj.plan_id || planObj.id;

                  return (
                    <div style={{
                      marginTop: '12px',
                      padding: '14px',
                      background: 'rgba(15, 23, 42, 0.8)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-subtle)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-cyan)', textTransform: 'uppercase' }}>
                          Proposed Operations ({operations.length})
                        </span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          Model: {planObj.model || 'Deterministic AI Planner'}
                        </span>
                      </div>

                      {operations.length > 0 ? (
                        <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0', fontSize: '0.82rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {operations.map((op, opIdx) => (
                            <li key={opIdx} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255, 255, 255, 0.03)', padding: '6px 10px', borderRadius: 'var(--radius-sm)' }}>
                              <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>•</span>
                              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{op.type || 'Operation'}</span>
                              {(op.column || op.columns) && (
                                <span style={{ color: 'var(--accent-cyan)' }}>
                                  on '{op.column || (Array.isArray(op.columns) ? op.columns.join(', ') : op.columns)}'
                                </span>
                              )}
                              {op.strategy && <span style={{ color: 'var(--text-muted)' }}>({op.strategy})</span>}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '8px 0' }}>
                          No specific transformation operations required.
                        </p>
                      )}

                      {warnings.length > 0 && (
                        <div style={{ marginTop: '8px', fontSize: '0.78rem', color: '#FBBF24' }}>
                          ⚠️ {warnings.join(', ')}
                        </div>
                      )}

                      {planId && operations.length > 0 && (
                        <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                          <button
                            onClick={() => onApprovePlan(planId)}
                            disabled={isExecutingPlan}
                            className="btn-primary"
                            style={{ padding: '7px 14px', fontSize: '0.8rem', flex: 1 }}
                          >
                            {isExecutingPlan ? 'Applying...' : 'Approve & Execute'}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px', padding: '0 4px' }}>
                {msg.timestamp}
              </span>
            </div>
          );
        })}

        {isGeneratingPlan && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>
            <svg className="animate-pulse-subtle" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            Analyzing schema & planning safe transformations...
          </div>
        )}
      </div>

      {/* Suggested Quick Prompts */}
      <div style={{ padding: '0 20px 12px 20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
          Suggested Operations
        </span>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {quickPrompts.slice(0, 2).map((qp, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(qp)}
              style={{
                textAlign: 'left',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '6px 10px',
                color: 'var(--text-secondary)',
                fontSize: '0.78rem',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#FFFFFF')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
            >
              • {qp}
            </button>
          ))}
        </div>
      </div>

      {/* Input Form */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid var(--border-subtle)',
        background: 'rgba(17, 24, 39, 0.95)'
      }}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          style={{ display: 'flex', gap: '10px' }}
        >
          <input
            type="text"
            placeholder="Ask AI to clean, fill, or transform data..."
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            disabled={isGeneratingPlan}
            style={{
              flex: 1,
              padding: '10px 14px',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              outline: 'none'
            }}
          />
          <button
            type="submit"
            className="btn-primary"
            disabled={!inputPrompt.trim() || isGeneratingPlan}
            style={{ padding: '10px 16px' }}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  </>
  );
};


// ==============================================================================
// FILE SUMMARY: frontend/src/components/AIAssistantPanel.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This component provides the Conversational AI Assistant and Operation Planner Drawer:
//   1. Chat conversation interface allowing natural language queries.
//   2. Quick suggested prompt chips ("Fill missing revenue", "Remove outliers", "Deduplicate").
//   3. Structured operation plan card displaying proposed operations, column references,
//      and potential impact warnings.
//   4. 'Approve & Execute' button invoking deterministic execution on the active version
//      and committing a new immutable snapshot with source='ai'.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Toggled open/closed from the top Navbar in 'frontend/src/App.tsx'.
// - Delegates plan creation and approval to 'api.createAIPlan' and 'api.approveAIPlan'.
// ==============================================================================
