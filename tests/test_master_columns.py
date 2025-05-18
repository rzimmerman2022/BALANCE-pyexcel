from balance_pipeline.constants import MASTER_SCHEMA_COLUMNS

def test_postdate_spelling():
    assert "PostDate" in MASTER_SCHEMA_COLUMNS
    assert "PostDatte" not in MASTER_SCHEMA_COLUMNS
