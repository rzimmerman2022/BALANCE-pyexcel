"""
==============================================================================
Module: test_merchant_cli.py
Project: BALANCE-pyexcel
Description: Unit tests for the 'balance merchant add' CLI command.
==============================================================================
"""

import csv
import subprocess  # To run CLI commands
from pathlib import Path

import pytest

# Assuming cli_merchant.py is in src/balance_pipeline
from balance_pipeline.cli_merchant import (
    MERCHANT_RULES_FILENAME,
    RULES_DIR,
    add_merchant_rule,
)


@pytest.fixture
def temp_rules_dir(tmp_path: Path) -> Path:
    """Create a temporary rules directory for testing."""
    rules_dir = tmp_path / RULES_DIR
    rules_dir.mkdir(parents=True, exist_ok=True)
    return rules_dir


@pytest.fixture
def temp_rules_file(temp_rules_dir: Path) -> Path:
    """Path to a temporary merchant_lookup.csv file."""
    return temp_rules_dir / MERCHANT_RULES_FILENAME


def run_merchant_cli_add_command(
    pattern: str, canonical: str, cwd: Path
) -> subprocess.CompletedProcess:
    """Helper function to run the 'balance merchant add' command."""
    # Construct the command using poetry run
    # This assumes poetry is available and the project is set up.
    # For unit tests, directly calling the function might be preferred if possible,
    # but testing the CLI entry point is also valuable.
    command = ["poetry", "run", "balance-merchant", "add", pattern, canonical]
    # Capture_output is True to get stdout/stderr
    # text=True decodes stdout/stderr as strings
    # cwd sets the current working directory for the subprocess
    return subprocess.run(command, capture_output=True, text=True, check=False, cwd=cwd)


