#!/usr/bin/env python3
###############################################################################
# BALANCE-pyexcel – Visualization Extractor
#
# Description : Utility to copy the large visualization functions from
#                analyzer.py into a dedicated module. The original file will
#                import these functions dynamically to keep compatibility.
# Key Concepts: - AST manipulation
#               - Code generation
# Public API  : - main()
# -----------------------------------------------------------------------------
# Change Log
# Date        Author      Type        Note
# 2025-06-08  Codex       add         Initial extractor scaffold
###############################################################################
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable


TARGET_PREFIXES = ["_build_", "_create_visualizations"]


def find_visualization_funcs(tree: ast.Module) -> Iterable[ast.FunctionDef]:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and any(
            node.name.startswith(p) for p in TARGET_PREFIXES
        ):
            yield node


def main() -> None:
    src = Path("analyzer.py")
    if not src.exists():
        raise FileNotFoundError(src)
    text = src.read_text()
    tree = ast.parse(text)

    viz_funcs = list(find_visualization_funcs(tree))
    if not viz_funcs:
        print("No visualization functions found")
        return

    lines = text.splitlines()
    extracted: list[str] = []
    for fn in viz_funcs:
        start, end = fn.lineno - 1, fn.end_lineno
        extracted.extend(lines[start:end])
        lines[start] = f"from visualization_funcs import {fn.name}  # extracted"
        for i in range(start + 1, end):
            lines[i] = ""

    src.write_text("\n".join(lines))

    header = (
        "###############################################################################\n"
        "# BALANCE-pyexcel – Visualization Functions\n"
        "#\n"
        "# AUTO-GENERATED – DO NOT EDIT MANUALLY\n"
        "# Generated by extract_visualizations.py\n"
        "###############################################################################\n"
    )
    out = Path("visualization_funcs.py")
    out.write_text(header + "\n".join(extracted) + "\n")
    print(f"Extracted {len(viz_funcs)} functions to {out}")


if __name__ == "__main__":
    main()
