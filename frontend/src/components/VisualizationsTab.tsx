import React, { useState, useEffect } from 'react';
import type { ChartRecommendation, VisualizationResponse } from '../types/api';

interface VisualizationsTabProps {
  columns: string[];
  recommendations: ChartRecommendation[];
  previews: VisualizationResponse[];
  onRequestCustomChart: (req: any) => Promise<VisualizationResponse>;
}

export const VisualizationsTab: React.FC<VisualizationsTabProps> = ({
  columns,
  recommendations,
  previews,
  onRequestCustomChart
}) => {
  const [activeChart, setActiveChart] = useState<VisualizationResponse | null>(previews[0] || null);
  const [chartType, setChartType] = useState<string>('bar');
  const [xCol, setXCol] = useState<string>(columns[0] || '');
  const [yCol, setYCol] = useState<string>(columns[1] || '');
  const [aggregation, setAggregation] = useState<string>('sum');
  const [isRendering, setIsRendering] = useState(false);

  useEffect(() => {
    if (previews.length > 0 && !activeChart) {
      setActiveChart(previews[0]);
    }
  }, [previews]);

  useEffect(() => {
    if (columns.length > 0) {
      if (!xCol || !columns.includes(xCol)) setXCol(columns[0]);
      if (!yCol || !columns.includes(yCol)) setYCol(columns[1] || columns[0]);
    }
  }, [columns, xCol, yCol]);

  const handleBuildChart = async () => {
    try {
      setIsRendering(true);
      const res = await onRequestCustomChart({
        chart_type: chartType,
        x_column: xCol,
        y_column: yCol,
        aggregation: aggregation,
        limit: 20
      });
      setActiveChart(res);
    } catch (err) {
      console.error("Error generating chart:", err);
    } finally {
      setIsRendering(false);
    }
  };

  // SVG Chart Renderer
  const renderSVGChart = (chart: VisualizationResponse) => {
    const data = chart.data || [];
    if (data.length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
          No data available for this chart configuration.
        </div>
      );
    }

    const width = 680;
    const height = 300;
    const padding = { top: 30, right: 30, bottom: 50, left: 60 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    if (chart.chart_type === 'bar' || chart.chart_type === 'histogram') {
      const values = data.map(d => Number(d.value || d.count || 0));
      const maxVal = Math.max(...values, 1);
      const barWidth = chartWidth / data.length;

      return (
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
          {/* Y Axis line */}
          <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke="rgba(255,255,255,0.15)" />
          {/* X Axis line */}
          <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} stroke="rgba(255,255,255,0.15)" />

          {/* Bars */}
          {data.map((item, idx) => {
            const val = Number(item.value || item.count || 0);
            const barH = (val / maxVal) * chartHeight;
            const x = padding.left + idx * barWidth + barWidth * 0.15;
            const y = height - padding.bottom - barH;
            const w = barWidth * 0.7;

            return (
              <g key={idx}>
                <rect
                  x={x}
                  y={y}
                  width={w}
                  height={barH}
                  fill="url(#barGradient)"
                  rx="4"
                  style={{ transition: 'all 0.3s ease', cursor: 'pointer' }}
                >
                  <title>{`${item.name || item.bin}: ${val.toLocaleString()}`}</title>
                </rect>
                <text
                  x={x + w / 2}
                  y={height - padding.bottom + 18}
                  fill="var(--text-muted)"
                  fontSize="11"
                  textAnchor="middle"
                >
                  {String(item.name || item.bin || '').slice(0, 8)}
                </text>
              </g>
            );
          })}

          <defs>
            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3B82F6" />
              <stop offset="100%" stopColor="#1D4ED8" />
            </linearGradient>
          </defs>
        </svg>
      );
    } else if (chart.chart_type === 'line') {
      const values = data.map(d => Number(d.value || 0));
      const maxVal = Math.max(...values, 1);
      const minVal = Math.min(...values, 0);
      const range = maxVal - minVal || 1;

      const points = data.map((d, idx) => {
        const x = padding.left + (idx / Math.max(1, data.length - 1)) * chartWidth;
        const val = Number(d.value || 0);
        const y = height - padding.bottom - ((val - minVal) / range) * chartHeight;
        return `${x},${y}`;
      }).join(' ');

      return (
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
          <polyline
            fill="none"
            stroke="var(--accent-cyan)"
            strokeWidth="3"
            points={points}
          />
          {data.map((d, idx) => {
            const x = padding.left + (idx / Math.max(1, data.length - 1)) * chartWidth;
            const val = Number(d.value || 0);
            const y = height - padding.bottom - ((val - minVal) / range) * chartHeight;
            return (
              <circle
                key={idx}
                cx={x}
                cy={y}
                r="4"
                fill="#FFFFFF"
                stroke="var(--accent-cyan)"
                strokeWidth="2"
              >
                <title>{`${d.name}: ${val.toLocaleString()}`}</title>
              </circle>
            );
          })}
        </svg>
      );
    } else if (chart.chart_type === 'scatter') {
      const xKey = chart.x_column || Object.keys(data[0] || {})[0] || 'x';
      const yKey = chart.y_column || Object.keys(data[0] || {})[1] || 'y';

      const validPoints = data
        .map(d => ({
          x: Number(d[xKey] ?? d.x ?? 0),
          y: Number(d[yKey] ?? d.y ?? 0),
          label: d.label || d.name || ''
        }))
        .filter(p => !isNaN(p.x) && !isNaN(p.y));

      if (validPoints.length === 0) {
        return (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
            No numeric data points available for scatter plot.
          </div>
        );
      }

      const xVals = validPoints.map(p => p.x);
      const yVals = validPoints.map(p => p.y);

      let minX = Math.min(...xVals);
      let maxX = Math.max(...xVals);
      let minY = Math.min(...yVals);
      let maxY = Math.max(...yVals);

      const rangeX = maxX - minX || 1;
      const rangeY = maxY - minY || 1;
      const padX = rangeX * 0.08;
      const padY = rangeY * 0.08;
      minX -= padX; maxX += padX;
      minY -= padY; maxY += padY;
      const spanX = maxX - minX;
      const spanY = maxY - minY;

      const toScreenX = (val: number) => padding.left + ((val - minX) / spanX) * chartWidth;
      const toScreenY = (val: number) => height - padding.bottom - ((val - minY) / spanY) * chartHeight;

      const xTicks = [0, 0.25, 0.5, 0.75, 1].map(ratio => minX + ratio * spanX);
      const yTicks = [0, 0.25, 0.5, 0.75, 1].map(ratio => minY + ratio * spanY);

      return (
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
          <defs>
            <radialGradient id="scatterDotGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#A78BFA" stopOpacity="1" />
              <stop offset="100%" stopColor="#7C3AED" stopOpacity="0.85" />
            </radialGradient>
          </defs>

          {/* Grid lines */}
          {yTicks.map((yVal, i) => (
            <line
              key={`ygrid-${i}`}
              x1={padding.left}
              y1={toScreenY(yVal)}
              x2={width - padding.right}
              y2={toScreenY(yVal)}
              stroke="rgba(255,255,255,0.07)"
              strokeDasharray="3 3"
            />
          ))}
          {xTicks.map((xVal, i) => (
            <line
              key={`xgrid-${i}`}
              x1={toScreenX(xVal)}
              y1={padding.top}
              x2={toScreenX(xVal)}
              y2={height - padding.bottom}
              stroke="rgba(255,255,255,0.07)"
              strokeDasharray="3 3"
            />
          ))}

          {/* Y Axis line & tick labels */}
          <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke="rgba(255,255,255,0.2)" />
          {yTicks.map((yVal, i) => (
            <text
              key={`ytick-${i}`}
              x={padding.left - 8}
              y={toScreenY(yVal) + 4}
              fill="var(--text-muted)"
              fontSize="10"
              textAnchor="end"
            >
              {Math.abs(yVal) >= 1000 ? `${(yVal / 1000).toFixed(1)}k` : yVal.toFixed(yVal % 1 === 0 ? 0 : 1)}
            </text>
          ))}

          {/* X Axis line & tick labels */}
          <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} stroke="rgba(255,255,255,0.2)" />
          {xTicks.map((xVal, i) => (
            <text
              key={`xtick-${i}`}
              x={toScreenX(xVal)}
              y={height - padding.bottom + 18}
              fill="var(--text-muted)"
              fontSize="10"
              textAnchor="middle"
            >
              {Math.abs(xVal) >= 1000 ? `${(xVal / 1000).toFixed(1)}k` : xVal.toFixed(xVal % 1 === 0 ? 0 : 1)}
            </text>
          ))}

          {/* Axis Titles */}
          <text
            x={padding.left + chartWidth / 2}
            y={height - 8}
            fill="var(--text-secondary)"
            fontSize="11"
            fontWeight="600"
            textAnchor="middle"
          >
            {xKey.replace(/_/g, ' ').toUpperCase()}
          </text>
          <text
            x={16}
            y={padding.top + chartHeight / 2}
            fill="var(--text-secondary)"
            fontSize="11"
            fontWeight="600"
            textAnchor="middle"
            transform={`rotate(-90 16 ${padding.top + chartHeight / 2})`}
          >
            {yKey.replace(/_/g, ' ').toUpperCase()}
          </text>

          {/* Scatter Points */}
          {validPoints.map((pt, idx) => {
            const cx = toScreenX(pt.x);
            const cy = toScreenY(pt.y);
            return (
              <circle
                key={idx}
                cx={cx}
                cy={cy}
                r="5"
                fill="url(#scatterDotGlow)"
                stroke="#EDE9FE"
                strokeWidth="1.5"
                style={{ cursor: 'pointer', transition: 'r 0.15s ease' }}
                onMouseEnter={e => e.currentTarget.setAttribute('r', '8')}
                onMouseLeave={e => e.currentTarget.setAttribute('r', '5')}
              >
                <title>{`${xKey}: ${pt.x.toLocaleString()} | ${yKey}: ${pt.y.toLocaleString()}${pt.label ? ` (${pt.label})` : ''}`}</title>
              </circle>
            );
          })}
        </svg>
      );
    } else if (chart.chart_type === 'box') {
      const bData = data[0] || {};
      const minVal = Number(bData.min ?? 0);
      const q1Val = Number(bData.q1 ?? 0);
      const medVal = Number(bData.median ?? 0);
      const q3Val = Number(bData.q3 ?? 0);
      const maxVal = Number(bData.max ?? 0);
      const outliers: number[] = Array.isArray(bData.outliers) ? bData.outliers : [];

      const allVals = [minVal, q1Val, medVal, q3Val, maxVal, ...outliers];
      const boundMin = Math.min(...allVals);
      const boundMax = Math.max(...allVals);
      const span = boundMax - boundMin || 1;
      const pad = span * 0.1;
      const plotMin = boundMin - pad;
      const plotMax = boundMax + pad;
      const plotSpan = plotMax - plotMin;

      const toY = (v: number) => height - padding.bottom - ((v - plotMin) / plotSpan) * chartHeight;

      const boxX = padding.left + chartWidth * 0.35;
      const boxW = chartWidth * 0.3;

      return (
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
          {/* Whiskers */}
          <line x1={boxX + boxW / 2} y1={toY(minVal)} x2={boxX + boxW / 2} y2={toY(q1Val)} stroke="var(--accent-purple)" strokeWidth="2" strokeDasharray="4 4" />
          <line x1={boxX + boxW / 2} y1={toY(q3Val)} x2={boxX + boxW / 2} y2={toY(maxVal)} stroke="var(--accent-purple)" strokeWidth="2" strokeDasharray="4 4" />
          <line x1={boxX + boxW * 0.25} y1={toY(minVal)} x2={boxX + boxW * 0.75} y2={toY(minVal)} stroke="var(--accent-purple)" strokeWidth="2" />
          <line x1={boxX + boxW * 0.25} y1={toY(maxVal)} x2={boxX + boxW * 0.75} y2={toY(maxVal)} stroke="var(--accent-purple)" strokeWidth="2" />

          {/* IQR Box */}
          <rect
            x={boxX}
            y={toY(q3Val)}
            width={boxW}
            height={Math.max(2, toY(q1Val) - toY(q3Val))}
            fill="rgba(139, 92, 246, 0.25)"
            stroke="var(--accent-purple)"
            strokeWidth="2"
            rx="4"
          >
            <title>{`Q3: ${q3Val.toLocaleString()} | Median: ${medVal.toLocaleString()} | Q1: ${q1Val.toLocaleString()}`}</title>
          </rect>

          {/* Median line */}
          <line x1={boxX} y1={toY(medVal)} x2={boxX + boxW} y2={toY(medVal)} stroke="#F59E0B" strokeWidth="3" />

          {/* Outliers */}
          {outliers.map((oVal, idx) => (
            <circle key={idx} cx={boxX + boxW / 2} cy={toY(oVal)} r="4" fill="#EF4444" stroke="#FFFFFF" strokeWidth="1">
              <title>{`Outlier: ${oVal}`}</title>
            </circle>
          ))}

          {/* Labels */}
          <text x={boxX + boxW + 12} y={toY(medVal) + 4} fill="#F59E0B" fontSize="11" fontWeight="600">Median: {medVal.toLocaleString()}</text>
          <text x={boxX + boxW + 12} y={toY(q3Val) + 4} fill="var(--text-muted)" fontSize="10">Q3: {q3Val.toLocaleString()}</text>
          <text x={boxX + boxW + 12} y={toY(q1Val) + 4} fill="var(--text-muted)" fontSize="10">Q1: {q1Val.toLocaleString()}</text>
        </svg>
      );
    } else if (chart.chart_type === 'heatmap') {
      const distinctCols = Array.from(new Set(data.map(d => d.x || d.column_1 || '')));
      const cellSize = Math.min(chartWidth / (distinctCols.length || 1), chartHeight / (distinctCols.length || 1), 60);

      return (
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
          {data.map((item, idx) => {
            const xIdx = distinctCols.indexOf(item.x);
            const yIdx = distinctCols.indexOf(item.y);
            if (xIdx === -1 || yIdx === -1) return null;
            const r = Number(item.correlation ?? item.value ?? 0);
            const cx = padding.left + xIdx * cellSize;
            const cy = padding.top + yIdx * cellSize;
            const color = r >= 0 ? `rgba(59, 130, 246, ${Math.max(0.15, Math.abs(r))})` : `rgba(239, 68, 68, ${Math.max(0.15, Math.abs(r))})`;

            return (
              <g key={idx}>
                <rect x={cx} y={cy} width={cellSize - 2} height={cellSize - 2} fill={color} rx="3">
                  <title>{`${item.x} vs ${item.y}: r = ${r.toFixed(2)}`}</title>
                </rect>
                <text x={cx + cellSize / 2 - 1} y={cy + cellSize / 2 + 4} fill="#FFFFFF" fontSize="10" textAnchor="middle">
                  {r.toFixed(2)}
                </text>
              </g>
            );
          })}
        </svg>
      );
    }

    return (
      <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-secondary)' }}>
        Rendered view for {chart.chart_type}. Total data points: {data.length}
      </div>
    );
  };

  return (
    <div className="animate-fade-in" style={{ padding: '24px 0' }}>
      {/* Top Recommendations Carousel / Grid */}
      <div style={{ marginBottom: '28px' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '6px' }}>
          Chart Recommendations
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Recommended based on inferred types and statistical distributions
        </p>

        {recommendations.length === 0 ? (
          <div className="glass-panel" style={{ padding: '28px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <p style={{ fontSize: '0.9rem' }}>
              No dataset loaded yet. Load sample data or upload a file to view automated chart recommendations.
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
            {recommendations.map((rec, idx) => {
              const isSelected = activeChart?.title === rec.title;
              return (
                <div
                  key={idx}
                  onClick={() => {
                    const matchingPreview = previews.find(p => p.title === rec.title);
                    if (matchingPreview) setActiveChart(matchingPreview);
                  }}
                  className="glass-panel"
                  style={{
                    padding: '16px 18px',
                    cursor: 'pointer',
                    borderColor: isSelected ? 'var(--brand-primary)' : 'var(--border-subtle)',
                    background: isSelected ? 'rgba(37, 99, 235, 0.12)' : 'var(--bg-card)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span className="badge badge-numeric" style={{ fontSize: '0.65rem' }}>
                      {rec.chart_type}
                    </span>
                  </div>
                  <h4 style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                    {rec.title}
                  </h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    {rec.reason}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Main Chart Viewer & Builder */}
      <div className="viz-workspace-grid" style={{ gap: '24px' }}>
        {/* Active Visualization Render */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {activeChart?.title || 'Interactive Visualizer'}
              </h3>
              {activeChart?.x_column && (
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  X: {activeChart.x_column} {activeChart.y_column ? `• Y: ${activeChart.y_column}` : ''}
                </span>
              )}
            </div>
            {activeChart?.chart_type && (
              <span className="badge badge-categorical">
                {activeChart.chart_type}
              </span>
            )}
          </div>

          <div style={{ minHeight: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {activeChart ? renderSVGChart(activeChart) : <p style={{ color: 'var(--text-muted)' }}>Select or build a chart.</p>}
          </div>

          {/* Observations and Insights */}
          {activeChart?.insights && activeChart.insights.length > 0 && (
            <div style={{ marginTop: '20px', padding: '14px 18px', background: 'rgba(6, 182, 212, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(6, 182, 212, 0.25)' }}>
              <div style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--accent-cyan)', marginBottom: '4px' }}>
                Statistical Findings
              </div>
              <ul style={{ paddingLeft: '16px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                {activeChart.insights.map((ins, i) => (
                  <li key={i}>{ins}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Custom Chart Builder Sidebar */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '16px', color: 'var(--text-primary)' }}>
            Custom Chart Builder
          </h4>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Chart Type
              </label>
              <select
                value={chartType}
                onChange={(e) => setChartType(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              >
                <option value="bar">Bar Chart</option>
                <option value="line">Line Chart</option>
                <option value="scatter">Scatter Plot</option>
                <option value="histogram">Histogram</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                X-Axis Column
              </label>
              <select
                value={xCol}
                onChange={(e) => setXCol(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              >
                {columns.map(col => <option key={col} value={col}>{col}</option>)}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Y-Axis Column (Value)
              </label>
              <select
                value={yCol}
                onChange={(e) => setYCol(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              >
                {columns.map(col => <option key={col} value={col}>{col}</option>)}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Aggregation
              </label>
              <select
                value={aggregation}
                onChange={(e) => setAggregation(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              >
                <option value="sum">Sum</option>
                <option value="mean">Mean (Average)</option>
                <option value="count">Count</option>
                <option value="min">Minimum</option>
                <option value="max">Maximum</option>
              </select>
            </div>

            <button
              onClick={handleBuildChart}
              disabled={isRendering}
              className="btn-primary"
              style={{ marginTop: '8px', padding: '10px' }}
            >
              {isRendering ? 'Rendering...' : 'Generate Visualization'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};


// ==============================================================================
// FILE SUMMARY: frontend/src/components/VisualizationsTab.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This component provides the Visual Analytics and Chart Recommendation Suite:
//   1. Displays intelligent chart recommendation cards with analytical rationales.
//   2. High-performance SVG chart renderer supporting Bar, Line, Scatter, and Histogram views.
//   3. Custom Chart Builder controls allowing users to select axes and aggregation strategies.
//   4. Presents automated statistical findings and distribution observations.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Rendered in 'frontend/src/App.tsx' under the 'Visualizations' tab.
// - Receives recommendations and series data generated via 'api.getDatasetVisualizations'
//   and 'api.requestVisualization'.
// ==============================================================================
