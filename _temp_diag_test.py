import logging
import sys
from pathlib import Path
# It's good practice to ensure 'src' is in path if PYTHONPATH isn't perfectly handled
# or if the script is run from an unexpected context, though 'set PYTHONPATH=src' should cover it.
# script_dir = Path(__file__).resolve().parent
# project_root = script_dir # Assuming script is in project root
# src_path = project_root / 'src'
# if str(src_path) not in sys.path:
#    sys.path.insert(0, str(src_path))

from balance_pipeline.csv_consolidator import process_csv_files

# Configure logging as requested
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(name)s: %(message)s' # Added %(name)s for better context
)
log = logging.getLogger(__name__)

def main():
    log.debug("Starting diagnostic test script.")
    try:
        # Path to the test CSV, relative to the project root (c:/BALANCE/BALANCE-pyexcel)
        csv_path = Path('fixtures/min_demo.csv')
        
        if not csv_path.exists():
            log.error(f"Test CSV file not found: {csv_path.resolve()}")
            print(f"ERROR: Test CSV file not found at {csv_path.resolve()}", file=sys.stderr)
            sys.exit(1)
        
        log.debug(f"Processing CSV file: {csv_path}")
        result_df = process_csv_files([csv_path])
        
        if result_df is not None:
            print(f"Processed {len(result_df)} rows with full diagnostic tracing.")
            log.debug(f"Successfully processed {len(result_df)} rows.")
        else:
            print("Processing returned None or an empty DataFrame, check logs for errors.")
            log.error("process_csv_files returned None or an empty DataFrame.")

    except ImportError as e:
        log.error(f"ImportError during script execution: {e}. PYTHONPATH might be incorrect or module missing.")
        print(f"ERROR: ImportError: {e}. Check PYTHONPATH and module availability.", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e: # Specifically for the CSV file if Path.exists() check fails somehow
        log.error(f"FileNotFoundError: {e}. Ensure '{csv_path}' exists.")
        print(f"ERROR: FileNotFoundError: {e}. Ensure '{csv_path}' exists.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"ERROR: An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        log.debug("Diagnostic test script finished.")

if __name__ == "__main__":
    main()
