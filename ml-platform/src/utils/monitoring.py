"""
Model Monitoring

Utilities for monitoring ML model performance, drift detection,
and inference statistics.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ModelMonitor:
    """Monitor ML model performance and detect drift."""
    
    def __init__(self, model_name: str):
        """
        Initialize model monitor.
        
        Args:
            model_name: Name of the model to monitor
        """
        self.model_name = model_name
        self.baseline_stats: Optional[Dict[str, Any]] = None
        self.prediction_history: List[Dict[str, Any]] = []
        self.drift_threshold = 0.1
        
    def set_baseline(self, data: pd.DataFrame, predictions: np.ndarray):
        """
        Set baseline statistics for drift detection.
        
        Args:
            data: Baseline input data
            predictions: Baseline predictions
        """
        self.baseline_stats = {
            'feature_means': data.mean().to_dict(),
            'feature_stds': data.std().to_dict(),
            'prediction_mean': float(np.mean(predictions)),
            'prediction_std': float(np.std(predictions)),
            'prediction_distribution': np.histogram(predictions, bins=10)[0].tolist(),
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Baseline set for model {self.model_name}")
        
    def log_prediction(self, 
                      input_data: pd.DataFrame, 
                      predictions: np.ndarray,
                      latency_ms: float):
        """
        Log prediction for monitoring.
        
        Args:
            input_data: Input features
            predictions: Model predictions
            latency_ms: Inference latency in milliseconds
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'num_samples': len(predictions),
            'prediction_mean': float(np.mean(predictions)),
            'prediction_std': float(np.std(predictions)),
            'latency_ms': latency_ms,
            'feature_means': input_data.mean().to_dict()
        }
        
        self.prediction_history.append(record)
        
        # Keep only last 1000 records
        if len(self.prediction_history) > 1000:
            self.prediction_history = self.prediction_history[-1000:]
            
    def detect_drift(self, current_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect data drift compared to baseline.
        
        Args:
            current_data: Current input data
            
        Returns:
            Drift detection results
        """
        if self.baseline_stats is None:
            return {'drift_detected': False, 'message': 'No baseline set'}
        
        drift_results = {
            'drift_detected': False,
            'drifted_features': [],
            'drift_scores': {}
        }
        
        current_means = current_data.mean()
        
        for feature in current_means.index:
            if feature in self.baseline_stats['feature_means']:
                baseline_mean = self.baseline_stats['feature_means'][feature]
                baseline_std = self.baseline_stats['feature_stds'].get(feature, 1.0)
                
                if baseline_std == 0:
                    baseline_std = 1.0
                
                # Calculate normalized drift
                drift_score = abs(current_means[feature] - baseline_mean) / baseline_std
                drift_results['drift_scores'][feature] = float(drift_score)
                
                if drift_score > self.drift_threshold:
                    drift_results['drifted_features'].append(feature)
                    drift_results['drift_detected'] = True
        
        if drift_results['drift_detected']:
            logger.warning(f"Drift detected in features: {drift_results['drifted_features']}")
        
        return drift_results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics from prediction history.
        
        Returns:
            Performance statistics
        """
        if not self.prediction_history:
            return {'message': 'No prediction history available'}
        
        latencies = [r['latency_ms'] for r in self.prediction_history]
        total_samples = sum(r['num_samples'] for r in self.prediction_history)
        
        return {
            'total_predictions': total_samples,
            'total_requests': len(self.prediction_history),
            'avg_latency_ms': float(np.mean(latencies)),
            'p50_latency_ms': float(np.percentile(latencies, 50)),
            'p95_latency_ms': float(np.percentile(latencies, 95)),
            'p99_latency_ms': float(np.percentile(latencies, 99)),
            'max_latency_ms': float(np.max(latencies)),
            'min_latency_ms': float(np.min(latencies))
        }
    
    def reset_history(self):
        """Reset prediction history."""
        self.prediction_history = []
        logger.info(f"Reset prediction history for model {self.model_name}")