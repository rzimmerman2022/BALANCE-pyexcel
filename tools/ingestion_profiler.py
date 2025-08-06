import json
import pathlib
import re

import pandas as pd


def money(v):
    v = str(v)
    cleaned = re.sub(r'[^0-9.\\-]', '', v)
    if cleaned in ('', '-'):
        return 0.0
    return float(cleaned)

def profile_expense_history(path: pathlib.Path):
    """
    Custom profiler for Expense_History.csv.
    This file has multiple sections, each with its own header.
    """
    with open(path, encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    data_blocks = []
    header_indices = [i for i, line in enumerate(lines) if 'Date of Purchase' in line]

    for i, header_index in enumerate(header_indices):
        start_index = header_index
        end_index = header_indices[i+1] if i+1 < len(header_indices) else len(lines)
        block_lines = lines[start_index:end_index]
        
        # Skip empty blocks
        if not any(l.strip() for l in block_lines[1:]):
            continue

        # Use a file-like object to read the block into pandas
        from io import StringIO
        block_io = StringIO("".join(block_lines))
        df = pd.read_csv(block_io)
        data_blocks.append(df)

    if not data_blocks:
        return {'error': 'No data blocks found'}

    df = pd.concat(data_blocks, ignore_index=True)
    df.columns = [c.strip().lower() for c in df.columns]

    actual_col = next((c for c in df.columns if 'actual amount' in c), None)
    allowed_col = next((c for c in df.columns if 'allowed amount' in c), None)
    person_col = next((c for c in df.columns if c == 'name'), 'Unknown')

    if not actual_col or not allowed_col:
        return {'error': 'Could not find amount columns'}

    df['actual_amount_parsed'] = df[actual_col].fillna('0').map(money)
    df['allowed_amount_parsed'] = df[allowed_col].fillna('0').map(money)
    df['person'] = df[person_col].fillna('Unknown') if person_col != 'Unknown' else 'Unknown'

    non_zero_rows = df[(df['actual_amount_parsed'] != 0) | (df['allowed_amount_parsed'] != 0)]
    
    return {
        'total_rows': len(df),
        'zero_value_rows': len(df) - len(non_zero_rows),
        'non_zero_rows': len(non_zero_rows)
    }

def profile_transaction_ledger(path: pathlib.Path):
    """Custom profiler for Transaction_Ledger.csv."""
    # This file seems to have a different structure.
    # For now, we'll just report that it needs a custom parser.
    return {'status': 'needs_custom_parser', 'total_rows': len(pd.read_csv(path, on_bad_lines='skip'))}

def profile_rent_allocation(path: pathlib.Path):
    """Custom profiler for Rent_Allocation.csv."""
    df = pd.read_csv(path)
    return {'total_rows': len(df), 'status': 'parsed_ok'}

def profile_rent_history(path: pathlib.Path):
    """Custom profiler for Rent_History.csv."""
    df = pd.read_csv(path)
    return {'total_rows': len(df), 'status': 'parsed_ok'}


def main():
    """
    Main function to profile all CSVs in the data directory.
    """
    output = {}
    profilers = {
        'Expense_History_20250527.csv': profile_expense_history,
        'Transaction_Ledger_20250527.csv': profile_transaction_ledger,
        'Rent_Allocation_20250527.csv': profile_rent_allocation,
        'Rent_History_20250527.csv': profile_rent_history,
    }
    
    data_dir = pathlib.Path('data')
    for filename, profiler_func in profilers.items():
        path = data_dir / filename
        if path.exists():
            result = profiler_func(path)
            output[filename] = result
        else:
            output[filename] = {'error': 'File not found'}

    artifacts_dir = pathlib.Path('artifacts')
    artifacts_dir.mkdir(exist_ok=True)
    output_path = artifacts_dir / 'ingestion_profile.json'

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"Profiling complete. Results written to {output_path}")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
