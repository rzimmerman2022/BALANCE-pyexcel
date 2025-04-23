# tests/test_sync.py
import pytest
import pandas as pd
from datetime import datetime
from balance_pipeline.sync import sync_review_decisions
from balance_pipeline.sync import QUEUE_TXNID_COL, QUEUE_DECISION_COL, QUEUE_SPLIT_COL
from balance_pipeline.sync import TRANS_TXNID_COL, TRANS_SHARED_FLAG_COL, TRANS_SPLIT_PERC_COL

# Sample test transaction data
@pytest.fixture
def sample_transactions():
    """Fixture providing a sample transactions DataFrame for testing."""
    return pd.DataFrame({
        'TxnID': ['tx001', 'tx002', 'tx003', 'tx004', 'tx005'],
        'Owner': ['Ryan', 'Jordyn', 'Ryan', 'Jordyn', 'Ryan'],
        'Date': [
            datetime(2025, 4, 1), 
            datetime(2025, 4, 2), 
            datetime(2025, 4, 3), 
            datetime(2025, 4, 4),
            datetime(2025, 4, 5)
        ],
        'Description': [
            'Grocery Store', 
            'Restaurant', 
            'Gas Station', 
            'Online Shopping', 
            'Utility Bill'
        ],
        'Account': [
            'Checking', 
            'Credit Card', 
            'Credit Card', 
            'Checking', 
            'Checking'
        ],
        'Amount': [-120.45, -35.67, -45.50, -89.99, -75.00],
        'SharedFlag': ['?', '?', '?', '?', '?'],
        'SplitPercent': [None, None, None, None, None],
        'Category': ['Groceries', 'Dining', 'Transportation', 'Shopping', 'Utilities']
    })

# Sample queue review data
@pytest.fixture
def sample_queue_review():
    """Fixture providing a sample Queue_Review DataFrame for testing."""
    return pd.DataFrame({
        'TxnID': ['tx001', 'tx002', 'tx003', 'tx004'],
        'Set Shared? (Y/N/S for Split)': ['Y', 'N', 'S', ''],  # Last one empty (no decision)
        'Set Split % (0-100)': [None, None, 75, None]
    })

def test_sync_review_decisions(sample_transactions, sample_queue_review):
    """Test that decisions from Queue_Review are correctly synced to Transactions."""
    
    # Call the function under test
    result = sync_review_decisions(sample_transactions, sample_queue_review)
    
    # Assertions to verify function behavior
    
    # 1. Check that the original DataFrame wasn't modified
    assert sample_transactions.loc[0, TRANS_SHARED_FLAG_COL] == '?'
    assert pd.isna(sample_transactions.loc[0, TRANS_SPLIT_PERC_COL])
    
    # 2. Check that the result has the correct number of rows
    assert len(result) == len(sample_transactions)
    
    # 3. Check that decisions were applied correctly
    assert result.loc[0, TRANS_SHARED_FLAG_COL] == 'Y'  # Shared = Y
    assert pd.isna(result.loc[0, TRANS_SPLIT_PERC_COL]) # No split value for Y
    
    assert result.loc[1, TRANS_SHARED_FLAG_COL] == 'N'  # Shared = N
    assert pd.isna(result.loc[1, TRANS_SPLIT_PERC_COL]) # No split value for N
    
    assert result.loc[2, TRANS_SHARED_FLAG_COL] == 'S'  # Shared = S (split)
    assert result.loc[2, TRANS_SPLIT_PERC_COL] == 75    # Split = 75%
    
    # 4. Check that rows without decisions were left unchanged
    assert result.loc[3, TRANS_SHARED_FLAG_COL] == '?'  # No decision (empty string)
    assert pd.isna(result.loc[3, TRANS_SPLIT_PERC_COL])
    
    assert result.loc[4, TRANS_SHARED_FLAG_COL] == '?'  # No entry in queue review
    assert pd.isna(result.loc[4, TRANS_SPLIT_PERC_COL])

def test_sync_empty_queue():
    """Test that function handles empty queue review gracefully."""
    transactions = pd.DataFrame({
        'TxnID': ['tx001'],
        'SharedFlag': ['?'],
        'SplitPercent': [None]
    })
    queue_review = pd.DataFrame(columns=['TxnID', 'Set Shared? (Y/N/S for Split)', 'Set Split % (0-100)'])
    
    result = sync_review_decisions(transactions, queue_review)
    
    assert len(result) == 1
    assert result.loc[0, 'SharedFlag'] == '?'
    assert pd.isna(result.loc[0, 'SplitPercent'])

def test_sync_invalid_decisions():
    """Test that function handles invalid decisions gracefully."""
    transactions = pd.DataFrame({
        'TxnID': ['tx001', 'tx002', 'tx003'],
        'SharedFlag': ['?', '?', '?'],
        'SplitPercent': [None, None, None]
    })
    queue_review = pd.DataFrame({
        'TxnID': ['tx001', 'tx002', 'tx003'],
        'Set Shared? (Y/N/S for Split)': ['X', 'S', 'S'],  # Invalid value
        'Set Split % (0-100)': [None, -10, 120]  # Invalid percentages
    })
    
    result = sync_review_decisions(transactions, queue_review)
    
    # Invalid shared flag should be ignored
    assert result.loc[0, 'SharedFlag'] == '?'
    assert pd.isna(result.loc[0, 'SplitPercent'])
    
    # Invalid percentages should be corrected to valid range
    assert result.loc[1, 'SharedFlag'] == 'S'
    assert result.loc[1, 'SplitPercent'] == 0  # Clamped to minimum
    
    assert result.loc[2, 'SharedFlag'] == 'S'
    assert result.loc[2, 'SplitPercent'] == 100  # Clamped to maximum

def test_sync_missing_columns():
    """Test that function handles missing columns gracefully."""
    # Missing columns in transactions
    transactions1 = pd.DataFrame({'TxnID': ['tx001']})
    queue_review = pd.DataFrame({
        'TxnID': ['tx001'],
        'Set Shared? (Y/N/S for Split)': ['Y'],
        'Set Split % (0-100)': [None]
    })
    
    result1 = sync_review_decisions(transactions1, queue_review)
    assert len(result1) == 1
    assert 'SharedFlag' not in result1.columns
    
    # Missing columns in queue_review
    transactions2 = pd.DataFrame({
        'TxnID': ['tx001'],
        'SharedFlag': ['?'],
        'SplitPercent': [None]
    })
    queue_review2 = pd.DataFrame({'TxnID': ['tx001']})
    
    result2 = sync_review_decisions(transactions2, queue_review2)
    assert len(result2) == 1
    assert result2.loc[0, 'SharedFlag'] == '?'
    assert pd.isna(result2.loc[0, 'SplitPercent'])
