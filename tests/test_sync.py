import numpy as np
import pandas as pd
from balance_pipeline.sync import (
    QUEUE_DECISION_COL,
    QUEUE_SPLIT_COL,
    QUEUE_TXNID_COL,
    TRANS_SHARED_FLAG_COL,
    TRANS_SPLIT_PERC_COL,
    TRANS_TXNID_COL,
    sync_review_decisions,
)
from pandas.testing import assert_frame_equal


# Sample transactions DataFrame
def sample_transactions_df() -> pd.DataFrame:
    data = {
        TRANS_TXNID_COL: ["TX1", "TX2", "TX3", "TX4", "TX5"],
        "Description": ["Desc1", "Desc2", "Desc3", "Desc4", "Desc5"],
        "Amount": [10.0, 20.0, 30.0, 40.0, 50.0],
        TRANS_SHARED_FLAG_COL: ["?", "?", "?", "Y", "?"],
        TRANS_SPLIT_PERC_COL: [pd.NA, pd.NA, pd.NA, 100.0, pd.NA],
    }
    df = pd.DataFrame(data)
    # Ensure correct dtypes, especially for SplitPercent which can be float or object with pd.NA
    # Replace pd.NA with np.nan before converting to float to avoid TypeError
    df[TRANS_SPLIT_PERC_COL] = (
        df[TRANS_SPLIT_PERC_COL].replace({pd.NA: np.nan}).astype(float)
    )
    return df


# Sample queue review DataFrame
def sample_queue_df() -> pd.DataFrame:
    data = {
        QUEUE_TXNID_COL: ["TX1", "TX2", "TX3", "TX_UNKNOWN", "TX5"],
        QUEUE_DECISION_COL: ["Y", "n", "S", "Y", "X"],  # TX5 has invalid decision
        QUEUE_SPLIT_COL: [
            None,
            "abc",
            "60.5",
            "50",
            "50",
        ],  # TX2 has invalid split, TX5 split is irrelevant
    }
    return pd.DataFrame(data)


def test_sync_empty_transactions():
    df_trans = pd.DataFrame(
        columns=[TRANS_TXNID_COL, TRANS_SHARED_FLAG_COL, TRANS_SPLIT_PERC_COL]
    )
    df_queue = sample_queue_df()
    result_df = sync_review_decisions(df_trans, df_queue)
    assert_frame_equal(result_df, df_trans)


def test_sync_empty_queue():
    df_trans = sample_transactions_df()
    df_queue = pd.DataFrame(
        columns=[QUEUE_TXNID_COL, QUEUE_DECISION_COL, QUEUE_SPLIT_COL]
    )
    result_df = sync_review_decisions(df_trans.copy(), df_queue)  # Pass copy
    assert_frame_equal(result_df, df_trans)


def test_sync_missing_cols_transactions(caplog):
    df_trans = sample_transactions_df().drop(columns=[TRANS_SHARED_FLAG_COL])
    df_queue = sample_queue_df()
    result_df = sync_review_decisions(df_trans.copy(), df_queue)
    assert "transactions dataframe missing required columns" in caplog.text.lower()
    assert_frame_equal(result_df, df_trans)


def test_sync_missing_cols_queue(caplog):
    df_trans = sample_transactions_df()
    df_queue = sample_queue_df().drop(columns=[QUEUE_DECISION_COL])
    result_df = sync_review_decisions(df_trans.copy(), df_queue)
    assert "queue review dataframe missing required columns" in caplog.text.lower()
    assert_frame_equal(result_df, df_trans)


def test_sync_happy_path_y_n_s_updates():
    df_trans = sample_transactions_df()
    # TX1: Y, TX2: N (from 'n'), TX3: S with 60.5, TX4: no queue entry, TX5: invalid decision 'X'
    queue_data = {
        QUEUE_TXNID_COL: ["TX1", "TX2", "TX3", "TX5"],
        QUEUE_DECISION_COL: ["Y", "n", "S", "X"],
        QUEUE_SPLIT_COL: [None, None, "60.5", "50"],
    }
    df_queue = pd.DataFrame(queue_data)

    result_df = sync_review_decisions(df_trans.copy(), df_queue)

    # TX1: SharedFlag='Y', SplitPercent=NA (original was NA, Y doesn't set it)
    tx1_res = result_df[result_df[TRANS_TXNID_COL] == "TX1"].iloc[0]
    assert tx1_res[TRANS_SHARED_FLAG_COL] == "Y"
    assert pd.isna(tx1_res[TRANS_SPLIT_PERC_COL])

    # TX2: SharedFlag='N', SplitPercent=NA (original was NA, N doesn't set it)
    tx2_res = result_df[result_df[TRANS_TXNID_COL] == "TX2"].iloc[0]
    assert tx2_res[TRANS_SHARED_FLAG_COL] == "N"
    assert pd.isna(tx2_res[TRANS_SPLIT_PERC_COL])

    # TX3: SharedFlag='S', SplitPercent=60.5
    tx3_res = result_df[result_df[TRANS_TXNID_COL] == "TX3"].iloc[0]
    assert tx3_res[TRANS_SHARED_FLAG_COL] == "S"
    assert tx3_res[TRANS_SPLIT_PERC_COL] == 60.5

    # TX4: Unchanged from original (SharedFlag='Y', SplitPercent=100.0)
    tx4_res = result_df[result_df[TRANS_TXNID_COL] == "TX4"].iloc[0]
    assert tx4_res[TRANS_SHARED_FLAG_COL] == "Y"
    assert tx4_res[TRANS_SPLIT_PERC_COL] == 100.0

    # TX5: Invalid decision 'X', should be unchanged (SharedFlag='?', SplitPercent=NA)
    tx5_res = result_df[result_df[TRANS_TXNID_COL] == "TX5"].iloc[0]
    assert tx5_res[TRANS_SHARED_FLAG_COL] == "?"
    assert pd.isna(tx5_res[TRANS_SPLIT_PERC_COL])


