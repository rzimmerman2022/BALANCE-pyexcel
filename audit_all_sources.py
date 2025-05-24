import pandas as pd
from pathlib import Path
from collections import Counter, defaultdict
import json
import re # For _canon if used directly

# Attempt to import from the project structure
try:
    from src.balance_pipeline.schema_registry import find_matching_schema, _canon
    from src.balance_pipeline.rules_engine import load_schema_rules_from_file # Assuming a way to get rules
except ImportError:
    print("WARNING: Could not import project modules. Schema matching capabilities will be limited.")
    # Define _canon locally if import fails, for header normalization
    _NON_ALNUM_AUDIT = re.compile(r"[^a-z0-9\s]")
    def _canon(text: str) -> str:
        text = _NON_ALNUM_AUDIT.sub("", str(text).lower()).strip()
        return re.sub(r"\s+", " ", text)
    
    find_matching_schema = None
    load_schema_rules_from_file = None

# Define the 5 source CSV files
# Paths are relative to the project root (c:/BALANCE/BALANCE-pyexcel)
# User confirmed CSVs are in c:\balance\csvs
BASE_CSV_PATH = Path("../csvs") 
SOURCE_CSV_FILES = [
    BASE_CSV_PATH / "Jordyn/Jordyn - Chase Bank - Total Checking x6173 - All.csv",
    BASE_CSV_PATH / "Jordyn/Jordyn - Discover - Discover It Card x1544 - CSV.csv",
    BASE_CSV_PATH / "Jordyn/Jordyn - Wells Fargo - Active Cash Visa Signature Card x4296 - CSV.csv",
    BASE_CSV_PATH / "Ryan/Ryan - Monarch Money - 20250412.csv",
    BASE_CSV_PATH / "Ryan/Ryan - Rocket Money - 20250412.csv",
]

# Global store for column statistics
# Structure:
# {
#   "canonical_column_name_suggestion": {
#     "original_names": {"source_file_A": "RawName1", "source_file_B": "RawName2"},
#     "sources_present_in": ["source_file_A", "source_file_B"],
#     "total_records_in_sources_present": 1500, # Sum of records in files where this column concept exists
#     "total_non_null_overall": 1200,
#     "overall_coverage_percentage": 80.0,
#     "per_source_details": {
#       "source_file_A": {"original_name": "RawName1", "non_null_count": 700, "total_rows": 1000, "completeness_pc": 70.0, "dtypes": {"str": 1000}},
#       "source_file_B": {"original_name": "RawName2", "non_null_count": 500, "total_rows": 500, "completeness_pc": 100.0, "dtypes": {"str": 500}},
#     },
#     "global_dtypes": {"str": 1500},
#     "unique_values_sample": ["val1", "val2"] # Global sample
#   }
# }
COLUMN_STATS = defaultdict(lambda: {
    "original_names": {},
    "sources_present_in": [],
    "total_records_in_sources_present": 0,
    "total_non_null_overall": 0,
    "overall_coverage_percentage": 0.0,
    "per_source_details": {},
    "global_dtypes": Counter(),
    "unique_values_sample": set() # Using set to collect unique samples
})

UNMAPPED_COLUMNS = defaultdict(list) # {"source_file_A": ["UnmappedCol1", "UnmappedCol2"]}

def get_column_samples(series: pd.Series, num_samples=5) -> list:
    """Get a few unique, non-null sample values from a series."""
    return series.dropna().unique()[:num_samples].tolist()

