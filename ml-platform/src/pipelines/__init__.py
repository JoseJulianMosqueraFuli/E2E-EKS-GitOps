"""
ML Pipelines Module

This module contains end-to-end ML pipelines for training, validation,
and deployment of machine learning models.
"""

from .inference_pipeline import InferencePipeline

__all__ = ["TrainingPipeline", "InferencePipeline"]


def __getattr__(name):
    if name == "TrainingPipeline":
        from .training_pipeline import TrainingPipeline

        return TrainingPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
