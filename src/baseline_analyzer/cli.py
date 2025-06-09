# src/baseline_analyzer/cli.py
from pathlib import Path

# The build_baseline function will be implemented in src/baseline_analyzer/processing.py
# It needs to load data, apply configurations/rules, run processing pipelines,
# and return a pandas DataFrame.
from .processing import build_baseline 

def main():
  """
  CLI entry point for the baseline analyzer.
  Generates a baseline_snapshot.csv.
  """
  print("Running baseline_analyzer CLI to generate baseline_snapshot.csv...")
  
  # build_baseline() will encapsulate the logic to produce the snapshot DataFrame.
  # This function needs to be defined in baseline_analyzer.processing
  baseline_df = build_baseline()
  
  output_file = Path("baseline_snapshot.csv")
  baseline_df.to_csv(output_file, index=False)
  print(f"Baseline snapshot successfully saved to {output_file.resolve()}")

if __name__ == "__main__":
  main()
