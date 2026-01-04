"""
Inference Pipeline

Pipeline for model inference with preprocessing, prediction, and post-processing.
Supports batch and real-time inference with monitoring.
"""

import logging
import os
import sys
import time
from typing import Dict, Any, List, Union, Optional
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from datetime import datetime
import joblib
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_loader import DataLoader
from data.feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)


class InferencePipeline:
    """Pipeline for model inference with preprocessing and monitoring."""
    
    def __init__(self, 
                 model_uri: Optional[str] = None,
                 model_path: Optional[str] = None,
                 feature_pipeline_path: Optional[str] = None):
        """
        Initialize inference pipeline.
        
        Args:
            model_uri: MLflow model URI (e.g., 'models:/model_name/version')
            model_path: Local path to saved model
            feature_pipeline_path: Path to feature engineering pipeline
        """
        self.model = None
        self.feature_engineer = None
        self.model_metadata = {}
        self.inference_stats = {
            'total_predictions': 0,
            'total_inference_time': 0.0,
            'error_count': 0
        }
        
        # Load model and feature pipeline
        if model_uri:
            self.load_model_from_mlflow(model_uri)
        elif model_path:
            self.load_model_from_path(model_path)
        
        if feature_pipeline_path:
            self.load_feature_pipeline(feature_pipeline_path)
    
    def load_model_from_mlflow(self, model_uri: str):
        """
        Load model from MLflow.
        
        Args:
            model_uri: MLflow model URI
        """
        try:
            # Load model
            self.model = mlflow.sklearn.load_model(model_uri)
            
            # Get model metadata
            model_version = mlflow.MlflowClient().get_model_version_by_alias(
                model_uri.split('/')[1], model_uri.split('/')[-1]
            ) if 'models:/' in model_uri else None
            
            self.model_metadata = {
                'model_uri': model_uri,
                'loaded_at': datetime.now().isoformat(),
                'model_version': model_version.version if model_version else 'unknown'
            }
            
            logger.info(f"Loaded model from MLflow: {model_uri}")
            
        except Exception as e:
            logger.error(f"Error loading model from MLflow: {e}")
            raise
    
    def load_model_from_path(self, model_path: str):
        """
        Load model from local path.
        
        Args:
            model_path: Path to saved model
        """
        try:
            # Load model using joblib (assuming it's a pickled model)
            with open(model_path, 'rb') as f:
                model_data = joblib.load(f)
            
            if isinstance(model_data, dict):
                self.model = model_data.get('model')
                self.model_metadata = {
                    'model_path': model_path,
                    'loaded_at': datetime.now().isoformat(),
                    'model_name': model_data.get('model_name', 'unknown')
                }
            else:
                self.model = model_data
                self.model_metadata = {
                    'model_path': model_path,
                    'loaded_at': datetime.now().isoformat()
                }
            
            logger.info(f"Loaded model from path: {model_path}")
            
        except Exception as e:
            logger.error(f"Error loading model from path: {e}")
            raise
    
    def load_feature_pipeline(self, pipeline_path: str):
        """
        Load feature engineering pipeline.
        
        Args:
            pipeline_path: Path to feature pipeline
        """
        try:
            self.feature_engineer = FeatureEngineer()
            self.feature_engineer.load_pipeline(pipeline_path)
            logger.info(f"Loaded feature pipeline from: {pipeline_path}")
            
        except Exception as e:
            logger.error(f"Error loading feature pipeline: {e}")
            raise
    
    def preprocess_data(self, data: pd.DataFrame) -> np.ndarray:
        """
        Preprocess input data using feature engineering pipeline.
        
        Args:
            data: Input data
            
        Returns:
            Preprocessed features
        """
        if self.feature_engineer is None:
            logger.warning("No feature pipeline loaded, returning data as-is")
            return data.values
        
        try:
            # Transform data
            X_transformed = self.feature_engineer.transform(data)
            
            # Apply feature selection if available
            if self.feature_engineer.feature_selector is not None:
                X_transformed = self.feature_engineer.feature_selector.transform(X_transformed)
            
            return X_transformed
            
        except Exception as e:
            logger.error(f"Error in preprocessing: {e}")
            raise
    
    def predict(self, 
                data: Union[pd.DataFrame, np.ndarray],
                return_probabilities: bool = False,
                confidence_threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        Make predictions on input data.
        
        Args:
            data: Input data
            return_probabilities: Whether to return prediction probabilities
            confidence_threshold: Minimum confidence for predictions
            
        Returns:
            Dictionary with predictions and metadata
        """
        if self.model is None:
            raise ValueError("No model loaded")
        
        start_time = time.time()
        
        try:
            # Convert to DataFrame if numpy array
            if isinstance(data, np.ndarray):
                data = pd.DataFrame(data)
            
            # Preprocess data
            X_processed = self.preprocess_data(data)
            
            # Make predictions
            predictions = self.model.predict(X_processed)
            
            result = {
                'predictions': predictions.tolist(),
                'num_samples': len(predictions),
                'inference_time': time.time() - start_time,
                'model_metadata': self.model_metadata
            }
            
            # Add probabilities if requested and available
            if return_probabilities and hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(X_processed)
                result['probabilities'] = probabilities.tolist()
                result['max_probability'] = np.max(probabilities, axis=1).tolist()
                
                # Apply confidence threshold if specified
                if confidence_threshold is not None:
                    confident_mask = np.max(probabilities, axis=1) >= confidence_threshold
                    result['confident_predictions'] = predictions.copy()
                    result['confident_predictions'][~confident_mask] = -1  # Mark uncertain predictions
                    result['confidence_flags'] = confident_mask.tolist()
                    result['confident_count'] = int(np.sum(confident_mask))
            
            # Update statistics
            self.inference_stats['total_predictions'] += len(predictions)
            self.inference_stats['total_inference_time'] += result['inference_time']
            
            logger.info(f"Made {len(predictions)} predictions in {result['inference_time']:.3f}s")
            
            return result
            
        except Exception as e:
            self.inference_stats['error_count'] += 1
            logger.error(f"Error during inference: {e}")
            raise
    
    def predict_batch(self, 
                     data_path: str,
                     output_path: Optional[str] = None,
                     batch_size: int = 1000,
                     **predict_kwargs) -> Dict[str, Any]:
        """
        Make predictions on batch data from file.
        
        Args:
            data_path: Path to input data file
            output_path: Path to save predictions (optional)
            batch_size: Batch size for processing
            **predict_kwargs: Additional arguments for predict method
            
        Returns:
            Batch prediction results
        """
        # Load data
        loader = DataLoader()
        
        if data_path.endswith('.csv'):
            data = loader.load_csv(data_path)
        elif data_path.endswith('.parquet'):
            data = loader.load_parquet(data_path)
        else:
            raise ValueError(f"Unsupported file format: {data_path}")
        
        logger.info(f"Loaded batch data: {data.shape}")
        
        # Process in batches
        all_predictions = []
        all_probabilities = []
        total_time = 0
        
        for i in range(0, len(data), batch_size):
            batch_data = data.iloc[i:i+batch_size]
            
            # Make predictions
            batch_results = self.predict(batch_data, **predict_kwargs)
            
            all_predictions.extend(batch_results['predictions'])
            total_time += batch_results['inference_time']
            
            if 'probabilities' in batch_results:
                all_probabilities.extend(batch_results['probabilities'])
            
            logger.info(f"Processed batch {i//batch_size + 1}/{(len(data)-1)//batch_size + 1}")
        
        # Prepare results
        results = {
            'predictions': all_predictions,
            'num_samples': len(all_predictions),
            'total_inference_time': total_time,
            'avg_inference_time_per_sample': total_time / len(all_predictions),
            'batch_size': batch_size,
            'model_metadata': self.model_metadata
        }
        
        if all_probabilities:
            results['probabilities'] = all_probabilities
        
        # Save predictions if output path specified
        if output_path:
            predictions_df = data.copy()
            predictions_df['predictions'] = all_predictions
            
            if all_probabilities:
                # Add probability columns
                prob_array = np.array(all_probabilities)
                for i in range(prob_array.shape[1]):
                    predictions_df[f'probability_class_{i}'] = prob_array[:, i]
            
            # Save results
            if output_path.endswith('.csv'):
                predictions_df.to_csv(output_path, index=False)
            elif output_path.endswith('.parquet'):
                predictions_df.to_parquet(output_path, index=False)
            
            logger.info(f"Saved predictions to: {output_path}")
        
        return results
    
    def get_inference_stats(self) -> Dict[str, Any]:
        """Get inference statistics."""
        stats = self.inference_stats.copy()
        
        if stats['total_predictions'] > 0:
            stats['avg_inference_time_per_prediction'] = (
                stats['total_inference_time'] / stats['total_predictions']
            )
            stats['error_rate'] = stats['error_count'] / stats['total_predictions']
        else:
            stats['avg_inference_time_per_prediction'] = 0
            stats['error_rate'] = 0
        
        return stats
    
    def reset_stats(self):
        """Reset inference statistics."""
        self.inference_stats = {
            'total_predictions': 0,
            'total_inference_time': 0.0,
            'error_count': 0
        }
        logger.info("Reset inference statistics")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the inference pipeline.
        
        Returns:
            Health check results
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'model_loaded': self.model is not None,
            'feature_pipeline_loaded': self.feature_engineer is not None,
            'model_metadata': self.model_metadata,
            'inference_stats': self.get_inference_stats()
        }
        
        # Test prediction with dummy data
        try:
            if self.model is not None:
                # Create dummy data based on expected input
                if self.feature_engineer and self.feature_engineer.feature_names_in_:
                    dummy_data = pd.DataFrame(
                        np.random.randn(1, len(self.feature_engineer.feature_names_in_)),
                        columns=self.feature_engineer.feature_names_in_
                    )
                else:
                    # Fallback: create simple dummy data
                    dummy_data = pd.DataFrame(np.random.randn(1, 5))
                
                # Test prediction
                test_result = self.predict(dummy_data)
                health_status['test_prediction_success'] = True
                health_status['test_inference_time'] = test_result['inference_time']
                
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['test_prediction_success'] = False
            health_status['error'] = str(e)
            logger.warning(f"Health check failed: {e}")
        
        return health_status
    
    def save_predictions_with_metadata(self, 
                                     predictions: Dict[str, Any],
                                     output_path: str):
        """
        Save predictions with metadata in JSON format.
        
        Args:
            predictions: Prediction results
            output_path: Output file path
        """
        # Add timestamp and pipeline info
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'pipeline_metadata': {
                'model_metadata': self.model_metadata,
                'inference_stats': self.get_inference_stats()
            },
            'predictions': predictions
        }
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Saved predictions with metadata to: {output_path}")


# Example usage
def inference_example():
    """Example of using the inference pipeline."""
    from ..pipelines.training_pipeline import TrainingPipeline
    
    # First, train a model (or load existing one)
    print("Training a sample model...")
    
    # Create sample data
    loader = DataLoader()
    sample_data = loader.create_sample_data(
        n_samples=1000,
        n_features=5,
        task_type="classification"
    )
    
    # Save training data
    os.makedirs("data", exist_ok=True)
    sample_data.to_csv("data/training_data.csv", index=False)
    
    # Train model
    pipeline = TrainingPipeline()
    results = pipeline.run_pipeline("data/training_data.csv")
    
    print(f"Model trained with run_id: {results['run_id']}")
    
    # Create inference data (similar structure, different values)
    inference_data = loader.create_sample_data(
        n_samples=100,
        n_features=5,
        task_type="classification"
    ).drop('target', axis=1)  # Remove target for inference
    
    inference_data.to_csv("data/inference_data.csv", index=False)
    
    # Initialize inference pipeline
    print("Setting up inference pipeline...")
    
    inference_pipeline = InferencePipeline(
        model_path=f"artifacts/model_{results['run_id']}.joblib",
        feature_pipeline_path=f"artifacts/feature_pipeline_{results['run_id']}.joblib"
    )
    
    # Health check
    health = inference_pipeline.health_check()
    print(f"Health check: {health['status']}")
    
    # Single prediction
    print("Making single predictions...")
    single_predictions = inference_pipeline.predict(
        inference_data.head(5),
        return_probabilities=True,
        confidence_threshold=0.8
    )
    
    print(f"Single predictions: {single_predictions['predictions']}")
    print(f"Confident predictions: {single_predictions.get('confident_count', 'N/A')}/5")
    
    # Batch prediction
    print("Making batch predictions...")
    batch_results = inference_pipeline.predict_batch(
        "data/inference_data.csv",
        "data/predictions.csv",
        batch_size=50,
        return_probabilities=True
    )
    
    print(f"Batch predictions completed: {batch_results['num_samples']} samples")
    print(f"Average inference time: {batch_results['avg_inference_time_per_sample']:.4f}s per sample")
    
    # Get statistics
    stats = inference_pipeline.get_inference_stats()
    print(f"Total predictions made: {stats['total_predictions']}")
    print(f"Error rate: {stats['error_rate']:.2%}")
    
    return inference_pipeline, batch_results


if __name__ == "__main__":
    # Create directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("artifacts", exist_ok=True)
    
    # Run example
    inference_pipeline, results = inference_example()