"""
create_package_structure.py - Sets up the balance_pipeline package structure
Run this from your project root: python create_package_structure.py
"""

from pathlib import Path

def create_package_structure():
    """Create the balance_pipeline package structure with all necessary directories and files."""
    
    # Define the structure we want to create
    directories = [
        "balance_pipeline",
        "balance_pipeline/io",
        "balance_pipeline/core",
        "balance_pipeline/viz",
    ]
    
    # Create each directory
    for dir_path in directories:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {dir_path}")
        
        # Create __init__.py to make it a proper Python package
        init_file = path / "__init__.py"
        init_file.touch(exist_ok=True)
        print(f"  → Added __init__.py")
    
    # Create a config.py file with some starter content
    config_file = Path("balance_pipeline/config.py")
    if not config_file.exists():
        config_content = '''"""Configuration for the balance pipeline."""

from dataclasses import dataclass
from enum import Enum


@dataclass
class AnalysisConfig:
    """Configuration parameters for the analysis."""
    
    RYAN_PCT: float = 0.43
    JORDYN_PCT: float = 0.57
    # Add other config parameters here


class DataQualityFlag(Enum):
    """Enumeration of data quality issues."""
    
    CLEAN = "CLEAN"
    MISSING_DATE = "MISSING_DATE"
    # Add other flags here
'''
        config_file.write_text(config_content)
        print(f"✓ Created config.py with starter content")
    
    print("\n✅ Package structure created successfully!")
    print("\nNext steps:")
    print("1. Move your DataLoaderV23 class to balance_pipeline/io/loaders.py")
    print("2. Move visualization functions to balance_pipeline/viz/charts.py")
    print("3. Move core analysis logic to balance_pipeline/core/analyzer.py")

if __name__ == "__main__":
    create_package_structure()