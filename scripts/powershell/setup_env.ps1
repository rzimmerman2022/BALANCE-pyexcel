# ---------------------------------------------------------------------------
#  setup_env.ps1  –  one-shot venv + dependency sync via Poetry
# ---------------------------------------------------------------------------
# Prereqs:
#   1. Poetry installed  →  pip install poetry  OR  winget install Python.Poetry
#   2. Python 3.11 on PATH (matches the ^3.11 spec in pyproject.toml)
# ---------------------------------------------------------------------------

# 1) Make sure Poetry is available
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Error "❌  Poetry CLI not found.  Install with  'pip install poetry'  then rerun."
    exit 1
}

# 2) Point Poetry at Python 3.11 (creates .venv under ./.venv by default)
Write-Host "🔧  Creating / selecting Poetry venv with Python 3.11 ..."
poetry env use 3.11

# 3) Ensure python-dateutil is in pyproject.toml  ---------------------------
# If it's already listed, Poetry will skip; otherwise it will add + lock.
Write-Host "➕  Adding missing runtime dep: python-dateutil ..."
poetry add python-dateutil --lock

# 4) Install (runtime + dev) deps exactly as declared & lockfile’d ----------
Write-Host "📦  Installing / updating all project dependencies ..."
poetry install

# 5) Show result & how to reactivate later ---------------------------------
$envPath = (poetry env info -p)
Write-Host "`n✅  Environment ready at: $envPath"
Write-Host "   Activate it any time with:`n`n    poetry shell`n"
