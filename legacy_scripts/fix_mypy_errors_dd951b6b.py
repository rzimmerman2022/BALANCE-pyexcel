#!/usr/bin/env python3
"""
MyPy Auto-Fixer: Automatically applies common type annotation fixes to Python code.

This script parses MyPy output and applies safe, automatic fixes for common issues:
- Missing return type annotations
- Path vs str type mismatches
- Implicit Optional types
- set.add() misuse patterns

Usage:
    python fix_mypy_errors.py [--apply] [--mypy-output FILE] [--verbose]
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import difflib
from dataclasses import dataclass


@dataclass
class MypyError:
    """Represents a single MyPy error with its location and type."""
    file: Path
    line: int
    column: int
    error_type: str
    message: str
    
    @classmethod
    def from_mypy_line(cls, line: str) -> Optional['MypyError']:
        """Parse a MyPy output line into an error object."""
        # Pattern: file.py:line:col: error: message  [error-type]
        pattern = r'^(.+?):(\d+):(\d+): error: (.+?)  \[(.+?)\]$'
        match = re.match(pattern, line.strip())
        
        if match:
            return cls(
                file=Path(match.group(1)),
                line=int(match.group(2)),
                column=int(match.group(3)),
                message=match.group(4),
                error_type=match.group(5)
            )
        return None


class PythonSourceFixer:
    """Applies automatic fixes to Python source code based on MyPy errors."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.files_to_fix: Dict[Path, List[MypyError]] = {}
        
    def add_error(self, error: MypyError) -> None:
        """Add an error to be fixed."""
        if error.file not in self.files_to_fix:
            self.files_to_fix[error.file] = []
        self.files_to_fix[error.file].append(error)
    
    def fix_missing_return_annotation(self, source: str, error: MypyError) -> str:
        """Add return type annotations to functions missing them."""
        lines = source.split('\n')
        target_line_idx = error.line - 1
        
        if target_line_idx >= len(lines):
            return source
            
        line = lines[target_line_idx]
        
        # Check if this is a function definition
        if 'def ' in line and ':' in line and '->' not in line:
            # Extract the part before the colon
            def_match = re.match(r'^(\s*def\s+\w+\s*\([^)]*\))\s*:', line)
            if def_match:
                # Determine if this function returns None by checking the body
                return_type = self._infer_return_type(lines, target_line_idx)
                
                # Insert the return type annotation
                new_line = f"{def_match.group(1)} -> {return_type}:"
                
                # Preserve any trailing comment
                if '#' in line:
                    comment_idx = line.index('#')
                    new_line += line[comment_idx:]
                    
                lines[target_line_idx] = new_line
                
                if self.verbose:
                    print(f"  Fixed return annotation in {error.file}:{error.line}")
                    
        return '\n'.join(lines)
    
    def _infer_return_type(self, lines: List[str], func_line_idx: int) -> str:
        """Infer the return type of a function by analyzing its body."""
        # Simple heuristic: look for return statements in the function body
        indent_level = len(lines[func_line_idx]) - len(lines[func_line_idx].lstrip())
        
        for i in range(func_line_idx + 1, len(lines)):
            line = lines[i].strip()
            
            # Stop if we hit another function at the same indent level
            if line.startswith('def ') or line.startswith('class '):
                current_indent = len(lines[i]) - len(lines[i].lstrip())
                if current_indent <= indent_level:
                    break
            
            # Look for return statements
            if line.startswith('return '):
                return_value = line[7:].strip()
                if not return_value or return_value == 'None':
                    return 'None'
                elif return_value.startswith('pd.DataFrame'):
                    return 'pd.DataFrame'
                elif return_value.startswith('['):
                    return 'list'
                elif return_value.startswith('{'):
                    return 'dict'
                else:
                    return 'Any'  # Safe fallback
        
        # No return found, assume None
        return 'None'
    
    def fix_path_str_mismatch(self, source: str, error: MypyError) -> str:
        """Fix Path vs str type mismatches."""
        if 'Path' in error.message and 'str' in error.message:
            lines = source.split('\n')
            target_line_idx = error.line - 1
            
            if target_line_idx < len(lines):
                line = lines[target_line_idx]
                
                # Common patterns to fix
                # Pattern 1: Path() expects str, not Path
                new_line = re.sub(r'Path\(([^)]+)\)', r'Path(str(\1))', line)
                
                # Pattern 2: Function expecting str got Path
                if 'expected "str"' in error.message:
                    # Add str() conversion around Path variables
                    new_line = re.sub(r'(\w+_path)', r'str(\1)', new_line)
                
                if new_line != line:
                    lines[target_line_idx] = new_line
                    if self.verbose:
                        print(f"  Fixed Path/str mismatch in {error.file}:{error.line}")
                        
            return '\n'.join(lines)
        
        return source
    
    def fix_set_add_misuse(self, source: str, error: MypyError) -> str:
        """Fix set.add() misuse where the return value is assigned."""
        if 'set.add' in error.message or 'returns None' in error.message:
            lines = source.split('\n')
            target_line_idx = error.line - 1
            
            if target_line_idx < len(lines):
                line = lines[target_line_idx]
                
                # Pattern: variable = set.add(item)
                match = re.match(r'^(\s*)(\w+)\s*=\s*(.+?)\.add\((.+?)\)', line)
                if match:
                    indent = match.group(1)
                    var_name = match.group(2)
                    set_name = match.group(3)
                    item = match.group(4)
                    
                    # Replace with proper pattern
                    new_lines = [
                        f"{indent}if {item} not in {set_name}:",
                        f"{indent}    {set_name}.add({item})",
                        f"{indent}    {var_name} = True",
                        f"{indent}else:",
                        f"{indent}    {var_name} = False"
                    ]
                    
                    # Replace the single line with multiple lines
                    lines[target_line_idx:target_line_idx+1] = new_lines
                    
                    if self.verbose:
                        print(f"  Fixed set.add() misuse in {error.file}:{error.line}")
                        
            return '\n'.join(lines)
        
        return source
    
    def fix_implicit_optional(self, source: str, error: MypyError) -> str:
        """Fix implicit Optional types by making them explicit."""
        if 'implicit Optional' in error.message:
            lines = source.split('\n')
            target_line_idx = error.line - 1
            
            if target_line_idx < len(lines):
                line = lines[target_line_idx]
                
                # Pattern: param: list[str] = None -> param: list[str] | None = None
                new_line = re.sub(
                    r':\s*([^=]+?)\s*=\s*None',
                    r': \1 | None = None',
                    line
                )
                
                if new_line != line:
                    lines[target_line_idx] = new_line
                    if self.verbose:
                        print(f"  Fixed implicit Optional in {error.file}:{error.line}")
                        
            return '\n'.join(lines)
        
        return source
    
    def apply_fixes(self, dry_run: bool = False) -> Dict[Path, str]:
        """Apply all collected fixes to the source files."""
        fixed_files = {}
        
        for file_path, errors in self.files_to_fix.items():
            if not file_path.exists():
                print(f"Warning: File not found: {file_path}")
                continue
                
            # Read the original source
            original_source = file_path.read_text(encoding='utf-8')
            fixed_source = original_source
            
            # Sort errors by line number (reverse order to avoid line number shifts)
            errors_by_line = sorted(errors, key=lambda e: e.line, reverse=True)
            
            # Apply fixes based on error type
            for error in errors_by_line:
                if error.error_type == 'no-untyped-def':
                    fixed_source = self.fix_missing_return_annotation(fixed_source, error)
                elif error.error_type in ['arg-type', 'assignment']:
                    fixed_source = self.fix_path_str_mismatch(fixed_source, error)
                elif 'set.add' in error.message:
                    fixed_source = self.fix_set_add_misuse(fixed_source, error)
                elif 'implicit Optional' in error.message:
                    fixed_source = self.fix_implicit_optional(fixed_source, error)
            
            # Only save if changes were made
            if fixed_source != original_source:
                if dry_run:
                    print(f"\nChanges for {file_path}:")
                    diff = difflib.unified_diff(
                        original_source.splitlines(keepends=True),
                        fixed_source.splitlines(keepends=True),
                        fromfile=str(file_path),
                        tofile=str(file_path)
                    )
                    sys.stdout.writelines(diff)
                else:
                    file_path.write_text(fixed_source, encoding='utf-8')
                    fixed_files[file_path] = fixed_source
                    print(f"✓ Fixed {file_path}")
        
        return fixed_files


