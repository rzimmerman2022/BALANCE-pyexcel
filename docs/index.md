# BALANCE Documentation

**Last Updated**: 2025-08-09  
**Version**: 2.0 - Repository Cleanup & Modernization  
**Project**: Professional Financial Analysis Pipeline

*The open-source pipeline that turns messy bank CSVs into clean Parquet, SQLite, and Power-BI dashboards.*

| Section | What you’ll find |
|---------|------------------|
| **[Quick Start](quick_start.md)** | Clone → `poetry install` → first Excel refresh in five minutes |
| **[Architecture Overview](architecture.md)** | High-level diagram of ingest → normalize → persist → dashboard |
| **[Schema Registry](schema_registry.md)** | How the YAML rules map headers, set sign logic, derive accounts, etc. |
| **[CLI Usage](cli_usage.md)** | Run the pipeline head-less, schedule nightly refreshes, integrate with VBA |
| **[Power BI Integration](power_bi_workflow.md)** | Three methods for Power BI data import with deduplication |
| **[Dispute Analyzer](dispute_analyzer_guide.md)** | Modern GUI for dispute analysis and refund verification |
| **[Developer Guide](developer_setup.md)** | Poetry, pre-commit, tests, CI matrix, Python-in-Excel tips |
| **[FAQ](faq.md)** | Common errors and how to fix them |
| **[Changelog](CHANGELOG.md)** | Version history & notable features |

> **Heads-up:** The full API reference (auto-generated from docstrings) lives under **Reference** in the left-hand navigation bar.

---

### Why BALANCE-pyexcel?

* **One pipeline for every bank.**  YAML-driven schemas mean you add a new institution without touching Python.  
* **Excel-friendly.**  Keep your macro-enabled workbook; BALANCE updates data via a temp file so VBA survives.  
* **Headless or hybrid.**  Use the CLI for automation, or fire the pipeline from a button inside Excel.  
* **Open formats.**  Everything ends up in Parquet + SQLite for easy BI and long-term auditability.  

Happy balancing!  Feel free to open issues or PRs on GitHub if you hit a snag or have an idea.

---

## Recent Updates - Version 2.0

### 🏗️ **Repository Cleanup & Modernization** (2025-08-09)
- **Major Repository Reorganization**: 90% of non-essential files archived to organized `/archive/` structure
- **Modern GUI v2.0**: Enhanced dispute analyzer with professional dark theme, gradient colors, and animated navigation
- **Streamlined Structure**: Reduced from 40+ root files to 10 core files, 50+ scripts to 5 essential utilities
- **Documentation Standardization**: Consistent formatting across all markdown files with timestamps and version info
- **Entry Point Validation**: All documented commands tested and functional

### 🚀 **Previous Major Features**
- **Advanced Deduplication**: 3-stage algorithm removes 30-35% duplicates while preserving unique transactions
- **Power BI Integration**: Three methods for data import with comprehensive documentation
- **External Business Rules Configuration**: Configure settlement keywords, payer splits, and merchant categories via `config/business_rules.yml`
- **Enhanced Test Coverage**: Expanded CSV consolidator test scenarios
- **Production Ready**: All identified production readiness issues resolved