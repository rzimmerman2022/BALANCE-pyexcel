#!/usr/bin/env python3
###############################################################################
# BALANCE-pyexcel – Analyzer Diagnostic Tool
#
# Description : Parse analyzer.py and generate a JSON report summarizing the
#                size of each function and its direct call dependencies. The
#                report helps identify large sections for potential extraction.
# Key Concepts: - AST parsing
#               - Static analysis
# Public API  : - main()
# -----------------------------------------------------------------------------
# Change Log
# Date        Author      Type        Note
# 2025-06-08  Codex       add         Initial creation
###############################################################################
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, List


def analyze(path: Path) -> List[Dict[str, Any]]:
    source = path.read_text()
    tree = ast.parse(source)
    functions: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            calls = {
                n.func.id
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            }
            functions.append(
                {
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "lines": node.end_lineno - node.lineno + 1,
                    "calls": sorted(calls),
                }
            )
    return sorted(functions, key=lambda d: d["lines"], reverse=True)


def main() -> None:
    """Generate analyzer diagnostic report."""
    target = Path("analyzer.py")
    if not target.exists():
        raise FileNotFoundError(target)
    report = analyze(target)
    out_dir = Path("analysis_output")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "analyzer_diagnostic.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Wrote report to {out_path}")


if __name__ == "__main__":
    main()
