import pandas as pd
import glob

for csv_file in glob.glob("C:/BALANCE/CSVs/**/*.csv", recursive=True):
    print(f"\n{csv_file}:")
    df = pd.read_csv(csv_file, nrows=0)
    print(list(df.columns))