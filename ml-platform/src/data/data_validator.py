"""
Data Validator

Data quality validation using Great Expectations (1.x fluent API).
Validates data schema, distributions, and business rules.
"""

import logging
from typing import Dict, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime
import great_expectations as gx

logger = logging.getLogger(__name__)


class DataValidator:
    """Data validation using Great Expectations 1.x fluent API."""

    def __init__(self, context_root_dir: str = "./gx"):
        self.context_root_dir = context_root_dir
        self._context = None

    @property
    def context(self):
        if self._context is None:
            self._context = gx.get_context(mode="ephemeral")
        return self._context

    def _get_or_create_datasource(self, name: str):
        try:
            return self.context.data_sources.get(name)
        except Exception:
            return self.context.data_sources.add_pandas(name=name)

    def _get_or_create_suite(self, name: str, overwrite: bool = False):
        try:
            suite = self.context.suites.get(name)
            if overwrite:
                self.context.suites.delete(name)
                suite = self.context.suites.add(gx.ExpectationSuite(name=name))
            return suite
        except Exception:
            return self.context.suites.add(gx.ExpectationSuite(name=name))

    def create_expectation_suite(self,
                                 suite_name: str,
                                 data: pd.DataFrame,
                                 overwrite: bool = False) -> str:
        suite = self._get_or_create_suite(suite_name, overwrite=overwrite)

        datasource = self._get_or_create_datasource(f"{suite_name}_ds")
        try:
            data_asset = datasource.get_asset(f"{suite_name}_asset")
        except Exception:
            data_asset = datasource.add_dataframe_asset(name=f"{suite_name}_asset")

        try:
            batch_definition = data_asset.get_batch_definition(f"{suite_name}_batch")
        except Exception:
            batch_definition = data_asset.add_batch_definition_whole_dataframe(
                name=f"{suite_name}_batch"
            )

        validation_def = gx.ValidationDefinition(
            name=f"{suite_name}_validation",
            data=batch_definition,
            suite=suite,
        )
        self.context.validation_definitions.add_or_update(validation_def)

        self._add_basic_expectations(suite, data)
        self.context.suites.add_or_update(suite)

        logger.info(f"Created expectation suite: {suite_name}")
        return suite_name

    def _add_basic_expectations(self, suite, data: pd.DataFrame):
        suite.add_expectation(
            gx.expectations.ExpectTableRowCountToBeBetween(min_value=1)
        )
        suite.add_expectation(
            gx.expectations.ExpectTableColumnsToMatchSet(
                column_set=list(data.columns), exact_match=False
            )
        )

        for column in data.columns:
            col_data = data[column]
            null_percentage = col_data.isnull().mean()
            if null_percentage < 0.05:
                suite.add_expectation(
                    gx.expectations.ExpectColumnValuesToNotBeNull(column=column)
                )
            else:
                suite.add_expectation(
                    gx.expectations.ExpectColumnValuesToNotBeNull(
                        column=column, mostly=1 - null_percentage - 0.01
                    )
                )

            if pd.api.types.is_numeric_dtype(col_data):
                if not col_data.isnull().all():
                    min_val = float(col_data.min())
                    max_val = float(col_data.max())
                    range_buffer = (max_val - min_val) * 0.1
                    suite.add_expectation(
                        gx.expectations.ExpectColumnValuesToBeBetween(
                            column=column,
                            min_value=min_val - range_buffer,
                            max_value=max_val + range_buffer,
                        )
                    )
            elif pd.api.types.is_string_dtype(col_data):
                if not col_data.isnull().all():
                    lengths = col_data.str.len()
                    min_length = int(lengths.min())
                    max_length = int(lengths.max())
                    suite.add_expectation(
                        gx.expectations.ExpectColumnValueLengthsToBeBetween(
                            column=column, min_value=min_length, max_value=max_length
                        )
                    )

    def validate_data(self,
                      data: pd.DataFrame,
                      suite_name: str,
                      run_name: Optional[str] = None) -> Dict[str, Any]:
        if run_name is None:
            run_name = f"validation_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        suite = self.context.suites.get(suite_name)

        ds_name = f"val_{run_name}_ds"
        datasource = self._get_or_create_datasource(ds_name)
        try:
            data_asset = datasource.get_asset(f"val_{run_name}_asset")
        except Exception:
            data_asset = datasource.add_dataframe_asset(name=f"val_{run_name}_asset")

        try:
            batch_definition = data_asset.get_batch_definition(f"val_{run_name}_batch")
        except Exception:
            batch_definition = data_asset.add_batch_definition_whole_dataframe(
                name=f"val_{run_name}_batch"
            )

        validation_def = gx.ValidationDefinition(
            name=f"val_{run_name}_validation",
            data=batch_definition,
            suite=suite,
        )
        self.context.validation_definitions.add_or_update(validation_def)

        checkpoint = gx.Checkpoint(
            name=f"checkpoint_{run_name}",
            validation_definitions=[validation_def],
        )
        self.context.checkpoints.add_or_update(checkpoint)

        result = checkpoint.run(batch_parameters={"dataframe": data})

        success = result.success
        stats = {}
        for vr in result.run_results:
            if hasattr(vr, "validation_result") and hasattr(vr.validation_result, "statistics"):
                stats = vr.validation_result.statistics
                break

        summary = {
            "success": success,
            "run_name": run_name,
            "suite_name": suite_name,
            "evaluated_expectations": stats.get("evaluated_expectations", 0),
            "successful_expectations": stats.get("successful_expectations", 0),
            "unsuccessful_expectations": stats.get("unsuccessful_expectations", 0),
            "success_percent": stats.get("success_percent", 0.0),
            "validation_time": datetime.now().isoformat(),
        }

        if summary["success"]:
            logger.info(f"Data validation passed: {summary['success_percent']:.1f}% success rate")
        else:
            logger.warning(f"Data validation failed: {summary['success_percent']:.1f}% success rate")

        return summary

    def get_validation_report_url(self) -> str:
        try:
            data_docs_sites = self.context.get_docs_sites_urls()
            if data_docs_sites:
                return list(data_docs_sites.values())[0]
        except Exception:
            pass
        return "Data docs not available"

    def create_data_quality_suite(self, suite_name: str = "data_quality_suite"):
        suite = self._get_or_create_suite(suite_name, overwrite=True)

        suite.add_expectation(
            gx.expectations.ExpectTableRowCountToBeBetween(min_value=1)
        )
        suite.add_expectation(
            gx.expectations.ExpectTableColumnsToMatchSet(
                column_set=["id", "feature_1", "feature_2", "target"]
            )
        )

        self.context.suites.add_or_update(suite)
        logger.info(f"Created data quality suite: {suite_name}")
        return suite_name


def validate_sample_data():
    np.random.seed(42)
    data = pd.DataFrame({
        "id": range(1000),
        "feature_1": np.random.normal(0, 1, 1000),
        "feature_2": np.random.uniform(0, 100, 1000),
        "feature_3": np.random.choice(["A", "B", "C"], 1000),
        "target": np.random.normal(50, 10, 1000),
    })
    data.loc[data.sample(50).index, "feature_1"] = np.nan

    validator = DataValidator()
    suite_name = validator.create_expectation_suite(
        "sample_data_suite", data.head(100), overwrite=True
    )
    results = validator.validate_data(data, suite_name)

    print(f"Validation Results:")
    print(f"Success: {results['success']}")
    print(f"Success Rate: {results['success_percent']:.1f}%")
    print(f"Report URL: {validator.get_validation_report_url()}")

    return validator, results


if __name__ == "__main__":
    validate_sample_data()