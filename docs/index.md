# BALANCE-pyexcel

*The open-source pipeline that turns messy bank CSVs into clean Parquet, SQLite, and Power-BI dashboards.*

| Section | What you’ll find |
|---------|------------------|
| **[Quick Start](quick_start.md)** | Clone → `poetry install` → first Excel refresh in five minutes |
| **[Architecture Overview](architecture.md)** | High-level diagram of ingest → normalize → persist → dashboard |
| **[Schema Registry](schema_registry.md)** | How the YAML rules map headers, set sign logic, derive accounts, etc. |
| **[CLI Usage](cli_usage.md)** | Run the pipeline head-less, schedule nightly refreshes, integrate with VBA |
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
What changed

Change	Reason
Added Architecture Overview and CLI Usage rows	Reflects the new docs you’ve written.
Added Changelog row	Helps people track releases.
Tightened tag-line & “Why” bullets	Quick elevator pitch for newcomers.
Minor wording tweaks	Consistent tone and parallel phrasing.