def test_sync_invalid_decision_value_ignored(caplog):
    df_trans = sample_transactions_df()
    queue_data = {
        QUEUE_TXNID_COL: ["TX1"],
        QUEUE_DECISION_COL: ["Invalid"],
        QUEUE_SPLIT_COL: [None],
    }
    df_queue = pd.DataFrame(queue_data)
    result_df = sync_review_decisions(df_trans.copy(), df_queue)

    assert "invalid decision value: 'invalid'" in caplog.text.lower()
    # TX1 should remain unchanged
    original_tx1 = df_trans[df_trans[TRANS_TXNID_COL] == "TX1"]
    result_tx1 = result_df[result_df[TRANS_TXNID_COL] == "TX1"]
    assert_frame_equal(
        result_tx1.reset_index(drop=True), original_tx1.reset_index(drop=True)
    )


def test_sync_split_decision_missing_percent_defaults_to_50(caplog):
    df_trans = sample_transactions_df()
    # TX1: S decision, missing split percent
    queue_data = {
        QUEUE_TXNID_COL: ["TX1"],
        QUEUE_DECISION_COL: ["S"],
        QUEUE_SPLIT_COL: [None],  # or np.nan
    }
    df_queue = pd.DataFrame(queue_data)
    result_df = sync_review_decisions(df_trans.copy(), df_queue)

    assert (
        "missing split percentage for split decision on txnid: tx1. using 50%."
        in caplog.text.lower()
    )
    tx1_res = result_df[result_df[TRANS_TXNID_COL] == "TX1"].iloc[0]
    assert tx1_res[TRANS_SHARED_FLAG_COL] == "S"
    assert tx1_res[TRANS_SPLIT_PERC_COL] == 50.0


def test_sync_split_decision_invalid_percent_format_defaults_to_50(caplog):
    df_trans = sample_transactions_df()
    # TX1: S decision, invalid format for split percent
    queue_data = {
        QUEUE_TXNID_COL: ["TX1"],
        QUEUE_DECISION_COL: ["S"],
        QUEUE_SPLIT_COL: ["abc"],
    }
    df_queue = pd.DataFrame(queue_data)
    result_df = sync_review_decisions(df_trans.copy(), df_queue)

    assert "invalid split percentage format" in caplog.text.lower() # no need to match the entire verbose message
    tx1_res = result_df[result_df[TRANS_TXNID_COL] == "TX1"].iloc[0]
    assert tx1_res[TRANS_SHARED_FLAG_COL] == "S"
    assert tx1_res[TRANS_SPLIT_PERC_COL] == 50.0


def test_sync_split_percent_out_of_bounds_clamped(caplog):
    df_trans = sample_transactions_df()
    queue_data = {
        QUEUE_TXNID_COL: ["TX1", "TX2"],
        QUEUE_DECISION_COL: ["S", "S"],
        QUEUE_SPLIT_COL: [-10, 110.0],  # TX1 below 0, TX2 above 100
    }
    df_queue = pd.DataFrame(queue_data)
    result_df = sync_review_decisions(df_trans.copy(), df_queue)

    assert (
        "split percentage (-10.0) below 0 for txnid: tx1. clamping to 0." in caplog.text.lower()
    )
    tx1_res = result_df[result_df[TRANS_TXNID_COL] == "TX1"].iloc[0]
    assert tx1_res[TRANS_SHARED_FLAG_COL] == "S"
    assert tx1_res[TRANS_SPLIT_PERC_COL] == 0.0

    assert (
        "split percentage (110.0) above 100 for txnid: tx2. clamping to 100."
        in caplog.text.lower()
    )
    tx2_res = result_df[result_df[TRANS_TXNID_COL] == "TX2"].iloc[0]
    assert tx2_res[TRANS_SHARED_FLAG_COL] == "S"
    assert tx2_res[TRANS_SPLIT_PERC_COL] == 100.0


def test_sync_txn_id_not_in_transactions_is_ignored():
    df_trans = sample_transactions_df()  # Has TX1-TX5
    # Queue has decision for TX_UNKNOWN
    queue_data = {
        QUEUE_TXNID_COL: ["TX_UNKNOWN"],
        QUEUE_DECISION_COL: ["Y"],
        QUEUE_SPLIT_COL: [None],
    }
    df_queue = pd.DataFrame(queue_data)
    result_df = sync_review_decisions(df_trans.copy(), df_queue)
    # Result should be identical to original df_trans as TX_UNKNOWN is not in df_trans
    assert_frame_equal(
        result_df.reset_index(drop=True), df_trans.reset_index(drop=True)
    )


