import pandas as pd
import warnings

# Ignore specific FutureWarning from pandas about Period[M]
warnings.simplefilter(action='ignore', category=FutureWarning)

# Construct the path relative to the script's location
# Assuming the script is run from the project root
dry_run_csv_path = 'workbook/BALANCE-pyexcel.dry-run.csv'

try:
    df = pd.read_csv(dry_run_csv_path, parse_dates=['Date'])

    # ---- 3 headline KPIs ----
    print("Rows ingested:", len(df))
    print("Date range:   ", df['Date'].min().date(), "→", df['Date'].max().date())
    print("Net cash-flow:", df['Amount'].sum().round(2), "\n")

    # ---- Spend by top 10 categories ----
    # Filter out positive amounts (income) before grouping for spending
    spending_df = df[df['Amount'] < 0].copy()
    top_cats = (spending_df.groupby('Category')['Amount']
                  .sum()
                  .sort_values()
                  .head(10))
    print("Top 10 spending categories:")
    # Check if top_cats is empty before printing
    if not top_cats.empty:
        print(top_cats.to_string(float_format='{:,.2f}'.format))
    else:
        print("No spending categories found.")
    print("\n") # Add a newline for better separation

    # ---- Monthly cash flow trend ----
    # Ensure 'Date' is datetime type before accessing dt accessor
    df['Date'] = pd.to_datetime(df['Date'])
    trend = (df.assign(Month=df['Date'].dt.to_period('M'))
               .groupby('Month')['Amount']
               .sum()
               .round(2))
    print("Monthly net flow:")
    # Check if trend is empty before printing
    if not trend.empty:
        print(trend.tail(6).to_string())
    else:
        print("No monthly data to display.")

except FileNotFoundError:
    print(f"Error: The file {dry_run_csv_path} was not found.")
    print("Please ensure the dry run command executed successfully and created the CSV file.")
except Exception as e:
    print(f"An error occurred: {e}")
