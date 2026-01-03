"""
Data Validator

Data quality validation using Great Expectations.
Validates data schema, distributions, and business rules.
"""

import logging
import os
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest
from great_expectations.checkpoint import SimpleCheckpoint

logger = logging.getLogger(__name__)


class DataValidator:
    """Data validation using Great Expectations."""
    
    def __init__(self, 
                 context_root_dir: str = "./gx",
                 datasource_name: str = "pandas_datasource"):
        """
        Initialize data validator.
        
        Args:
            context_root_dir: Great Expectations context directory
            datasource_name: Name of the datasource
        """
        self.context_root_dir = context_root_dir
        self.datasource_name = datasource_name
        self.context = None
        self.datasource = None
        
        self._setup_context()
        
    def _setup_context(self):
        """Setup Great Expectations context and datasource."""
        try:
            # Try to get existing context
            self.context = gx.get_context(context_root_dir=self.context_root_dir)
            logger.info("Using existing Great Expectations context")
        except:
            # Create new context
            self.context = gx.get_context(
                context_root_dir=self.context_root_dir,
                mode="file"
            )
            logger.info("Created new Great Expectations context")
        
        # Setup pandas datasource
        try:
            self.datasource = self.context.get_datasource(self.datasource_name)
        except:
            datasource_config = {
                "name": self.datasource_name,
                "class_name": "Datasource",
                "execution_engine": {
                    "class_name": "PandasExecutionEngine"
                },
                "data_connectors": {
                    "runtime_data_connector": {
                        "class_name": "RuntimeDataConnector",
                        "batch_identifiers": ["batch_id"]
                    }
                }
            }
            self.datasource = self.context.add_datasource(**datasource_config)
            logger.info(f"Created datasource: {self.datasource_name}")
    
    def create_expectation_suite(self, 
                                suite_name: str,
                                data: pd.DataFrame,
                                overwrite: bool = False) -> str:
        """
        Create expectation suite based on data profiling.
        
        Args:
            suite_name: Name of the expectation suite
            data: Sample data for profiling
            overwrite: Whether to overwrite existing suite
            
        Returns:
            Suite name
        """
        try:
            if overwrite:
                self.context.delete_expectation_suite(suite_name)
        except:
            pass
            
        # Create expectation suite
        suite = self.context.create_expectation_suite(
            expectation_suite_name=suite_name,
            overwrite_existing=overwrite
        )
        
        # Create validator
        batch_request = RuntimeBatchRequest(
            datasource_name=self.datasource_name,
            data_connector_name="runtime_data_connector",
            data_asset_name="validation_data",
            runtime_parameters={"batch_data": data},
            batch_identifiers={"batch_id": "sample_batch"}
        )
        
        validator = self.context.get_validator(
            batch_request=batch_request,
            expectation_suite_name=suite_name
        )
        
        # Add basic expectations based on data
        self._add_basic_expectations(validator, data)
        
        # Save suite
        validator.save_expectation_suite(discard_failed_expectations=False)
        
        logger.info(f"Created expectation suite: {suite_name}")
        return suite_name
    
    def _add_basic_expectations(self, validator, data: pd.DataFrame):
        """Add basic expectations based on data profiling."""
        
        # Table-level expectations
        validator.expect_table_row_count_to_be_between(
            min_value=1,
            max_value=None
        )
        
        validator.expect_table_columns_to_match_ordered_list(
            column_list=list(data.columns)
        )
        
        # Column-level expectations
        for column in data.columns:
            col_data = data[column]
            
            # Non-null expectations
            null_percentage = col_data.isnull().mean()
            if null_percentage < 0.05:  # Less than 5% nulls
                validator.expect_column_values_to_not_be_null(column)
            else:
                validator.expect_column_values_to_not_be_null(
                    column,
                    mostly=1 - null_percentage - 0.01  # Allow slightly more nulls
                )
            
            # Type-specific expectations
            if pd.api.types.is_numeric_dtype(col_data):
                # Numeric columns
                validator.expect_column_values_to_be_of_type(
                    column, 
                    type_="float" if col_data.dtype == 'float64' else "int"
                )
                
                # Range expectations
                if not col_data.isnull().all():
                    min_val = col_data.min()
                    max_val = col_data.max()
                    
                    # Add some buffer to min/max
                    range_buffer = (max_val - min_val) * 0.1
                    validator.expect_column_values_to_be_between(
                        column,
                        min_value=min_val - range_buffer,
                        max_value=max_val + range_buffer
                    )
                
            elif pd.api.types.is_string_dtype(col_data):
                # String columns
                validator.expect_column_values_to_be_of_type(column, type_="str")
                
                # Length expectations
                if not col_data.isnull().all():
                    lengths = col_data.str.len()
                    min_length = lengths.min()
                    max_length = lengths.max()
                    
                    if min_length == max_length:
                        validator.expect_column_value_lengths_to_equal(column, min_length)
                    else:
                        validator.expect_column_value_lengths_to_be_between(
                            column, min_length, max_length
                        )
                
            elif pd.api.types.is_datetime64_any_dtype(col_data):
                # Datetime columns
                validator.expect_column_values_to_be_of_type(column, type_="datetime")
                
                if not col_data.isnull().all():
                    min_date = col_data.min()
                    max_date = col_data.max()
                    
                    validator.expect_column_values_to_be_between(
                        column, min_date, max_date
                    )
    
    def validate_data(self, 
                     data: pd.DataFrame,
                     suite_name: str,
                     run_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate data against expectation suite.
        
        Args:
            data: Data to validate
            suite_name: Name of expectation suite
            run_name: Optional run name for tracking
            
        Returns:
            Validation results
        """
        if run_name is None:
            run_name = f"validation_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create batch request
        batch_request = RuntimeBatchRequest(
            datasource_name=self.datasource_name,
            data_connector_name="runtime_data_connector",
            data_asset_name="validation_data",
            runtime_parameters={"batch_data": data},
            batch_identifiers={"batch_id": run_name}
        )
        
        # Create checkpoint
        checkpoint_config = {
            "name": f"checkpoint_{run_name}",
            "config_version": 1.0,
            "template_name": None,
            "run_name_template": run_name,
            "expectation_suite_name": suite_name,
            "batch_request": batch_request,
            "action_list": [
                {
                    "name": "store_validation_result",
                    "action": {"class_name": "StoreValidationResultAction"},
                },
                {
                    "name": "update_data_docs",
                    "action": {"class_name": "UpdateDataDocsAction"},
                },
            ],
        }
        
        checkpoint = SimpleCheckpoint(
            f"checkpoint_{run_name}",
            self.context,
            **checkpoint_config
        )
        
        # Run validation
        results = checkpoint.run()
        
        # Extract key metrics
        validation_result = results.list_validation_results()[0]
        
        summary = {
            "success": validation_result.success,
            "run_name": run_name,
            "suite_name": suite_name,
            "evaluated_expectations": validation_result.statistics["evaluated_expectations"],
            "successful_expectations": validation_result.statistics["successful_expectations"],
            "unsuccessful_expectations": validation_result.statistics["unsuccessful_expectations"],
            "success_percent": validation_result.statistics["success_percent"],
            "validation_time": datetime.now().isoformat()
        }
        
        # Log results
        if summary["success"]:
            logger.info(f"Data validation passed: {summary['success_percent']:.1f}% success rate")
        else:
            logger.warning(f"Data validation failed: {summary['success_percent']:.1f}% success rate")
            
        return summary
    
    def get_validation_report_url(self) -> str:
        """Get URL for data docs validation report."""
        try:
            data_docs_sites = self.context.get_docs_sites_urls()
            if data_docs_sites:
                return list(data_docs_sites.values())[0]
        except:
            pass
        return "Data docs not available"
    
    def create_data_quality_suite(self, suite_name: str = "data_quality_suite"):
        """
        Create a comprehensive data quality expectation suite.
        
        Args:
            suite_name: Name of the suite
        """
        suite = self.context.create_expectation_suite(
            expectation_suite_name=suite_name,
            overwrite_existing=True
        )
        
        # This would be populated with business-specific rules
        # For now, we'll create a template
        expectations = [
            {
                "expectation_type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 1}
            },
            {
                "expectation_type": "expect_table_columns_to_match_set",
                "kwargs": {"column_set": ["id", "feature_1", "feature_2", "target"]}
            }
        ]
        
        for expectation in expectations:
            suite.add_expectation(
                gx.expectations.registry.get_expectation_class_from_expectation_type(
                    expectation["expectation_type"]
                )(**expectation["kwargs"])
            )
        
        self.context.save_expectation_suite(suite)
        logger.info(f"Created data quality suite: {suite_name}")
        
        return suite_name


# Example usage
def validate_sample_data():
    """Example of data validation workflow."""
    # Create sample data
    np.random.seed(42)
    data = pd.DataFrame({
        'id': range(1000),
        'feature_1': np.random.normal(0, 1, 1000),
        'feature_2': np.random.uniform(0, 100, 1000),
        'feature_3': np.random.choice(['A', 'B', 'C'], 1000),
        'target': np.random.normal(50, 10, 1000)
    })
    
    # Add some nulls
    data.loc[data.sample(50).index, 'feature_1'] = np.nan
    
    # Initialize validator
    validator = DataValidator()
    
    # Create expectation suite
    suite_name = validator.create_expectation_suite(
        "sample_data_suite", 
        data.head(100),  # Use sample for profiling
        overwrite=True
    )
    
    # Validate full dataset
    results = validator.validate_data(data, suite_name)
    
    print(f"Validation Results:")
    print(f"Success: {results['success']}")
    print(f"Success Rate: {results['success_percent']:.1f}%")
    print(f"Report URL: {validator.get_validation_report_url()}")
    
    return validator, results


if __name__ == "__main__":
    validator, results = validate_sample_data()