def test_sync_case_insensitivity_and_whitespace_in_decision():
    df_trans = sample_transactions_df()
    # TX1: decision ' y '
    queue_data = {
        QUEUE_TXNID_COL: ["TX1"],
        QUEUE_DECISION_COL: [" y "],
        QUEUE_SPLIT_COL: [None],
    }
    df_queue = pd.DataFrame(queue_data)
    result_df = sync_review_decisions(df_trans.copy(), df_queue)

    tx1_res = result_df[result_df[TRANS_TXNID_COL] == "TX1"].iloc[0]
    assert tx1_res[TRANS_SHARED_FLAG_COL] == "Y"  # Standardized to 'Y'
    assert pd.isna(tx1_res[TRANS_SPLIT_PERC_COL])


def test_sync_preserves_other_columns():
    df_trans = sample_transactions_df()
    original_desc_amount = df_trans[[TRANS_TXNID_COL, "Description", "Amount"]].copy()

    queue_data = {
        QUEUE_TXNID_COL: ["TX1"],
        QUEUE_DECISION_COL: ["Y"],
        QUEUE_SPLIT_COL: [None],
    }
    df_queue = pd.DataFrame(queue_data)
    result_df = sync_review_decisions(df_trans.copy(), df_queue)

    # Merge original non-synced columns with result to check they are unchanged
    # Need to ensure dtypes are consistent for merge if TxnID was changed
    result_desc_amount = result_df[[TRANS_TXNID_COL, "Description", "Amount"]]

    # Sort by TxnID before comparing to ensure row order doesn't matter
    original_desc_amount = original_desc_amount.sort_values(
        by=TRANS_TXNID_COL
    ).reset_index(drop=True)
    result_desc_amount = result_desc_amount.sort_values(by=TRANS_TXNID_COL).reset_index(
        drop=True
    )

    assert_frame_equal(result_desc_amount, original_desc_amount)


def test_sync_split_percent_for_non_s_decision_is_ignored():
    """If queue has 'Y' and a SplitPercent value, that SplitPercent should be ignored."""
    df_trans = sample_transactions_df()  # TX1 has SplitPercent=NA initially
    queue_data = {
        QUEUE_TXNID_COL: ["TX1"],
        QUEUE_DECISION_COL: ["Y"],  # Decision is 'Y'
        QUEUE_SPLIT_COL: ["75"],  # Split percent provided but should be ignored
    }
    df_queue = pd.DataFrame(queue_data)
    result_df = sync_review_decisions(df_trans.copy(), df_queue)

    tx1_res = result_df[result_df[TRANS_TXNID_COL] == "TX1"].iloc[0]
    assert tx1_res[TRANS_SHARED_FLAG_COL] == "Y"
    # SplitPercent should remain NA (from original df_trans) because decision was not 'S'
    assert pd.isna(tx1_res[TRANS_SPLIT_PERC_COL])

    # Test case where original SplitPercent was something, e.g. 100.0 for TX4
    df_trans.loc[df_trans[TRANS_TXNID_COL] == "TX4", TRANS_SPLIT_PERC_COL] = 100.0
    queue_data_tx4 = {
        QUEUE_TXNID_COL: ["TX4"],
        QUEUE_DECISION_COL: ["N"],
        QUEUE_SPLIT_COL: ["25"],
    }
    df_queue_tx4 = pd.DataFrame(queue_data_tx4)
    result_df_tx4 = sync_review_decisions(df_trans.copy(), df_queue_tx4)

    tx4_res = result_df_tx4[result_df_tx4[TRANS_TXNID_COL] == "TX4"].iloc[0]
    assert tx4_res[TRANS_SHARED_FLAG_COL] == "N"
    # SplitPercent should remain 100.0 (from original df_trans for TX4)
    assert tx4_res[TRANS_SPLIT_PERC_COL] == 100.0


def test_sync_empty_decision_in_queue_is_ignored():
    df_trans = sample_transactions_df()
    # TX1: decision is empty string, TX2: decision is NaN
    queue_data = {
        QUEUE_TXNID_COL: ["TX1", "TX2"],
        QUEUE_DECISION_COL: ["", np.nan],
        QUEUE_SPLIT_COL: ["50", "50"],  # Split percents are irrelevant here
    }
    df_queue = pd.DataFrame(queue_data)
    result_df = sync_review_decisions(df_trans.copy(), df_queue)

    # TX1 and TX2 should be unchanged from original
    original_tx1_tx2 = df_trans[df_trans[TRANS_TXNID_COL].isin(["TX1", "TX2"])]
    result_tx1_tx2 = result_df[result_df[TRANS_TXNID_COL].isin(["TX1", "TX2"])]
    assert_frame_equal(
        result_tx1_tx2.reset_index(drop=True), original_tx1_tx2.reset_index(drop=True)
    )
