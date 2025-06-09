from baseline_analyzer.processing import build_baseline
import pandas as pd

def test_frame_has_columns():
    df = build_baseline()
    assert isinstance(df, pd.DataFrame), "build_baseline should return a pandas DataFrame"
    expected_columns = {"person", "net_owed"}
    assert expected_columns <= set(df.columns), \
        f"DataFrame columns {df.columns} do not contain all expected columns {expected_columns}"
