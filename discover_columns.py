import pandas as pd

EXP = "data/Expense_History_20250527.csv"
LED = "data/Transaction_Ledger_20250527.csv"

exp_cols = pd.read_csv(EXP, nrows=0).columns.tolist()
led_cols = pd.read_csv(LED, nrows=0).columns.tolist()

print("Expense columns:", exp_cols)
print("Ledger  columns:", led_cols)
