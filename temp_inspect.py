import balance_pipeline.ingest
import os
import sys

print(f"Using ingest file at -> {balance_pipeline.ingest.__file__}")
print(f"ingest.py mtime    -> {os.path.getmtime(balance_pipeline.ingest.__file__)}")
print(f"Python executable  -> {sys.executable}")
