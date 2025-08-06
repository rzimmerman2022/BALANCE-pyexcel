#!/usr/bin/env python3
import ast
import json
from pathlib import Path
from typing import Any


def analyze(path: Path) -> list[dict[str, Any]]:
    """Parse Python file and extract function information."""
    print(f"Reading {path}...")
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source)
    functions: list[dict[str, Any]] = []
    
    # Walk through all nodes in the AST
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Count lines properly
            if hasattr(node, 'end_lineno'):
                lines = node.end_lineno - node.lineno + 1
            else:
                lines = 1
                
            functions.append({
                "name": node.name,
                "start_line": node.lineno,
                "end_line": getattr(node, 'end_lineno', node.lineno),
                "lines": lines,
            })
    
    return sorted(functions, key=lambda d: d["lines"], reverse=True)

def main() -> None:
    """Generate analyzer diagnostic report."""
    # Look for analyzer.py in the correct location
    target = Path("src/balance_pipeline/analyzer.py")
    
    if not target.exists():
        print(f"Could not find {target}")
        print("Please run this script from the project root directory")
        return
    
    print(f"Analyzing {target}...")
    print(f"File size: {target.stat().st_size / 1024:.1f} KB")
    
    report = analyze(target)
    
    # Display summary
    print(f"\nFound {len(report)} functions")
    print("\nTop 15 largest functions:")
    print("-" * 70)
    print(f"{'Function Name':<45} {'Lines':>10} {'Location':>15}")
    print("-" * 70)
    
    for func in report[:15]:
        location = f"{func['start_line']}-{func['end_line']}"
        print(f"{func['name']:<45} {func['lines']:>10} {location:>15}")
    
    # Calculate statistics
    total_lines = sum(f['lines'] for f in report)
    avg_lines = total_lines / len(report) if report else 0
    
    print("-" * 70)
    print("\nStatistics:")
    print(f"  Total functions: {len(report)}")
    print(f"  Total function lines: {total_lines}")
    print(f"  Average function size: {avg_lines:.1f} lines")
    print(f"  Functions over 100 lines: {sum(1 for f in report if f['lines'] > 100)}")
    print(f"  Functions over 50 lines: {sum(1 for f in report if f['lines'] > 50)}")
    
    # Save detailed report
    out_dir = Path("analysis_output")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "analyzer_diagnostic.json"
    
    with open(out_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {out_path}")

if __name__ == "__main__":
    main()