def analyze_csv_file(file_path: Path, file_index: int):
    """Analyzes a single CSV file and updates global statistics."""
    absolute_file_path = file_path.resolve(strict=False)
    print(f"\n--- Analyzing file ({file_index+1}/{len(SOURCE_CSV_FILES)}): {file_path.name} ---")
    print(f"Attempting to access: {absolute_file_path}")

    if not absolute_file_path.exists():
        print(f"ERROR: File not found at resolved path: {absolute_file_path}")
        # As a fallback, try to list contents of the parent directory to help diagnose
        parent_dir = absolute_file_path.parent
        if parent_dir.exists():
            print(f"Contents of parent directory ({parent_dir}):")
            try:
                for item in parent_dir.iterdir():
                    print(f"  - {item.name}")
            except Exception as e_dir:
                print(f"    Could not list parent directory contents: {e_dir}")
        else:
            print(f"Parent directory {parent_dir} also does not exist.")
        return

    try:
        # Read CSV, keeping all data as string initially to inspect raw values
        df = pd.read_csv(absolute_file_path, dtype=str, keep_default_na=False) # keep_default_na=False to see empty strings
        df = df.replace('', pd.NA) # Treat empty strings as NA for consistency in .isna()/.notna()
    except Exception as e:
        print(f"ERROR: Could not read CSV {absolute_file_path.name}: {e}")
        return

    if df.empty:
        print(f"INFO: File {file_path.name} is empty or contains only headers.")
        return

    total_rows_in_file = len(df)
    print(f"INFO: Read {total_rows_in_file} rows, {len(df.columns)} columns from {file_path.name}.")

    # Attempt to find a matching schema from the project's rules
    matched_schema_info = None
    current_schema_rules = None
    current_column_map = {} # raw_original_header -> canonical_name

    if find_matching_schema:
        try:
            # find_matching_schema might return MatchResult or Dict or None
            match_result_or_dict = find_matching_schema(df.columns.tolist(), filename=file_path.name)
            if match_result_or_dict:
                if hasattr(match_result_or_dict, 'rules'): # MatchResult object
                    current_schema_rules = match_result_or_dict.rules
                    matched_schema_info = {"id": current_schema_rules.get("id", "N/A"), "type": "MatchResult"}
                elif isinstance(match_result_or_dict, dict): # Raw dict (e.g. from test shim)
                    current_schema_rules = match_result_or_dict
                    matched_schema_info = {"id": current_schema_rules.get("id", "N/A"), "type": "Dict"}
                
                if current_schema_rules:
                    raw_col_map = current_schema_rules.get("column_map", {})
                    # Normalize keys of column_map for matching against normalized df headers
                    current_column_map = {_canon(k): v for k, v in raw_col_map.items()}
                    print(f"INFO: Matched to schema: {matched_schema_info['id']}")
                else:
                    print(f"INFO: No specific schema rules found from match result for {file_path.name}.")
            else:
                print(f"INFO: No schema matched for {file_path.name}. Analyzing raw columns.")
        except Exception as e:
            print(f"WARNING: Error during schema matching for {file_path.name}: {e}")
    else:
        print("INFO: Schema matching disabled (project modules not imported). Analyzing raw columns.")

    file_unmapped_cols = []

    for original_col_name in df.columns:
        col_series = df[original_col_name]
        non_null_count = col_series.notna().sum()
        completeness_pc = (non_null_count / total_rows_in_file) * 100 if total_rows_in_file > 0 else 0
        
        # Determine canonical name: from schema map, or canonized original name
        canon_original_col_name = _canon(original_col_name)
        canonical_name_suggestion = current_column_map.get(canon_original_col_name, canon_original_col_name)

        if canon_original_col_name not in current_column_map and matched_schema_info : # Only consider unmapped if a schema was attempted
             file_unmapped_cols.append(original_col_name)

        # Update global stats
        stat_entry = COLUMN_STATS[canonical_name_suggestion]
        stat_entry["original_names"][file_path.name] = original_col_name
        if file_path.name not in stat_entry["sources_present_in"]:
            stat_entry["sources_present_in"].append(file_path.name)
        
        stat_entry["total_records_in_sources_present"] += total_rows_in_file # This will overcount if called multiple times for same file, but structure is per-column
        stat_entry["total_non_null_overall"] += non_null_count
        
        # Per-source details
        source_detail = stat_entry["per_source_details"].get(file_path.name, {})
        source_detail["original_name"] = original_col_name
        source_detail["non_null_count"] = non_null_count
        source_detail["total_rows"] = total_rows_in_file
        source_detail["completeness_pc"] = completeness_pc
        source_detail["dtypes"] = col_series.apply(type).value_counts().to_dict()
        source_detail["unique_samples"] = get_column_samples(col_series)
        stat_entry["per_source_details"][file_path.name] = source_detail

        # Global dtypes and samples
        for dtype, count in source_detail["dtypes"].items():
            stat_entry["global_dtypes"][dtype] += count
        for sample in source_detail["unique_samples"]:
            if len(stat_entry["unique_values_sample"]) < 10: # Limit global samples
                 stat_entry["unique_values_sample"].add(str(sample)) # Store as string

    if file_unmapped_cols:
        UNMAPPED_COLUMNS[file_path.name].extend(file_unmapped_cols)
        print(f"INFO: Unmapped columns for {file_path.name} (based on schema '{matched_schema_info['id'] if matched_schema_info else 'N/A'}'): {file_unmapped_cols}")


