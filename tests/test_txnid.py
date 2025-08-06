import pathlib

import pandas as pd
import pytest  # Keep pytest import separate for clarity
from balance_pipeline.ingest import load_folder
from balance_pipeline.normalize import normalize_df

# Define project root relative to this test file for robust pathing
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Use a fixture file that's checked into the repo instead of a private file
WF_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "wells_fargo_card_sample.csv"


def test_txnid_unique_real_file(tmp_path):
    # copy fixture to temp inbox
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _ = pd.read_csv(WF_FIXTURE).to_csv(inbox / WF_FIXTURE.name, index=False)

    # Removed owner_hint="Jordyn" as it's not a valid argument for load_folder
    df = load_folder(inbox)
    df_norm = normalize_df(df)
    assert df_norm["TxnID"].is_unique


@pytest.mark.parametrize(
    "d1,p1,d2,p2",
    [
        ("2024-01-01", "01/01", "2024-01-01", "01/02"),
        ("2024-08-19", "08/19", "2024-08-19", "08/20"),
    ],
)
def test_txnid_differs_by_postdate(d1, p1, d2, p2):
    from balance_pipeline.normalize import _txn_id

    row1 = {
        "Date": d1,
        "PostDate": p1,
        "Amount": 1,
        "Description": "X",
        "Bank": "B",
        "Account": "A",
    }
    row2 = row1 | {"PostDate": p2}
    assert _txn_id(row1) != _txn_id(row2)
