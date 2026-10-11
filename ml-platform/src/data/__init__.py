"""
Data Processing Module

This module contains data validation, preprocessing, and feature engineering
utilities for the MLOps platform.
"""

from .data_loader import DataLoader
from .feature_engineering import FeatureEngineer

__all__ = ["DataValidator", "FeatureEngineer", "DataLoader"]


def __getattr__(name):
    if name == "DataValidator":
        from .data_validator import DataValidator

        return DataValidator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
