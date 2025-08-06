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

def profile_csv(path: pathlib.Path):
    """
    Profiles a single CSV file to find rows with zero amounts.
    """
    # Heuristic: use first row containing the word "amount" as header else row 0
    hdr_row = 0
    try:
        with path.open(encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if re.search('amount', line, re.I):
                    hdr_row = i
                    break
    except Exception:
        # Fallback for binary or unreadable files
        pass

    try:
        df = pd.read_csv(path, skiprows=hdr_row, dtype=str, encoding='utf-8', on_bad_lines='skip')
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        return {'error': f'Pandas read failed: {e}', 'total_rows': 0}


    # locate amount columns
    actual_cols = [c for c in df.columns if re.search('actual', c)]
    allowed_cols = [c for c in df.columns if re.search('allowed', c)]

    if not actual_cols or not allowed_cols:
        return {'missing_headers': True, 'total_rows': len(df)}

    actual_col = actual_cols[0]
    allowed_col = allowed_cols[0]

    df['actual_amount_parsed'] = df[actual_col].fillna('').map(money)
    df['allowed_amount_parsed'] = df[allowed_col].fillna('').map(money)

    # Identify person column
    person_col_candidates = [c for c in df.columns if c in ['person', 'name']]
    if person_col_candidates:
        df['person'] = df[person_col_candidates[0]].fillna('Unknown')
    else:
        df['person'] = 'Unknown'


    zeros = df[(df['actual_amount_parsed'] == 0) & (df['allowed_amount_parsed'] == 0)]
    summary = zeros.groupby('person').size().to_dict()
    summary['total_rows'] = len(df)
    summary['zero_value_rows'] = len(zeros)

    return summary

def main():
    """
    Main function to profile all CSVs in the data directory.
    """
    output = {}
    data_dir = pathlib.Path('data')
    csv_files = list(data_dir.glob('*.csv'))

    for p in csv_files:
        result = profile_csv(p)
        output[p.name] = result

    artifacts_dir = pathlib.Path('artifacts')
    artifacts_dir.mkdir(exist_ok=True)
    output_path = artifacts_dir / 'zero_value_profile.json'

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"Profiling complete. Results written to {output_path}")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