# Test direct function call for more controlled unit testing
def test_add_merchant_rule_creates_file_with_header(temp_rules_file: Path):
    """Test that add_merchant_rule creates the CSV with a header if it doesn't exist."""
    assert not temp_rules_file.exists()
    add_merchant_rule("Test Pattern", "Test Canonical", rules_file=temp_rules_file)

    assert temp_rules_file.exists()
    with open(temp_rules_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ["pattern", "canonical"]
        row1 = next(reader)
        assert row1 == ["Test Pattern", "Test Canonical"]


def test_add_merchant_rule_appends_to_existing_file(temp_rules_file: Path):
    """Test that add_merchant_rule appends to an existing CSV."""
    # Create initial file
    with open(temp_rules_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pattern", "canonical"])
        writer.writerow(["Old Pattern", "Old Canonical"])

    add_merchant_rule("New Pattern", "New Canonical", rules_file=temp_rules_file)

    with open(temp_rules_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert len(rows) == 3  # Header + Old Row + New Row
        assert rows[0] == ["pattern", "canonical"]
        assert rows[1] == ["Old Pattern", "Old Canonical"]
        assert rows[2] == ["New Pattern", "New Canonical"]


def test_add_merchant_rule_invalid_regex(temp_rules_file: Path, capsys, caplog):
    """Test add_merchant_rule with an invalid regex pattern."""
    invalid_pattern = "*invalid_regex"
    with pytest.raises(SystemExit) as excinfo:
        add_merchant_rule(invalid_pattern, "Some Canonical", rules_file=temp_rules_file)

    assert excinfo.value.code == 1  # Check for sys.exit(1)
    captured = capsys.readouterr()
    assert f"error: invalid regex pattern: '{invalid_pattern}'".lower() in captured.err.lower()
    assert f"error: invalid regex pattern: {invalid_pattern}".lower() in caplog.text.lower()
    assert not temp_rules_file.exists()  # File should not be created or modified


def test_add_merchant_rule_canonical_with_comma(temp_rules_file: Path, capsys, caplog):
    """Test add_merchant_rule with a comma in the canonical name."""
    canonical_with_comma = "Name, WithComma"
    with pytest.raises(SystemExit) as excinfo:
        add_merchant_rule(
            "Some Pattern", canonical_with_comma, rules_file=temp_rules_file
        )

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "error: canonical name cannot contain a comma." in captured.err.lower()
    assert "error: canonical name cannot contain a comma." in caplog.text.lower()
    assert not temp_rules_file.exists()


# Tests for the CLI command via subprocess
# These tests assume the current working directory for subprocess is the project root.
# You might need to adjust `project_root_for_cli_tests` if tests are run from a different dir.
@pytest.fixture
def project_root_for_cli_tests(tmp_path: Path) -> Path:
    """
    Simulates a project root structure for CLI tests.
    Copies pyproject.toml and creates src/balance_pipeline for poetry run to work.
    """
    # This fixture needs to ensure that `poetry run` can find the script.
    # Copy the main pyproject.toml to the tmp_path to allow `poetry run` to work.
    # This assumes the tests are run from a context where the main pyproject.toml is accessible.
    # A more robust solution might involve a minimal pyproject.toml for tests.
    main_project_root = Path(
        __file__
    ).parent.parent  # Assuming tests/ is one level down from project root
    pyproject_toml_path = main_project_root / "pyproject.toml"
    if pyproject_toml_path.exists():
        import shutil

        shutil.copy(pyproject_toml_path, tmp_path / "pyproject.toml")
    else:
        # Fallback or warning if main pyproject.toml isn't found easily
        # This might happen if test structure changes.
        # For now, we'll proceed, but poetry run might fail if it's not copied.
        print(
            f"Warning: Could not find main pyproject.toml at {pyproject_toml_path} to copy for CLI test."
        )

    # Create a temporary rules directory within the simulated project root (tmp_path)
    rules_dir = tmp_path / RULES_DIR
    rules_dir.mkdir(parents=True, exist_ok=True)

    # Create a dummy src structure for poetry to find the package
    src_dir = tmp_path / "src"
    balance_pipeline_dir = src_dir / "balance_pipeline"
    balance_pipeline_dir.mkdir(parents=True, exist_ok=True)
    (balance_pipeline_dir / "__init__.py").touch()
    # If cli_merchant.py is directly invoked or needed for pathing, copy it too.
    # For now, __init__.py might be enough for `poetry run` to set up paths.

    return tmp_path  # Use tmp_path as the cwd for the subprocess


def test_cli_merchant_add_happy_path(project_root_for_cli_tests: Path):
    """Test 'balance merchant add' happy path via CLI."""
    rules_file = project_root_for_cli_tests / RULES_DIR / MERCHANT_RULES_FILENAME
    assert not rules_file.exists()

    pattern = "^AMAZON\\s*MKTP"
    canonical = "Amazon Marketplace"

    result = run_merchant_cli_add_command(
        pattern, canonical, cwd=project_root_for_cli_tests
    )

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0
    assert "Rule added - Refresh in Excel to apply." in result.stdout

    assert rules_file.exists()
    with open(rules_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert len(rows) == 2  # Header + 1 rule
        assert rows[0] == ["pattern", "canonical"]
        assert rows[1] == [pattern, canonical]


def test_cli_merchant_add_invalid_regex(project_root_for_cli_tests: Path):
    """Test 'balance merchant add' with invalid regex via CLI."""
    rules_file = project_root_for_cli_tests / RULES_DIR / MERCHANT_RULES_FILENAME
    invalid_pattern = "TestPattern["
    canonical = "Test Canonical"

    result = run_merchant_cli_add_command(
        invalid_pattern, canonical, cwd=project_root_for_cli_tests
    )

    assert result.returncode == 1
    assert f"Error: Invalid regex pattern: '{invalid_pattern}'" in result.stderr
    assert not rules_file.exists()  # File should not be created on error


def test_cli_merchant_add_canonical_with_comma(project_root_for_cli_tests: Path):
    """Test 'balance merchant add' with comma in canonical name via CLI."""
    rules_file = project_root_for_cli_tests / RULES_DIR / MERCHANT_RULES_FILENAME
    pattern = "TestPattern"
    canonical_with_comma = "Test,Canonical"

    result = run_merchant_cli_add_command(
        pattern, canonical_with_comma, cwd=project_root_for_cli_tests
    )

    assert result.returncode == 1
    assert "Error: Canonical name cannot contain a comma." in result.stderr
    assert not rules_file.exists()
