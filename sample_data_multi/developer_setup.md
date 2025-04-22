
---

### **`docs/developer_setup.md`**

```markdown
# Developer Setup

```bash
poetry install --with dev     # 🐍 deps + docs + linters
pre-commit install            # git hooks (black, ruff)
poetry run pytest             # run tests
poetry run mkdocs serve       # live docs at http://127.0.0.1:8000
