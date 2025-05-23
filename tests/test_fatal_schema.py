import pytest
from balance_pipeline.csv_consolidator import process_csv_files
from balance_pipeline.errors import FatalSchemaError


def test_fatal_schema_bubbles(tmp_path):
    # Create a corrupt YAML registry
    registry = tmp_path / "schema.yml"
    registry.write_text("not: [unclosed")
    # Create a minimal CSV to process
    csv = tmp_path / "sample.csv"
    csv.write_text("Date,Description,Amount\n2025-01-01,Test,100\n")
    # Running process_csv_files with the corrupt registry should raise FatalSchemaError
    with pytest.raises(FatalSchemaError):
        process_csv_files([str(csv)], schema_registry_override_path=registry)
