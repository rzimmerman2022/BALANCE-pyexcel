# -*- coding: utf-8 -*-
"""
==============================================================================
Module: cli_merchant.py
Project: BALANCE-pyexcel
Description: CLI sub-commands for managing merchant rules.
==============================================================================
"""
import argparse
import csv
import re
import sys
from pathlib import Path
import logging

# Configure logging
log = logging.getLogger(__name__)

MERCHANT_RULES_FILENAME = "merchant_lookup.csv"
RULES_DIR = "rules" # Relative to project root, or adjust as needed

def get_rules_file_path(project_root: Path = None) -> Path:
    """Determines the path to the merchant_lookup.csv file."""
    if project_root is None:
        # This assumes the script is run from a context where Path.cwd() is the project root
        # or that RULES_DIR is accessible from the current working directory.
        # For a poetry script, cwd might be the project root.
        # A more robust solution might involve finding the project root based on a known file/dir.
        project_root = Path.cwd() 
    return project_root / RULES_DIR / MERCHANT_RULES_FILENAME

def add_merchant_rule(pattern: str, canonical_name: str, rules_file: Path = None):
    """
    Adds a new merchant rule to the merchant_lookup.csv file.

    Args:
        pattern (str): The regex pattern to match.
        canonical_name (str): The canonical merchant name.
        rules_file (Path, optional): Path to the rules CSV. Defaults to standard location.
    """
    if rules_file is None:
        rules_file = get_rules_file_path()

    # Sanitize canonical_name: reject if it contains a comma
    if ',' in canonical_name:
        log.error("Error: Canonical name cannot contain a comma.")
        print("Error: Canonical name cannot contain a comma.", file=sys.stderr)
        sys.exit(1)

    # Validate regex pattern
    try:
        re.compile(pattern)
    except re.error as e:
        log.error(f"Error: Invalid regex pattern: {pattern}. Details: {e}")
        print(f"Error: Invalid regex pattern: '{pattern}'. Details: {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure the rules directory exists
    rules_file.parent.mkdir(parents=True, exist_ok=True)

    file_exists = rules_file.exists()
    
    try:
        with open(rules_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists or rules_file.stat().st_size == 0:
                writer.writerow(["pattern", "canonical"])
                log.info(f"Created new rules file with header: {rules_file}")
            
            writer.writerow([pattern, canonical_name])
        log.info(f"Rule added: '{pattern}' -> '{canonical_name}' to {rules_file}")
        print("Rule added - Refresh in Excel to apply.") # Standard output for user
    except IOError as e:
        log.error(f"Error writing to rules file {rules_file}: {e}")
        print(f"Error: Could not write to rules file {rules_file}. Details: {e}", file=sys.stderr)
        sys.exit(1)


def main_merchant():
    """
    Main entry point for 'balance merchant' sub-commands.
    """
    parser = argparse.ArgumentParser(
        description="Manage merchant lookup rules for BALANCE-pyexcel.",
        prog="balance merchant" # Ensures help message shows 'balance merchant ...'
    )
    subparsers = parser.add_subparsers(dest="command", title="Available commands", required=True)

    # --- 'add' command ---
    add_parser = subparsers.add_parser(
        "add", 
        help="Add a new merchant rule.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    add_parser.add_argument("pattern", help="Regex pattern to match the merchant.")
    add_parser.add_argument("canonical", help="Canonical merchant name to assign.")
    # Optional: add --rules-file argument if needed for testing or custom locations
    # add_parser.add_argument("--rules-file", type=Path, help="Custom path to the merchant rules CSV file.")


    # --- Setup basic logging for the merchant CLI if not already configured ---
    # This is a simple setup. A more robust solution would integrate with cli.py's setup_logging.
    if not logging.getLogger().hasHandlers(): # Check if root logger has handlers
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


    args = parser.parse_args() # sys.argv[1:] is default, for subcommands needs careful parsing

    # Re-parse args specifically for the subcommand if using sys.argv directly
    # For `poetry run balance merchant add ...`, sys.argv will be like:
    # ['.../cli_merchant.py', 'add', '<pattern>', '<canonical>']
    # So, parser.parse_args() should work if this script is the entry point.
    # If this `main_merchant` is called from another script, sys.argv might need slicing.

    if args.command == "add":
        # Determine rules file path. If --rules-file is added, use args.rules_file.
        # For now, using default.
        rules_path = get_rules_file_path() 
        add_merchant_rule(args.pattern, args.canonical, rules_file=rules_path)
    else:
        parser.print_help() # Should not happen if subcommand is required

if __name__ == "__main__":
    # This allows running `python src/balance_pipeline/cli_merchant.py add ...`
    main_merchant()