def run_mypy(src_dir: str = "src", strict: bool = True) -> List[str]:
    """Run MyPy and capture its output."""
    cmd = ["poetry", "run", "mypy", src_dir]
    if strict:
        cmd.append("--strict")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        print(f"Error running MyPy: {e}")
        return []


def main() -> None:
    """Main entry point for the MyPy auto-fixer."""
    parser = argparse.ArgumentParser(description="Automatically fix common MyPy errors")
    parser.add_argument(
        "--apply", 
        action="store_true", 
        help="Apply fixes (default is dry-run mode)"
    )
    parser.add_argument(
        "--mypy-output", 
        type=Path,
        help="Path to MyPy output file (if not provided, runs MyPy)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show detailed progress"
    )
    parser.add_argument(
        "--src-dir",
        default="src",
        help="Source directory to check (default: src)"
    )
    
    args = parser.parse_args()
    
    # Get MyPy errors
    if args.mypy_output and args.mypy_output.exists():
        mypy_lines = args.mypy_output.read_text().strip().split('\n')
    else:
        print("Running MyPy to collect errors...")
        mypy_lines = run_mypy(args.src_dir)
    
    # Parse errors
    fixer = PythonSourceFixer(verbose=args.verbose)
    error_count = 0
    
    for line in mypy_lines:
        error = MypyError.from_mypy_line(line)
        if error:
            fixer.add_error(error)
            error_count += 1
    
    if error_count == 0:
        print("✅ No MyPy errors found!")
        return
    
    print(f"\nFound {error_count} MyPy errors across {len(fixer.files_to_fix)} files")
    
    # Apply fixes
    if args.apply:
        print("\nApplying fixes...")
        fixed = fixer.apply_fixes(dry_run=False)
        print(f"\n✓ Fixed {len(fixed)} files")
        
        # Re-run MyPy to check remaining errors
        print("\nRe-running MyPy to check remaining errors...")
        remaining_errors = run_mypy(args.src_dir)
        remaining_count = sum(1 for line in remaining_errors if ': error:' in line)
        
        if remaining_count == 0:
            print("🎉 All MyPy errors fixed!")
        else:
            print(f"\n⚠️  {remaining_count} errors remain (may need manual fixes)")
            for line in remaining_errors:
                if ': error:' in line:
                    print(f"  {line}")
    else:
        print("\nShowing proposed fixes (dry-run mode)...")
        fixer.apply_fixes(dry_run=True)
        print("\n💡 Run with --apply to apply these fixes")


if __name__ == "__main__":
    main()