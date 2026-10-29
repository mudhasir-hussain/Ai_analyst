import React, { useState, useEffect } from 'react';
import type {
  MLTargetCandidate,
  MLTrainResponse,
  MLCompareResponse,
  MLPredictResponse,
  DatasetVersion
} from '../types/api';
import { api } from '../services/api';

interface MLLabTabProps {
  datasetId?: string;
  versions: DatasetVersion[];
  activeVersionNumber?: number;
  onLoadSample?: () => void;
  showToast: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export const MLLabTab: React.FC<MLLabTabProps> = ({
  datasetId,
  versions,
  activeVersionNumber = 1,
  onLoadSample,
  showToast
}) => {
  // State
  const [candidates, setCandidates] = useState<MLTargetCandidate[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string>('');
  const [modelType, setModelType] = useState<string>('decision_tree');
  const [testSize, setTestSize] = useState<number>(0.2);
  const [maxDepth, setMaxDepth] = useState<number | null>(3);
  const [isUnconstrainedDepth, setIsUnconstrainedDepth] = useState<boolean>(false);
  const [knnNeighbors, setKnnNeighbors] = useState<number>(5);
  const [svmKernel, setSvmKernel] = useState<string>('rbf');

  // Feature Selection What-If Sandbox State
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
  const [isFeatureSelectorOpen, setIsFeatureSelectorOpen] = useState<boolean>(false);

  // What-If Live Prediction Simulator State
  const [simulatorInputs, setSimulatorInputs] = useState<Record<string, any>>({});
  const [predictionResult, setPredictionResult] = useState<MLPredictResponse | null>(null);
  const [isPredicting, setIsPredicting] = useState<boolean>(false);
  const [isExportingCode, setIsExportingCode] = useState<boolean>(false);

  // Results State
  const [trainResult, setTrainResult] = useState<MLTrainResponse | null>(null);
  const [compareResult, setCompareResult] = useState<MLCompareResponse | null>(null);
  const [isTraining, setIsTraining] = useState<boolean>(false);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [selectedBaseVersion, setSelectedBaseVersion] = useState<number>(1);
  const [activeVizTab, setActiveVizTab] = useState<'loss' | 'actual_vs_pred' | 'features' | 'overfitting' | 'confusion_matrix' | 'what_if'>('overfitting');

  // Load target candidates when datasetId changes
  useEffect(() => {
    if (!datasetId) {
      setCandidates([]);
      setSelectedTarget('');
      setSelectedFeatures([]);
      setTrainResult(null);
      setCompareResult(null);
      return;
    }

    let isMounted = true;
    api.getMLTargets(datasetId)
      .then((res: any) => {
        if (!isMounted) return;
        const list: MLTargetCandidate[] = Array.isArray(res) ? res : (res?.candidates || []);
        setCandidates(list);
        if (list.length > 0) {
          const suitable = list.filter((c) => c.is_suitable !== false);
          const firstTarget = suitable.length > 0 ? suitable[0].column : list[0].column;
          setSelectedTarget(firstTarget);
          const validCols = list
            .filter((c) => c.column !== firstTarget && c.is_suitable !== false)
            .map((c) => c.column);
          const initialFeatures = validCols.length > 0 ? validCols : list.filter((c) => c.column !== firstTarget).map((c) => c.column);
          setSelectedFeatures(initialFeatures);

          // Auto-train default model on initial load so the dashboard is immediately interactive
          if (initialFeatures.length > 0) {
            setIsTraining(true);
            api.trainMLModel(datasetId, {
              target_column: firstTarget,
              model_type: modelType,
              test_size: testSize,
              hyperparameters: { max_depth: 3 },
              selected_features: initialFeatures,
              version_number: activeVersionNumber
            }).then((trainRes) => {
              if (isMounted) {
                setTrainResult(trainRes);
                if (trainRes.feature_specs && trainRes.feature_specs.length > 0) {
                  const initialInputs: Record<string, any> = {};
                  trainRes.feature_specs.forEach((f) => {
                    initialInputs[f.name] = f.default_val;
                  });
                  setSimulatorInputs(initialInputs);
                  api.predictMLModel(datasetId, initialInputs)
                    .then((pred) => isMounted && setPredictionResult(pred))
                    .catch(() => {});
                }
              }
            }).catch(() => {
              // Non-blocking initial train error
            }).finally(() => {
              if (isMounted) setIsTraining(false);
            });
          }
        }
      })
      .catch((err) => {
        console.error("Failed to fetch ML targets:", err);
        if (isMounted) setCandidates([]);
      });

    return () => {
      isMounted = false;
    };
  }, [datasetId, activeVersionNumber]);

  const safeCandidates = Array.isArray(candidates) ? candidates : [];

  // When selectedTarget changes, update available and selected features if needed
  useEffect(() => {
    if (safeCandidates.length > 0 && selectedTarget) {
      const validFeatures = safeCandidates.map((c) => c.column).filter((c) => c !== selectedTarget);
      setSelectedFeatures((prev) => {
        const filtered = prev.filter((col) => col !== selectedTarget && validFeatures.includes(col));
        return filtered.length > 0 ? filtered : validFeatures;
      });
    }
  }, [selectedTarget, safeCandidates.length]);

  const currentCandidate = safeCandidates.find((c) => c.column === selectedTarget);
  const taskType = currentCandidate?.task_type || 'regression';
  const availableFeatures = safeCandidates.filter((c) => c.column !== selectedTarget);

  // Feature Selection Helpers
  const toggleFeature = (col: string) => {
    setSelectedFeatures((prev) => {
      if (prev.includes(col)) {
        if (prev.length <= 1) {
          showToast('At least one feature must remain selected.', 'info');
          return prev;
        }
        return prev.filter((f) => f !== col);
      } else {
        return [...prev, col];
      }
    });
  };

  const selectAllFeatures = () => {
    setSelectedFeatures(availableFeatures.map((c) => c.column));
  };

  const deselectAllFeatures = () => {
    if (availableFeatures.length > 0) {
      setSelectedFeatures([availableFeatures[0].column]);
    }
  };

  // Handler: Train Model
  const handleTrain = async (overrideModelType?: string | unknown) => {
    if (!datasetId || !selectedTarget) {
      showToast('Please select a target variable first.', 'info');
      return;
    }

    if (currentCandidate && currentCandidate.is_suitable === false) {
      showToast(`Cannot train: "${selectedTarget}" is ineligible (${currentCandidate.suitability_reason || 'ID or high-cardinality text'}).`, 'error');
      return;
    }

    if (selectedFeatures.length === 0) {
      showToast('Please select at least one feature in the Feature Selector.', 'info');
      return;
    }

    const activeModel = typeof overrideModelType === 'string' ? overrideModelType : modelType;

    setIsTraining(true);
    setCompareResult(null);
    try {
      const hyperparameters: Record<string, any> = {};
      if (activeModel === 'decision_tree' || activeModel === 'random_forest' || activeModel === 'gradient_boosting') {
        hyperparameters.max_depth = isUnconstrainedDepth ? null : maxDepth;
      }
      if (activeModel === 'neural_net') {
        hyperparameters.max_iter = 120;
      }
      if (activeModel === 'knn') {
        hyperparameters.n_neighbors = knnNeighbors;
      }
      if (activeModel === 'svm') {
        hyperparameters.kernel = svmKernel;
      }

      const res = await api.trainMLModel(datasetId, {
        target_column: selectedTarget,
        model_type: activeModel,
        test_size: testSize,
        hyperparameters,
        selected_features: selectedFeatures,
        version_number: activeVersionNumber
      });

      setTrainResult(res);
      showToast(`Trained ${res.model_name} successfully!`, 'success');

      // Initialize simulator inputs with defaults from feature_specs
      if (res.feature_specs && res.feature_specs.length > 0) {
        const initialInputs: Record<string, any> = {};
        res.feature_specs.forEach((f) => {
          initialInputs[f.name] = f.default_val;
        });
        setSimulatorInputs(initialInputs);
        api.predictMLModel(datasetId, initialInputs)
          .then((pred) => setPredictionResult(pred))
          .catch(() => {});
      }

      // Auto-switch viz tab depending on model and metrics
      if (res.metrics.confusion_matrix) {
        setActiveVizTab('confusion_matrix');
      } else if (res.loss_curve && res.loss_curve.length > 0) {
        setActiveVizTab('loss');
      } else {
        setActiveVizTab('overfitting');
      }
    } catch (err: any) {
      showToast(err.message || 'Failed to train machine learning model.', 'error');
    } finally {
      setIsTraining(false);
    }
  };

  // Handler: Run What-If Prediction
  const handleRunPrediction = async (updatedInputs?: Record<string, any>) => {
    if (!datasetId) return;
    const inputsToUse = updatedInputs || simulatorInputs;
    setIsPredicting(true);
    try {
      const pred = await api.predictMLModel(datasetId, inputsToUse);
      setPredictionResult(pred);
    } catch (err: any) {
      showToast(err.message || 'Prediction failed.', 'error');
    } finally {
      setIsPredicting(false);
    }
  };

  const handleSimulatorChange = (featName: string, val: any) => {
    const updated = { ...simulatorInputs, [featName]: val };
    setSimulatorInputs(updated);
    handleRunPrediction(updated);
  };

  // Handler: Export Trained Model Code
  const handleExportCode = async () => {
    if (!datasetId) return;
    setIsExportingCode(true);
    try {
      const res = await api.exportMLCode(datasetId);
      const blob = new Blob([res.code], { type: 'text/x-python' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = res.filename || `inference_pipeline_${datasetId.slice(0, 8)}.py`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast('Exported standalone Python model script!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to export model code. Train a model first.', 'error');
    } finally {
      setIsExportingCode(false);
    }
  };

  // Handler: Compare Versions
  const handleCompareVersions = async () => {
    if (!datasetId || !selectedTarget) {
      showToast('Please select a target variable first.', 'info');
      return;
    }

    if (currentCandidate && currentCandidate.is_suitable === false) {
      showToast(`Cannot compare: "${selectedTarget}" is ineligible (${currentCandidate.suitability_reason || 'ID or high-cardinality text'}).`, 'error');
      return;
    }

    setIsComparing(true);
    try {
      const hyperparameters: Record<string, any> = {};
      if (modelType === 'decision_tree' || modelType === 'random_forest' || modelType === 'gradient_boosting') {
        hyperparameters.max_depth = isUnconstrainedDepth ? null : maxDepth;
      }
      if (modelType === 'knn') {
        hyperparameters.n_neighbors = knnNeighbors;
      }
      if (modelType === 'svm') {
        hyperparameters.kernel = svmKernel;
      }

      const res = await api.compareMLVersions(datasetId, {
        target_column: selectedTarget,
        model_type: modelType,
        base_version_number: selectedBaseVersion,
        target_version_number: activeVersionNumber,
        hyperparameters,
        selected_features: selectedFeatures
      });

      setCompareResult(res);
      // Synchronize trainResult so model insights card reflects this model's benchmark
      if (res.target_version) {
        setTrainResult(res.target_version);
      }
      showToast('Generated cross-version ML comparison!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Comparison failed. Ensure at least two versions exist.', 'error');
    } finally {
      setIsComparing(false);
    }
  };

  // Helper for Status Badge
  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'healthy_generalization':
        return {
          label: 'Healthy Generalization',
          bg: 'rgba(5, 150, 105, 0.15)',
          color: '#10B981',
          border: '1px solid rgba(5, 150, 105, 0.4)'
        };
      case 'moderate_overfitting':
        return {
          label: 'Moderate Overfitting',
          bg: 'rgba(217, 119, 6, 0.15)',
          color: '#F59E0B',
          border: '1px solid rgba(217, 119, 6, 0.4)'
        };
      case 'severe_overfitting':
        return {
          label: 'Severe Overfitting',
          bg: 'rgba(225, 29, 72, 0.15)',
          color: '#F43F5E',
          border: '1px solid rgba(225, 29, 72, 0.4)'
        };
      case 'underfitting':
        return {
          label: 'Underfitting',
          bg: 'rgba(2, 132, 199, 0.15)',
          color: '#38BDF8',
          border: '1px solid rgba(2, 132, 199, 0.4)'
        };
      default:
        return {
          label: 'Pending Training',
          bg: 'rgba(100, 116, 139, 0.15)',
          color: '#94A3B8',
          border: '1px solid rgba(100, 116, 139, 0.3)'
        };
    }
  };

  // Empty State: No Dataset
  if (!datasetId) {
    return (
      <div className="card" style={{ padding: '60px 40px', textAlign: 'center', maxWidth: '780px', margin: '40px auto' }}>
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '16px',
          background: 'rgba(37, 99, 235, 0.12)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px auto',
          border: '1px solid rgba(37, 99, 235, 0.3)'
        }}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--brand-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5" />
          </svg>
        </div>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '12px', color: '#FFFFFF' }}>
          Machine Learning Impact Studio
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '28px', maxWidth: '580px', margin: '0 auto 28px auto' }}>
          Experience first-hand how raw, uncleaned data (missing values, extreme outliers, duplicate rows) degrades model performance and causes severe overfitting. Train models directly, toggle input features in the What-If Sandbox, inspect confusion matrices, and benchmark raw vs. cleaned versions.
        </p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
          {onLoadSample && (
            <button onClick={onLoadSample} className="btn-primary" style={{ padding: '10px 22px', fontSize: '0.9rem' }}>
              Load SaaS Customer Churn Dataset (146 rows)
            </button>
          )}
        </div>
      </div>
    );
  }

  const statusBadge = getStatusBadge(trainResult?.metrics.overfitting_status);
  const confMatrix = trainResult?.metrics.confusion_matrix;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', paddingBottom: '40px' }}>
      {/* 1. Header & Configuration Card */}
      <div className="card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <div style={{
                width: '28px',
                height: '28px',
                borderRadius: '6px',
                background: 'var(--brand-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2">
                  <path d="M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5" />
                </svg>
              </div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#FFFFFF', margin: 0 }}>
                Machine Learning Impact Studio
              </h2>
              <span className="badge badge-numeric" style={{ fontSize: '0.72rem' }}>
                v{activeVersionNumber} Active
              </span>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0, maxWidth: '720px' }}>
              Train lightweight Scikit-Learn models in real-time, inspect overfitting gaps, observe neural loss convergence, test feature subsets in the What-If sandbox, and measure how data cleaning unlocks model generalization.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={() => handleTrain()}
              disabled={isTraining || !selectedTarget || selectedFeatures.length === 0 || currentCandidate?.is_suitable === false}
              className="btn-primary"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 20px',
                fontSize: '0.88rem',
                opacity: isTraining || selectedFeatures.length === 0 || currentCandidate?.is_suitable === false ? 0.6 : 1,
                cursor: currentCandidate?.is_suitable === false ? 'not-allowed' : 'pointer'
              }}
            >
              {isTraining ? (
                <>
                  <span className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }}></span>
                  Training Model...
                </>
              ) : (
                <>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                  Train & Analyze Model
                </>
              )}
            </button>
          </div>
        </div>

        {/* Control Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
          paddingTop: '16px',
          borderTop: '1px solid var(--border-subtle)'
        }}>
          {/* Target Variable Selector */}
          <div>
            <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              <span>Target Column</span>
              <span style={{ fontSize: '0.7rem', color: '#10B981', fontWeight: 500, textTransform: 'none' }}>
                Failsafe Protected
              </span>
            </label>
            <select
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
              className="input-select"
              style={{ width: '100%', padding: '8px 12px', fontSize: '0.85rem' }}
            >
              <optgroup label="✅ Recommended Prediction Targets">
                {safeCandidates.filter((c) => c.is_suitable !== false).map((c) => (
                  <option key={c.column} value={c.column}>
                    {c.column} ({c.task_type.toUpperCase()} • {c.data_type})
                  </option>
                ))}
              </optgroup>
              {safeCandidates.some((c) => c.is_suitable === false) && (
                <optgroup label="⚠️ Ineligible as Target (IDs / Names / Free Text)">
                  {safeCandidates.filter((c) => c.is_suitable === false).map((c) => (
                    <option key={c.column} value={c.column} disabled={true}>
                      {c.column} ({c.suitability_reason || 'Ineligible'})
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
            {currentCandidate && currentCandidate.is_suitable === false ? (
              <div style={{
                marginTop: '6px',
                padding: '6px 8px',
                borderRadius: '6px',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#F87171',
                fontSize: '0.73rem',
                lineHeight: 1.3
              }}>
                ⚠️ <strong>Ineligible Target:</strong> {currentCandidate.suitability_reason || 'Identifiers or high-cardinality text cannot be predicted.'}
              </div>
            ) : currentCandidate ? (
              <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{
                  fontSize: '0.7rem',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: currentCandidate.task_type === 'regression' ? 'rgba(2, 132, 199, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                  color: currentCandidate.task_type === 'regression' ? '#38BDF8' : '#34D399',
                  fontWeight: 600,
                  textTransform: 'uppercase'
                }}>
                  {currentCandidate.task_type}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {currentCandidate.unique_values} unique values
                </span>
              </div>
            ) : null}
          </div>

          {/* Model Type Selector */}
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Model Architecture
            </label>
            <select
              value={modelType}
              onChange={(e) => {
                const newType = e.target.value;
                setModelType(newType);
                if (selectedTarget && selectedFeatures.length > 0) {
                  handleTrain(newType);
                }
              }}
              className="input-select"
              style={{ width: '100%', padding: '8px 12px', fontSize: '0.85rem' }}
            >
              <option value="decision_tree">Decision Tree (Overfitting Demo)</option>
              <option value="random_forest">Random Forest (Bagging Ensemble)</option>
              <option value="gradient_boosting">Gradient Boosting (Boosting Ensemble)</option>
              <option value="linear">
                {taskType === 'regression' ? 'Linear Ridge Regression' : 'Logistic Regression'}
              </option>
              <option value="knn">K-Nearest Neighbors (Distance-Based)</option>
              <option value="svm">Support Vector Machine (Maximum-Margin)</option>
              <option value="neural_net">Neural Network (MLP Backprop)</option>
            </select>
            <span style={{ fontSize: '0.73rem', color: 'var(--text-muted)', display: 'block', marginTop: '6px' }}>
              {modelType === 'decision_tree' && 'Sensitive to duplicate data & outliers; demonstrates tree memorization'}
              {modelType === 'linear' && 'Baseline linear model; sensitive to extreme outlier leverage'}
              {modelType === 'random_forest' && 'Bagging ensemble reduces variance across multiple decorrelated trees'}
              {modelType === 'gradient_boosting' && 'Sequential boosting; minimizes residual deviance step-by-step'}
              {modelType === 'knn' && 'Instance distance learner; very sensitive to unscaled features & noise'}
              {modelType === 'svm' && 'Maximizes separating margin; boundary vectors vulnerable to outlier points'}
              {modelType === 'neural_net' && 'Multi-layer backpropagation loss curve'}
            </span>
          </div>

          {/* Decision Tree / Ensemble Max Depth Slider */}
          {(modelType === 'decision_tree' || modelType === 'random_forest' || modelType === 'gradient_boosting') && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Tree Depth
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={isUnconstrainedDepth}
                    onChange={(e) => setIsUnconstrainedDepth(e.target.checked)}
                  />
                  Unconstrained (Max)
                </label>
              </div>

              {!isUnconstrainedDepth ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <input
                    type="range"
                    min="1"
                    max="15"
                    step="1"
                    value={maxDepth || 3}
                    onChange={(e) => setMaxDepth(parseInt(e.target.value))}
                    style={{ flex: 1, accentColor: 'var(--brand-primary)' }}
                  />
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, minWidth: '24px', color: '#FFFFFF' }}>
                    {maxDepth}
                  </span>
                </div>
              ) : (
                <div style={{ fontSize: '0.78rem', color: '#F43F5E', fontWeight: 500, padding: '6px 0' }}>
                  ⚠️ Unlimited depth: Model will fully memorize training duplicates.
                </div>
              )}
            </div>
          )}

          {/* KNN Hyperparameter: K Neighbors */}
          {modelType === 'knn' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Neighbors (K)
                </label>
                <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--brand-primary)' }}>
                  {knnNeighbors} Neighbors
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="15"
                step="1"
                value={knnNeighbors}
                onChange={(e) => setKnnNeighbors(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--brand-primary)' }}
              />
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block', marginTop: '4px' }}>
                Low K (e.g. 1-2) overfits to noise; Higher K yields smoother decision boundaries.
              </span>
            </div>
          )}

          {/* SVM Hyperparameter: Kernel Function */}
          {modelType === 'svm' && (
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Kernel Function
              </label>
              <select
                value={svmKernel}
                onChange={(e) => setSvmKernel(e.target.value)}
                className="input-select"
                style={{ width: '100%', padding: '8px 12px', fontSize: '0.85rem' }}
              >
                <option value="rbf">RBF (Radial Basis - Non-Linear)</option>
                <option value="linear">Linear (Flat Hyperplane)</option>
                <option value="poly">Polynomial (Degree 3)</option>
              </select>
            </div>
          )}

          {/* Test Split Slider */}
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Test Split: {(testSize * 100).toFixed(0)}%
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <input
                type="range"
                min="0.1"
                max="0.4"
                step="0.05"
                value={testSize}
                onChange={(e) => setTestSize(parseFloat(e.target.value))}
                style={{ flex: 1, accentColor: 'var(--brand-primary)' }}
              />
              <span style={{ fontSize: '0.85rem', fontWeight: 600, minWidth: '36px', color: '#FFFFFF' }}>
                {(testSize * 100).toFixed(0)}%
              </span>
            </div>
            <span style={{ fontSize: '0.73rem', color: 'var(--text-muted)', display: 'block', marginTop: '6px' }}>
              {100 - Math.round(testSize * 100)}% Train / {Math.round(testSize * 100)}% Validation
            </span>
          </div>
        </div>

        {/* Feature Selector & What-If Sandbox (Collapsible Section) */}
        <div style={{
          marginTop: '18px',
          paddingTop: '16px',
          borderTop: '1px solid var(--border-subtle)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <button
              onClick={() => setIsFeatureSelectorOpen(!isFeatureSelectorOpen)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-primary)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                padding: '4px 0',
                fontSize: '0.86rem',
                fontWeight: 600
              }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                style={{
                  transform: isFeatureSelectorOpen ? 'rotate(90deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s ease'
                }}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
              <span>Feature Selection & What-If Sandbox</span>
              <span style={{
                fontSize: '0.72rem',
                padding: '2px 8px',
                borderRadius: '4px',
                background: selectedFeatures.length === availableFeatures.length ? 'rgba(37, 99, 235, 0.2)' : 'rgba(217, 119, 6, 0.2)',
                color: selectedFeatures.length === availableFeatures.length ? '#60A5FA' : '#FBBF24',
                fontWeight: 600
              }}>
                {selectedFeatures.length} / {availableFeatures.length} Features Active
              </span>
            </button>

            {isFeatureSelectorOpen && (
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                  onClick={selectAllFeatures}
                  className="btn-secondary"
                  style={{ padding: '3px 10px', fontSize: '0.74rem' }}
                >
                  Select All
                </button>
                <button
                  onClick={deselectAllFeatures}
                  className="btn-secondary"
                  style={{ padding: '3px 10px', fontSize: '0.74rem' }}
                >
                  Reset (1 Feature)
                </button>
              </div>
            )}
          </div>

          {isFeatureSelectorOpen && (
            <div style={{
              marginTop: '14px',
              padding: '14px 16px',
              background: 'rgba(0, 0, 0, 0.2)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)'
            }}>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: 1.5 }}>
                💡 <strong>Feature Impact Sandbox:</strong> Check or uncheck columns to test how removing noisy, redundant, or misleading features improves real-world model accuracy and prevents memorizing noise.
              </p>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                gap: '10px',
                maxHeight: '220px',
                overflowY: 'auto',
                paddingRight: '6px'
              }}>
                {availableFeatures.map((cand) => {
                  const isChecked = selectedFeatures.includes(cand.column);
                  return (
                    <label
                      key={cand.column}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '6px 10px',
                        borderRadius: 'var(--radius-sm)',
                        background: isChecked ? 'rgba(37, 99, 235, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                        border: isChecked ? '1px solid rgba(37, 99, 235, 0.4)' : '1px solid var(--border-subtle)',
                        cursor: 'pointer',
                        userSelect: 'none',
                        transition: 'background 0.15s ease'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleFeature(cand.column)}
                        style={{ accentColor: 'var(--brand-primary)', cursor: 'pointer' }}
                      />
                      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                        <span style={{ fontSize: '0.8rem', color: isChecked ? '#FFFFFF' : 'var(--text-secondary)', fontWeight: isChecked ? 600 : 400 }}>
                          {cand.column}
                        </span>
                      </div>
                      <span style={{
                        fontSize: '0.65rem',
                        color: 'var(--text-muted)',
                        textTransform: 'uppercase',
                        padding: '1px 4px',
                        borderRadius: '3px',
                        background: 'rgba(255,255,255,0.05)'
                      }}>
                        {cand.data_type.startsWith('int') || cand.data_type.startsWith('float') ? 'num' : 'cat'}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 2. Training Results Section */}
      {trainResult ? (
        <>
          {/* Pedagogical Generalization Banner */}
          <div style={{
            background: statusBadge.bg,
            border: statusBadge.border,
            borderRadius: 'var(--radius-md)',
            padding: '18px 22px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '16px'
          }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.06)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: statusBadge.color,
              flexShrink: 0
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.6px',
                  color: statusBadge.color
                }}>
                  {statusBadge.label}
                </span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  • Gap: {(trainResult.metrics.overfitting_score * 100).toFixed(1)}%
                </span>
              </div>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', lineHeight: 1.5, margin: 0 }}>
                {trainResult.metrics.overfitting_explanation}
              </p>
            </div>
          </div>

          {/* 4 Scorecard KPI Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px'
          }}>
            {/* Train Score Card */}
            <div className="card" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.5px', marginBottom: '8px' }}>
                Training Score ({taskType === 'regression' ? 'R²' : 'Accuracy'})
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.5px' }}>
                {(trainResult.metrics.train_score * 100).toFixed(1)}%
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Fit on seen training records
              </div>
            </div>

            {/* Test Score Card */}
            <div className="card" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.5px', marginBottom: '8px' }}>
                Test Score ({taskType === 'regression' ? 'R²' : 'Accuracy'})
              </div>
              <div style={{
                fontSize: '1.8rem',
                fontWeight: 700,
                color: trainResult.metrics.test_score >= 0.7 ? '#10B981' : trainResult.metrics.test_score >= 0.4 ? '#F59E0B' : '#F43F5E',
                letterSpacing: '-0.5px'
              }}>
                {(trainResult.metrics.test_score * 100).toFixed(1)}%
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                True generalization on unseen holdout
              </div>
            </div>

            {/* Generalization Gap Card */}
            <div className="card" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.5px', marginBottom: '8px' }}>
                Overfitting Gap (Δ)
              </div>
              <div style={{
                fontSize: '1.8rem',
                fontWeight: 700,
                color: trainResult.metrics.overfitting_score <= 0.12 ? '#10B981' : trainResult.metrics.overfitting_score <= 0.25 ? '#F59E0B' : '#F43F5E',
                letterSpacing: '-0.5px'
              }}>
                {(trainResult.metrics.overfitting_score * 100).toFixed(1)}%
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Train vs Test divergence
              </div>
            </div>

            {/* Secondary Metric Card */}
            <div className="card" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.5px', marginBottom: '8px' }}>
                {taskType === 'regression' ? 'Root Mean Squared Error (RMSE)' : 'F1-Score (Macro)'}
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.5px' }}>
                {taskType === 'regression'
                  ? (trainResult.metrics.regression_metrics?.rmse.toFixed(3) ?? 'N/A')
                  : `${((trainResult.metrics.classification_metrics?.f1_score || 0) * 100).toFixed(1)}%`}
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                {taskType === 'regression'
                  ? `MAE: ${trainResult.metrics.regression_metrics?.mae.toFixed(3) ?? 'N/A'}`
                  : `Precision: ${((trainResult.metrics.classification_metrics?.precision || 0) * 100).toFixed(1)}%`}
              </div>
            </div>
          </div>

          {/* 3. Interactive Pedagogical Visualizations */}
          <div className="card" style={{ padding: '24px' }}>
            {/* Visualizer Nav Tabs */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px', marginBottom: '20px' }}>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  onClick={() => setActiveVizTab('overfitting')}
                  style={{
                    background: activeVizTab === 'overfitting' ? 'var(--brand-primary)' : 'transparent',
                    color: activeVizTab === 'overfitting' ? '#FFFFFF' : 'var(--text-secondary)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    padding: '6px 14px',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Overfitting Diagnostics
                </button>

                {confMatrix && (
                  <button
                    onClick={() => setActiveVizTab('confusion_matrix')}
                    style={{
                      background: activeVizTab === 'confusion_matrix' ? 'var(--brand-primary)' : 'transparent',
                      color: activeVizTab === 'confusion_matrix' ? '#FFFFFF' : 'var(--text-secondary)',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      padding: '6px 14px',
                      fontSize: '0.82rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    Confusion Matrix Heatmap
                  </button>
                )}

                {trainResult.loss_curve && trainResult.loss_curve.length > 0 && (
                  <button
                    onClick={() => setActiveVizTab('loss')}
                    style={{
                      background: activeVizTab === 'loss' ? 'var(--brand-primary)' : 'transparent',
                      color: activeVizTab === 'loss' ? '#FFFFFF' : 'var(--text-secondary)',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      padding: '6px 14px',
                      fontSize: '0.82rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    Loss Curve / Gradient Descent
                  </button>
                )}

                <button
                  onClick={() => setActiveVizTab('actual_vs_pred')}
                  style={{
                    background: activeVizTab === 'actual_vs_pred' ? 'var(--brand-primary)' : 'transparent',
                    color: activeVizTab === 'actual_vs_pred' ? '#FFFFFF' : 'var(--text-secondary)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    padding: '6px 14px',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  {taskType === 'regression' ? 'Actual vs. Predicted Scatter' : 'Prediction Distribution'}
                </button>

                <button
                  onClick={() => setActiveVizTab('features')}
                  style={{
                    background: activeVizTab === 'features' ? 'var(--brand-primary)' : 'transparent',
                    color: activeVizTab === 'features' ? '#FFFFFF' : 'var(--text-secondary)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    padding: '6px 14px',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Feature Importance
                </button>

                <button
                  onClick={() => setActiveVizTab('what_if')}
                  style={{
                    background: activeVizTab === 'what_if' ? 'var(--brand-primary)' : 'transparent',
                    color: activeVizTab === 'what_if' ? '#FFFFFF' : 'var(--text-secondary)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    padding: '6px 14px',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <span>⚡ What-If Simulator</span>
                  <span style={{ fontSize: '0.65rem', background: 'rgba(16, 185, 129, 0.2)', color: '#10B981', padding: '1px 5px', borderRadius: '4px' }}>Live</span>
                </button>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={handleExportCode}
                  disabled={isExportingCode}
                  className="btn-secondary"
                  title="Download standalone Python inference script"
                  style={{ fontSize: '0.78rem', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  {isExportingCode ? 'Exporting...' : 'Export Python Code'}
                </button>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  {trainResult.total_samples} samples • {trainResult.feature_count} features active
                </span>
              </div>
            </div>

            {/* TAB: Overfitting Diagnostics Gauge */}
            {activeVizTab === 'overfitting' && (
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '8px' }}>
                  Generalization Diagnostics: Training vs. Holdout Validation
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '24px', maxWidth: '700px' }}>
                  A healthy machine learning model maintains close proximity between training score and validation score. Large divergence indicates that the model memorized idiosyncrasies, duplicate rows, or outlier noise rather than discovering transferable patterns.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '650px' }}>
                  {/* Train Score Bar */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '6px' }}>
                      <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Training Score</span>
                      <span style={{ color: '#FFFFFF', fontWeight: 600 }}>{(trainResult.metrics.train_score * 100).toFixed(1)}%</span>
                    </div>
                    <div style={{ height: '14px', background: 'rgba(255,255,255,0.06)', borderRadius: '7px', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%',
                        width: `${Math.min(100, Math.max(0, trainResult.metrics.train_score * 100))}%`,
                        background: 'var(--brand-primary)',
                        borderRadius: '7px',
                        transition: 'width 0.4s ease'
                      }} />
                    </div>
                  </div>

                  {/* Test Score Bar */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '6px' }}>
                      <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Validation Holdout Score</span>
                      <span style={{ color: statusBadge.color, fontWeight: 600 }}>{(trainResult.metrics.test_score * 100).toFixed(1)}%</span>
                    </div>
                    <div style={{ height: '14px', background: 'rgba(255,255,255,0.06)', borderRadius: '7px', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%',
                        width: `${Math.min(100, Math.max(0, trainResult.metrics.test_score * 100))}%`,
                        background: statusBadge.color,
                        borderRadius: '7px',
                        transition: 'width 0.4s ease'
                      }} />
                    </div>
                  </div>

                  {/* Overfitting Gap Highlighter */}
                  <div style={{
                    padding: '14px 18px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Generalization Gap (Train − Test):</span>
                    <span style={{ fontSize: '0.92rem', fontWeight: 700, color: statusBadge.color }}>
                      {(trainResult.metrics.overfitting_score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* TAB: Confusion Matrix Heatmap (Classification) */}
            {activeVizTab === 'confusion_matrix' && confMatrix && (
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '6px' }}>
                  Holdout Confusion Matrix Heatmap (Actual vs. Predicted)
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '20px', maxWidth: '720px' }}>
                  Shows where classification predictions align with ground-truth labels. Diagonal cells indicate correct classifications (True Positives / True Negatives), while off-diagonal cells highlight misclassifications caused by ambiguous features or noisy samples.
                </p>

                {(() => {
                  const maxCellVal = Math.max(...confMatrix.matrix.flatMap((row) => row), 1);
                  return (
                    <div style={{ maxWidth: '640px', overflowX: 'auto', paddingBottom: '10px' }}>
                      {/* Matrix Grid */}
                      <div style={{ display: 'inline-block', minWidth: '320px' }}>
                        {/* Column Header Label */}
                        <div style={{ textAlign: 'center', fontSize: '0.78rem', color: 'var(--brand-primary)', fontWeight: 600, marginBottom: '8px', letterSpacing: '0.5px' }}>
                          PREDICTED CLASS →
                        </div>

                        {/* Top Headers */}
                        <div style={{ display: 'grid', gridTemplateColumns: `100px repeat(${confMatrix.labels.length}, minmax(70px, 1fr))`, gap: '6px', marginBottom: '6px' }}>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textAlign: 'right', paddingRight: '8px', alignSelf: 'center' }}>
                            ACTUAL ↓
                          </div>
                          {confMatrix.labels.map((lbl, idx) => (
                            <div key={idx} style={{ textAlign: 'center', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.03)', padding: '6px 4px', borderRadius: '4px' }}>
                              Class {lbl}
                            </div>
                          ))}
                        </div>

                        {/* Rows */}
                        {confMatrix.matrix.map((row, rIdx) => (
                          <div key={rIdx} style={{ display: 'grid', gridTemplateColumns: `100px repeat(${confMatrix.labels.length}, minmax(70px, 1fr))`, gap: '6px', marginBottom: '6px' }}>
                            {/* Row Header */}
                            <div style={{ textAlign: 'right', paddingRight: '8px', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', alignSelf: 'center' }}>
                              Class {confMatrix.labels[rIdx]}
                            </div>

                            {/* Cells */}
                            {row.map((val, cIdx) => {
                              const isDiagonal = rIdx === cIdx;
                              const intensity = val / maxCellVal;
                              const bg = isDiagonal
                                ? `rgba(16, 185, 129, ${0.15 + intensity * 0.65})`
                                : val > 0
                                  ? `rgba(244, 63, 94, ${0.12 + intensity * 0.55})`
                                  : 'rgba(255, 255, 255, 0.02)';
                              const border = isDiagonal
                                ? '1px solid rgba(16, 185, 129, 0.4)'
                                : val > 0
                                  ? '1px solid rgba(244, 63, 94, 0.35)'
                                  : '1px solid var(--border-subtle)';
                              const textColor = isDiagonal ? '#34D399' : val > 0 ? '#F43F5E' : 'var(--text-muted)';

                              return (
                                <div
                                  key={cIdx}
                                  title={`Actual Class ${confMatrix.labels[rIdx]} → Predicted Class ${confMatrix.labels[cIdx]}: ${val} samples`}
                                  style={{
                                    background: bg,
                                    border: border,
                                    borderRadius: '6px',
                                    padding: '12px 6px',
                                    textAlign: 'center',
                                    cursor: 'default',
                                    transition: 'all 0.15s ease'
                                  }}
                                >
                                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: textColor }}>
                                    {val}
                                  </div>
                                  <div style={{ fontSize: '0.66rem', color: isDiagonal ? '#A7F3D0' : val > 0 ? '#FECDD3' : 'var(--text-muted)' }}>
                                    {isDiagonal ? 'Match' : val > 0 ? 'Error' : 'None'}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ))}
                      </div>

                      {/* Legend */}
                      <div style={{ marginTop: '16px', display: 'flex', gap: '16px', alignItems: 'center', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: 'rgba(16, 185, 129, 0.6)' }} />
                          <span>Correct Predictions (Diagonal)</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: 'rgba(244, 63, 94, 0.6)' }} />
                          <span>Misclassifications (Off-Diagonal)</span>
                        </div>
                        <span style={{ color: 'var(--text-muted)' }}>
                          • Total Test Samples: {confMatrix.total_samples}
                        </span>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* TAB: Loss Curve / Gradient Descent */}
            {activeVizTab === 'loss' && trainResult.loss_curve && (
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '6px' }}>
                  Neural Network Gradient Descent: Loss vs. Training Epochs
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '18px' }}>
                  Monitors error reduction during backpropagation. Clean data produces smooth, monotonic loss minimization, whereas duplicate rows and extreme unscaled outliers cause erratic spikes or premature plateaus.
                </p>

                {/* SVG Loss Curve */}
                <div style={{ width: '100%', height: '260px', position: 'relative' }}>
                  <svg width="100%" height="100%" viewBox="0 0 600 240" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
                    <defs>
                      <linearGradient id="lossGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--brand-primary)" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="var(--brand-primary)" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>

                    {/* Grid lines */}
                    <line x1="40" y1="20" x2="580" y2="20" stroke="var(--border-subtle)" strokeDasharray="3 3" />
                    <line x1="40" y1="110" x2="580" y2="110" stroke="var(--border-subtle)" strokeDasharray="3 3" />
                    <line x1="40" y1="200" x2="580" y2="200" stroke="var(--border-subtle)" />

                    {/* Y-axis labels */}
                    <text x="32" y="24" fill="var(--text-muted)" fontSize="10" textAnchor="end">
                      {Math.max(...trainResult.loss_curve.map((p) => p.loss)).toFixed(2)}
                    </text>
                    <text x="32" y="204" fill="var(--text-muted)" fontSize="10" textAnchor="end">
                      {Math.min(...trainResult.loss_curve.map((p) => p.loss)).toFixed(2)}
                    </text>

                    {/* Generate SVG Path */}
                    {(() => {
                      const points = trainResult.loss_curve;
                      const maxLoss = Math.max(...points.map((p) => p.loss)) || 1;
                      const minLoss = Math.min(...points.map((p) => p.loss)) || 0;
                      const lossRange = maxLoss - minLoss || 1;

                      const svgPoints = points.map((p, idx) => {
                        const x = 40 + (idx / Math.max(1, points.length - 1)) * 540;
                        const y = 200 - ((p.loss - minLoss) / lossRange) * 180;
                        return { x, y, ...p };
                      });

                      const pathD = svgPoints.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`, '');
                      const areaD = `${pathD} L ${svgPoints[svgPoints.length - 1].x} 200 L 40 200 Z`;

                      return (
                        <>
                          <path d={areaD} fill="url(#lossGradient)" />
                          <path d={pathD} fill="none" stroke="var(--brand-primary)" strokeWidth="2.5" strokeLinecap="round" />
                          {svgPoints.filter((_, i) => i % Math.ceil(svgPoints.length / 10) === 0 || i === svgPoints.length - 1).map((p, i) => (
                            <circle key={i} cx={p.x} cy={p.y} r="3.5" fill="#FFFFFF" stroke="var(--brand-primary)" strokeWidth="2" />
                          ))}
                        </>
                      );
                    })()}

                    {/* X-axis label */}
                    <text x="310" y="225" fill="var(--text-muted)" fontSize="11" textAnchor="middle">
                      Training Epochs (Total: {trainResult.loss_curve.length})
                    </text>
                  </svg>
                </div>
              </div>
            )}

            {/* TAB: Actual vs. Predicted Scatter */}
            {activeVizTab === 'actual_vs_pred' && (
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '6px' }}>
                  {taskType === 'regression' ? 'Actual vs. Predicted Scatter (Test Samples)' : 'Prediction Accuracy Distribution'}
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '18px' }}>
                  {taskType === 'regression'
                    ? 'Points hugging the dashed 45° diagonal line represent accurate predictions. Deviations and outlier clusters highlight modeling errors.'
                    : 'Shows how holdout samples are categorized relative to ground-truth labels.'}
                </p>

                {taskType === 'regression' && trainResult.predictions.length > 0 ? (
                  <div style={{ width: '100%', height: '260px' }}>
                    <svg width="100%" height="100%" viewBox="0 0 600 240" preserveAspectRatio="none">
                      {/* 45 degree ideal diagonal */}
                      <line x1="50" y1="190" x2="570" y2="30" stroke="rgba(255,255,255,0.2)" strokeDasharray="4 4" strokeWidth="1.5" />

                      {/* Bounding box axes */}
                      <line x1="50" y1="20" x2="50" y2="200" stroke="var(--border-subtle)" />
                      <line x1="50" y1="200" x2="580" y2="200" stroke="var(--border-subtle)" />

                      {(() => {
                        const pts = trainResult.predictions;
                        const allVals = pts.flatMap((p) => [p.actual, p.predicted]);
                        const minVal = Math.min(...allVals);
                        const maxVal = Math.max(...allVals);
                        const range = maxVal - minVal || 1;

                        return (
                          <>
                            {pts.map((p, idx) => {
                              const x = 50 + ((p.actual - minVal) / range) * 520;
                              const y = 200 - ((p.predicted - minVal) / range) * 170;
                              return (
                                <circle
                                  key={idx}
                                  cx={x}
                                  cy={y}
                                  r="4"
                                  fill="rgba(56, 189, 248, 0.75)"
                                  stroke="#0284C7"
                                  strokeWidth="1"
                                />
                              );
                            })}
                            <text x="315" y="225" fill="var(--text-muted)" fontSize="11" textAnchor="middle">
                              Actual Values
                            </text>
                            <text x="20" y="115" fill="var(--text-muted)" fontSize="11" transform="rotate(-90 20 115)" textAnchor="middle">
                              Predicted
                            </text>
                          </>
                        );
                      })()}
                    </svg>
                  </div>
                ) : (
                  <div style={{ padding: '20px', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Total test predictions evaluated: <strong style={{ color: '#FFFFFF' }}>{trainResult.predictions.length}</strong>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB: Feature Importance */}
            {activeVizTab === 'features' && (
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '6px' }}>
                  Model Feature Importance / Coefficients
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '18px' }}>
                  Relative feature weight contributions during model decision-making. Preprocessing features through imputation and scaling ensures unskewed, meaningful feature attribution.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '700px' }}>
                  {trainResult.feature_importance.slice(0, 10).map((item, idx) => (
                    <div key={idx}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                        <span style={{ color: '#FFFFFF', fontWeight: 500 }}>{item.feature}</span>
                        <span style={{ color: 'var(--text-muted)' }}>{(item.importance * 100).toFixed(1)}%</span>
                      </div>
                      <div style={{ height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: `${Math.min(100, Math.max(0, item.importance * 100))}%`,
                          background: 'var(--accent-cyan)',
                          borderRadius: '4px'
                        }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB: What-If Live Simulator */}
            {activeVizTab === 'what_if' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
                  <div>
                    <h4 style={{ fontSize: '0.98rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '4px' }}>
                      Interactive What-If Live Prediction Simulator
                    </h4>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0, maxWidth: '680px' }}>
                      Simulate real-time model inference using your trained Scikit-Learn pipeline. Tweak numeric sliders or category values below to observe how input adjustments immediately change predictions.
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      if (trainResult.feature_specs) {
                        const defaults: Record<string, any> = {};
                        trainResult.feature_specs.forEach((f) => { defaults[f.name] = f.default_val; });
                        setSimulatorInputs(defaults);
                        handleRunPrediction(defaults);
                      }
                    }}
                    className="btn-secondary"
                    style={{ fontSize: '0.76rem', padding: '5px 12px' }}
                  >
                    Reset to Means / Medians
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1.4fr) minmax(280px, 1fr)', gap: '24px', alignItems: 'start' }}>
                  {/* Left: Input Controls */}
                  <div style={{
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '18px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '16px',
                    maxHeight: '480px',
                    overflowY: 'auto'
                  }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)' }}>
                      Adjust Feature Inputs ({trainResult.feature_specs?.length || 0} features)
                    </div>

                    {(!trainResult.feature_specs || trainResult.feature_specs.length === 0) ? (
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                        No feature specifications available for this model.
                      </div>
                    ) : (
                      trainResult.feature_specs.map((spec) => {
                        const currentValue = simulatorInputs[spec.name] ?? spec.default_val;
                        if (spec.dtype === 'numeric') {
                          const min = spec.min_val ?? 0;
                          const max = spec.max_val ?? 100;
                          const step = (max - min > 10 ? 1 : 0.1);
                          return (
                            <div key={spec.name} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <label style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                                  {spec.name}
                                </label>
                                <span style={{
                                  fontSize: '0.82rem',
                                  fontWeight: 600,
                                  color: 'var(--brand-primary)',
                                  background: 'rgba(37, 99, 235, 0.12)',
                                  padding: '2px 8px',
                                  borderRadius: '4px'
                                }}>
                                  {typeof currentValue === 'number' ? (Number.isInteger(currentValue) ? currentValue : currentValue.toFixed(2)) : currentValue}
                                </span>
                              </div>
                              <input
                                type="range"
                                min={min}
                                max={max}
                                step={step}
                                value={currentValue}
                                onChange={(e) => handleSimulatorChange(spec.name, parseFloat(e.target.value))}
                                style={{ accentColor: 'var(--brand-primary)', cursor: 'pointer' }}
                              />
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                                <span>Min: {min}</span>
                                <span>Mean: {typeof spec.default_val === 'number' ? spec.default_val.toFixed(1) : spec.default_val}</span>
                                <span>Max: {max}</span>
                              </div>
                            </div>
                          );
                        } else {
                          return (
                            <div key={spec.name} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <label style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                                  {spec.name}
                                </label>
                                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Categorical</span>
                              </div>
                              <select
                                value={currentValue}
                                onChange={(e) => handleSimulatorChange(spec.name, e.target.value)}
                                className="input-select"
                                style={{ padding: '6px 10px', fontSize: '0.82rem' }}
                              >
                                {(spec.options || []).map((cat: string) => (
                                  <option key={cat} value={cat}>
                                    {cat}
                                  </option>
                                ))}
                              </select>
                            </div>
                          );
                        }
                      })
                    )}
                  </div>

                  {/* Right: Live Prediction Output Card */}
                  <div style={{
                    background: 'linear-gradient(145deg, rgba(37, 99, 235, 0.08) 0%, rgba(16, 185, 129, 0.04) 100%)',
                    border: '1px solid rgba(37, 99, 235, 0.3)',
                    borderRadius: 'var(--radius-md)',
                    padding: '24px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '18px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)', fontWeight: 600 }}>
                        Target: {selectedTarget}
                      </span>
                      <span style={{
                        fontSize: '0.72rem',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        background: 'rgba(16, 185, 129, 0.15)',
                        color: '#10B981',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}>
                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
                        {isPredicting ? 'Inferring...' : '< 3ms In-Memory'}
                      </span>
                    </div>

                    {predictionResult ? (
                      <div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                          Predicted Outcome
                        </div>
                        <div style={{
                          fontSize: '2.2rem',
                          fontWeight: 800,
                          color: (predictionResult.predicted_class === '1' || predictionResult.predicted_class === 'Yes' || predictionResult.predicted_class === 'True')
                            ? '#F43F5E'
                            : (predictionResult.predicted_class === '0' || predictionResult.predicted_class === 'No' || predictionResult.predicted_class === 'False')
                            ? '#10B981'
                            : '#60A5FA',
                          letterSpacing: '-0.5px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px'
                        }}>
                          {taskType === 'regression'
                            ? (predictionResult.predicted_value !== undefined ? predictionResult.predicted_value.toFixed(2) : 'N/A')
                            : (predictionResult.predicted_class ?? 'N/A')}
                        </div>

                        {predictionResult.probabilities && (
                          <div style={{ marginTop: '16px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                              <span>Class Probabilities</span>
                              {predictionResult.probabilities['1'] !== undefined && (
                                <span style={{ fontWeight: 600, color: '#FFFFFF' }}>
                                  {(predictionResult.probabilities['1'] * 100).toFixed(1)}% Positive
                                </span>
                              )}
                            </div>
                            <div style={{ height: '10px', background: 'rgba(255,255,255,0.08)', borderRadius: '6px', overflow: 'hidden', display: 'flex' }}>
                              {Object.entries(predictionResult.probabilities).map(([cls, prob], idx) => (
                                <div
                                  key={cls}
                                  title={`Class ${cls}: ${(prob * 100).toFixed(1)}%`}
                                  style={{
                                    height: '100%',
                                    width: `${prob * 100}%`,
                                    background: idx === 0 ? '#10B981' : idx === 1 ? '#F43F5E' : '#38BDF8',
                                    transition: 'width 0.2s ease'
                                  }}
                                />
                              ))}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                              {Object.entries(predictionResult.probabilities).map(([cls, prob]) => (
                                <span key={cls}>Class {cls}: {(prob * 100).toFixed(0)}%</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        Adjust inputs on the left to simulate prediction.
                      </div>
                    )}

                    <div style={{
                      marginTop: '8px',
                      padding: '12px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'rgba(0,0,0,0.2)',
                      fontSize: '0.78rem',
                      color: 'var(--text-secondary)',
                      lineHeight: 1.4
                    }}>
                      💡 <strong>Model Interpretability Note:</strong> Because data cleaning eliminated outlier skews and imputed missing values before training, the decision boundaries remain stable and realistic.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 4. Educational Takeaways Card */}
          {trainResult.educational_takeaways && trainResult.educational_takeaways.length > 0 && (
            <div className="card" style={{ padding: '20px 24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--brand-primary)" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                <h4 style={{ fontSize: '0.92rem', fontWeight: 600, color: '#FFFFFF', margin: 0 }}>
                  Key Takeaways & Model Insights
                </h4>
              </div>
              <ul style={{ paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {trainResult.educational_takeaways.map((takeaway, idx) => (
                  <li key={idx} style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    {takeaway}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 5. Cross-Version Comparison Benchmark ("Before vs. After Cleaning") */}
          <div className="card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '4px' }}>
                  Cross-Version Generalization Benchmark
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.83rem', margin: 0 }}>
                  Quantify the exact model performance gain (+R², +Accuracy, reduced overfitting gap) achieved between the uncleaned baseline and your preprocessed dataset version.
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Compare against:</label>
                <select
                  value={selectedBaseVersion}
                  onChange={(e) => setSelectedBaseVersion(parseInt(e.target.value))}
                  className="input-select"
                  style={{ padding: '6px 12px', fontSize: '0.82rem' }}
                >
                  {versions.map((v) => (
                    <option key={v.version_number} value={v.version_number}>
                      v{v.version_number} {v.version_number === 1 ? '(Raw Baseline)' : ''}
                    </option>
                  ))}
                </select>

                <button
                  onClick={handleCompareVersions}
                  disabled={isComparing || versions.length < 2}
                  className="btn-secondary"
                  style={{ padding: '7px 16px', fontSize: '0.82rem' }}
                >
                  {isComparing ? 'Benchmarking...' : 'Run Benchmark'}
                </button>
              </div>
            </div>

            {/* Comparison Results Card */}
            {compareResult && (
              <div style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '20px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                  <div style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    background: compareResult.score_delta >= 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                    color: compareResult.score_delta >= 0 ? '#34D399' : '#F43F5E',
                    fontWeight: 700,
                    fontSize: '0.85rem'
                  }}>
                    {compareResult.score_delta >= 0 ? '+' : ''}{(compareResult.score_delta * 100).toFixed(1)}% Performance Gain
                  </div>
                  <div style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    background: compareResult.overfitting_gap_reduction >= 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                    color: compareResult.overfitting_gap_reduction >= 0 ? '#34D399' : '#F43F5E',
                    fontWeight: 600,
                    fontSize: '0.82rem'
                  }}>
                    {compareResult.overfitting_gap_reduction >= 0 ? '−' : '+'}
                    {(Math.abs(compareResult.overfitting_gap_reduction) * 100).toFixed(1)}% Overfitting Reduction
                  </div>
                </div>

                <p style={{ fontSize: '0.86rem', color: 'var(--text-primary)', lineHeight: 1.5, marginBottom: '18px' }}>
                  {compareResult.summary}
                </p>

                {/* Side-by-Side Comparison Table */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div style={{ padding: '14px', background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                      Baseline v{compareResult.base_version.version_number}
                    </div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF' }}>
                      {(compareResult.base_version.metrics.test_score * 100).toFixed(1)}% Test Score
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      Overfitting Gap: {(compareResult.base_version.metrics.overfitting_score * 100).toFixed(1)}%
                    </div>
                  </div>

                  <div style={{ padding: '14px', background: 'rgba(37, 99, 235, 0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(37, 99, 235, 0.3)' }}>
                    <div style={{ fontSize: '0.74rem', color: 'var(--brand-primary)', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 600 }}>
                      Cleaned v{compareResult.target_version.version_number} (Active)
                    </div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF' }}>
                      {(compareResult.target_version.metrics.test_score * 100).toFixed(1)}% Test Score
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#10B981', marginTop: '4px' }}>
                      Overfitting Gap: {(compareResult.target_version.metrics.overfitting_score * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      ) : (
        /* Empty Prompt before first training */
        <div className="card" style={{ padding: '48px 24px', textAlign: 'center' }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'rgba(255,255,255,0.04)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px auto',
            color: 'var(--text-muted)'
          }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '8px' }}>
            Ready to Train Model
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '480px', margin: '0 auto 20px auto' }}>
            Select your target column, tune features in the What-If sandbox, and click <strong>Train & Analyze Model</strong> to compute train vs. test scores, evaluate overfitting, inspect the confusion matrix, and track loss convergence.
          </p>
        </div>
      )}
    </div>
  );
};

// ==============================================================================
// FILE SUMMARY: frontend/src/components/MLLabTab.tsx
// ==============================================================================
// WHAT THIS FILE CONTAINS AND DOES:
// This component implements the Pedagogical Machine Learning Impact Lab & Generalization Engine:
//   1. Target Column Detection & Selection: Queries target candidate variables and auto-classifies
//      into regression vs classification tasks.
//   2. Feature Selection & What-If Sandbox: Checkbox controls allowing users to toggle individual
//      features on/off to discover which columns improve generalization and eliminate noise.
//   3. Model Architecture Selection: Supports Decision Trees (with tunable max_depth slider),
//      Ridge/Logistic Regression, Random Forests, and Multi-Layer Perceptron (Neural Network).
//   4. Pedagogical Generalization Diagnostics: Color-coded health status banner
//      (healthy_generalization, moderate_overfitting, severe_overfitting, underfitting) with
//      backend plain-English pedagogical explanations.
//   5. 4-KPI Metric Grid: Train score, Holdout Test score, Overfitting Gap (Δ), and RMSE/F1.
//   6. Pure SVG & Matrix Interactive Visualizations:
//      - Overfitting diagnostics gauge (train vs test bars).
//      - Classification Confusion Matrix Heatmap (Actual vs Predicted matrix with error highlights).
//      - Neural network gradient descent loss curve over epochs.
//      - Actual vs predicted scatter plot with 45-degree diagonal.
//      - Feature importance / weight attribution horizontal bar chart.
//   7. Cross-Version Generalization Benchmark: Side-by-side comparison of baseline raw v1 vs
//      active cleaned dataset, showing performance gain (+R² / +Accuracy) and overfitting reduction.
//
// HOW IT CONNECTS TO OTHER FILES:
// - Imports types from 'frontend/src/types/api.ts'.
// - Calls 'api.getMLTargets', 'api.trainMLModel', and 'api.compareMLVersions' from 'frontend/src/services/api.ts'.
// - Rendered inside 'frontend/src/App.tsx' when the user switches to the 'ml' tab.
// ==============================================================================