def finalize_and_print_report():
    """Finalizes overall statistics and prints the report."""
    print("\n\n--- Overall Column Analysis Report ---")

    # Finalize overall coverage percentages
    # This needs careful thought: total_records_in_sources_present is sum of all rows in files where column *concept* appears.
    # This is not right. It should be:
    # For each canonical_name_suggestion:
    #   total_rows_across_all_sources = sum of len(df) for all 5 files. (Constant for all columns)
    #   total_non_null_for_this_column_concept_globally = sum of non_null_count from each source where it (or its alias) appears.
    
    # Let's recalculate overall coverage more accurately.
    # total_rows_in_all_processed_files = sum(details["total_rows"] for file_details_map in COLUMN_STATS.values() for details in file_details_map["per_source_details"].values())
    # This is still tricky. Let's use a simpler sum of non-nulls / sum of rows where column *could* appear.

    sorted_column_names = sorted(COLUMN_STATS.keys())

    report_sections = {
        "core": [], # >90% overall coverage, present in most sources
        "optional": [], # valuable but source-specific or lower coverage
        "low_coverage_or_rare": [], # <10% overall coverage or very few sources
    }
    
    grand_total_records_processed = 0
    temp_file_lengths = {}
    for file_path in SOURCE_CSV_FILES:
        if file_path.exists():
            try:
                df_temp = pd.read_csv(file_path, dtype=str, keep_default_na=False)
                temp_file_lengths[file_path.name] = len(df_temp)
                grand_total_records_processed += len(df_temp)
            except:
                temp_file_lengths[file_path.name] = 0


    for name in sorted_column_names:
        stats = COLUMN_STATS[name]
        
        # Recalculate overall coverage
        # Sum of non-nulls for this column concept across all files it appeared in
        global_non_null_count = stats["total_non_null_overall"] # This is already sum of non_nulls from per_source_details
        
        # Sum of total rows from only the files where this column concept was present
        total_rows_in_relevant_sources = 0
        for source_file_name in stats["sources_present_in"]:
            total_rows_in_relevant_sources += temp_file_lengths.get(source_file_name, 0)

        stats["overall_coverage_percentage"] = (global_non_null_count / total_rows_in_relevant_sources) * 100 if total_rows_in_relevant_sources > 0 else 0
        
        # Categorize
        overall_cov = stats["overall_coverage_percentage"]
        num_sources = len(stats["sources_present_in"])

        category = "optional" # Default
        if overall_cov > 90 and num_sources >= len(SOURCE_CSV_FILES) * 0.6: # Present in >= 60% of sources
            category = "core"
        elif overall_cov < 10 or num_sources == 1:
            category = "low_coverage_or_rare"
        
        report_entry = f"\nCanonical Name Suggestion: \"{name}\"\n"
        report_entry += f"  Overall Coverage: {stats['overall_coverage_percentage']:.2f}% (across {total_rows_in_relevant_sources} rows in {num_sources} sources)\n"
        report_entry += f"  Global Non-Null Count: {global_non_null_count}\n"
        report_entry += f"  Sources Present In ({num_sources}): {', '.join(stats['sources_present_in'])}\n"
        report_entry += f"  Original Names Map: {json.dumps(stats['original_names'])}\n"
        report_entry += "  Per-Source Details:\n"
        for fname, details in stats["per_source_details"].items():
            report_entry += f"    - {fname}: Orig='{details['original_name']}', Non-Nulls={details['non_null_count']}/{details['total_rows']} ({details['completeness_pc']:.2f}%), Dtypes={details['dtypes']}, Samples={details['unique_samples']}\n"
        report_entry += f"  Global Data Types Observed: {stats['global_dtypes']}\n"
        report_entry += f"  Global Unique Samples: {list(stats['unique_values_sample'])}\n"
        
        report_sections[category].append(report_entry)

    print("\n--- Proposed Canonical Schema Categories ---")
    for cat_name, entries in report_sections.items():
        print(f"\n## {cat_name.upper()} COLUMNS ({len(entries)}) ##")
        if entries:
            for entry_text in entries:
                print(entry_text)
        else:
            print("  (No columns in this category)")

    print("\n\n--- Unmapped Columns By Source (if schemas were matched) ---")
    if UNMAPPED_COLUMNS:
        for source_file, unmapped_list in UNMAPPED_COLUMNS.items():
            print(f"  {source_file}: {unmapped_list}")
    else:
        print("  No unmapped columns recorded (or no schemas were matched to sources).")

    print("\n--- End of Report ---")


if __name__ == "__main__":
    # Ensure project modules can be found if script is run directly
    import sys
    # Add project root to sys.path if not already there
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Re-attempt imports if they failed initially, now that path might be set
    if find_matching_schema is None:
        try:
            from src.balance_pipeline.schema_registry import find_matching_schema, _canon
            print("Successfully re-imported project modules in __main__.")
        except ImportError:
            print("WARNING: Failed to re-import project modules in __main__.")


    for i, file_path in enumerate(SOURCE_CSV_FILES):
        analyze_csv_file(file_path, i)
    
    finalize_and_print_report()

    # Suggestion for canonical schema YAML structure (to be manually created from report)
    print("\n\n--- Suggested Canonical Schema YAML Structure (for manual creation) ---")
    print("""
# canonical_schema.yml
# Based on audit_all_sources.py report

# required_columns:
#   - Name: Date
#     Rationale: "100% overall coverage, present in 5/5 sources. Key transactional field."
#     Originals: {"file1.csv": "Transaction Date", "file2.csv": "Date"} # Example
#   - Name: Amount
#     Rationale: "..."
#     Originals: {"file1.csv": "Transaction Amount", "file2.csv": "Value"}

# optional_columns:
#   - Name: Tags
#     Rationale: "30% overall coverage, present in 2/5 sources (Monarch, etc.). Valuable for categorization where available."
#     Originals: {"monarch.csv": "Tags"}
#   - Name: AccountLast4
#     Rationale: "Present only in card sources, ~60% coverage in those. Useful for account identification."
#     Originals: {"card1.csv": "Account Ending In"}

# columns_to_consider_removing_or_map_to_extras:
#   - Name: InternalSystemID
#     Rationale: "<5% overall coverage, only in 1 source, seems internal."
#     Originals: {"legacy_system.csv": "SYS_ID"}
    """)
