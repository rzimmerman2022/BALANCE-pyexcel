"""
Power BI Data Refresh Pipeline
Generates optimized datasets for Power BI dashboard consumption
"""

import pandas as pd

def generate_powerbi_datasets():
    """Generate comprehensive datasets optimized for Power BI visualization"""
    
    print("🔄 Power BI Data Refresh Pipeline Starting...")
    print("=" * 60)
    
    # Load the most recent integrated audit trail
    try:
        audit_file = "integrated_audit_trail_with_zelle_20250702_103908.csv"
        df = pd.read_csv(audit_file)
        print(f"✅ Loaded audit trail: {len(df)} transactions")
    except Exception as e:
        print(f"❌ Error loading audit trail: {e}")
        return None
    
    # Convert date column
    df['Date'] = pd.to_datetime(df['Date'])
    
    # 1. MONTHLY SUMMARY DATASET
    print("\n📊 Generating Monthly Summary Dataset...")
    monthly_summary = generate_monthly_summary(df)
    monthly_summary.to_csv("powerbi_monthly_summary.csv", index=False)
    print(f"✅ Monthly summary: {len(monthly_summary)} months")
    
    # 2. TRANSACTION DETAILS DATASET (optimized for Power BI)
    print("\n💳 Generating Transaction Details Dataset...")
    transaction_details = generate_transaction_details(df)
    transaction_details.to_csv("powerbi_transaction_details.csv", index=False)
    print(f"✅ Transaction details: {len(transaction_details)} transactions")
    
    # 3. BALANCE HISTORY DATASET
    print("\n📈 Generating Balance History Dataset...")
    balance_history = generate_balance_history(df)
    balance_history.to_csv("powerbi_balance_history.csv", index=False)
    print(f"✅ Balance history: {len(balance_history)} data points")
    
    # 4. CATEGORY ANALYSIS DATASET
    print("\n🏷️ Generating Category Analysis Dataset...")
    category_analysis = generate_category_analysis(df)
    category_analysis.to_csv("powerbi_category_analysis.csv", index=False)
    print(f"✅ Category analysis: {len(category_analysis)} categories")
    
    # 5. CURRENT STATUS SNAPSHOT
    print("\n📸 Generating Current Status Snapshot...")
    status_snapshot = generate_status_snapshot(df)
    status_snapshot.to_csv("powerbi_current_status.csv", index=False)
    print("✅ Current status snapshot generated")
    
    # 6. Generate consolidated Parquet file for high performance
    print("\n🚀 Generating High-Performance Parquet Dataset...")
    df_clean = df.copy()
    df_clean['Year'] = df_clean['Date'].dt.year
    df_clean['Month'] = df_clean['Date'].dt.month
    df_clean['Quarter'] = df_clean['Date'].dt.quarter
    df_clean['DayOfWeek'] = df_clean['Date'].dt.day_name()
    df_clean.to_parquet("powerbi_complete_dataset.parquet", index=False)
    print("✅ High-performance dataset: powerbi_complete_dataset.parquet")
    
    print("\n🎉 Power BI Data Refresh Complete!")
    print("=" * 60)
    return True

def generate_monthly_summary(df):
    """Generate monthly summary statistics"""
    df_monthly = df.copy()
    df_monthly['Year_Month'] = df_monthly['Date'].dt.to_period('M')
    
    monthly = df_monthly.groupby(['Year_Month', 'Person']).agg({
        'Amount_Paid': 'sum',
        'Share_Owed': 'sum',
        'Net_Effect': 'sum',
        'Transaction_Number': 'count'
    }).reset_index()
    
    monthly['Year_Month'] = monthly['Year_Month'].astype(str)
    monthly.columns = ['Month', 'Person', 'Total_Paid', 'Total_Share', 'Net_Effect', 'Transaction_Count']
    
    return monthly

def generate_transaction_details(df):
    """Generate cleaned transaction details for Power BI"""
    details = df.copy()
    
    # Add helpful calculated columns
    details['Amount_Absolute'] = details['Amount_Paid'].abs()
    details['Is_Expense'] = details['Source'] == 'Expense'
    details['Is_Rent'] = details['Source'] == 'Rent'
    details['Is_Zelle'] = details['Source'] == 'Zelle'
    details['Month_Name'] = details['Date'].dt.strftime('%B %Y')
    details['Week_Start'] = details['Date'].dt.to_period('W').dt.start_time
    
    # Clean description for better Power BI visualization
    details['Description_Clean'] = details['Description'].str.slice(0, 100)  # Truncate long descriptions
    
    # Add transaction size categories
    details['Amount_Category'] = pd.cut(details['Amount_Absolute'], 
                                      bins=[0, 25, 100, 500, 1000, float('inf')],
                                      labels=['Small ($0-25)', 'Medium ($25-100)', 'Large ($100-500)', 
                                             'Very Large ($500-1000)', 'Huge ($1000+)'])
    
    return details

def generate_balance_history(df):
    """Generate running balance history for trend analysis"""
    balance_data = []
    
    for person in df['Person'].unique():
        person_df = df[df['Person'] == person].sort_values('Date').copy()
        person_df['Cumulative_Balance'] = person_df['Net_Effect'].cumsum()
        
        for _, row in person_df.iterrows():
            balance_data.append({
                'Date': row['Date'],
                'Person': person,
                'Running_Balance': row['Running_Balance'],
                'Cumulative_Balance': row['Cumulative_Balance'],
                'Daily_Net_Effect': row['Net_Effect']
            })
    
    return pd.DataFrame(balance_data)

def generate_category_analysis(df):
    """Generate category-based analysis"""
    
    # Group by transaction type and source
    analysis = df.groupby(['Transaction_Type', 'Source', 'Person']).agg({
        'Amount_Paid': ['sum', 'count', 'mean'],
        'Share_Owed': 'sum',
        'Net_Effect': 'sum'
    }).reset_index()
    
    # Flatten column names
    analysis.columns = ['Transaction_Type', 'Source', 'Person', 
                       'Total_Amount', 'Count', 'Average_Amount',
                       'Total_Share', 'Net_Effect']
    
    return analysis

def generate_status_snapshot(df):
    """Generate current status snapshot"""
    latest_date = df['Date'].max()
    
    # Get final balances
    final_balances = df.groupby('Person')['Running_Balance'].last().reset_index()
    final_balances['As_Of_Date'] = latest_date
    final_balances['Status'] = final_balances['Running_Balance'].apply(
        lambda x: 'Owes Money' if x < 0 else 'Owed Money' if x > 0 else 'Even'
    )
    
    # Add summary stats
    total_transactions = len(df)
    date_range = f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}"
    
    # Create summary row
    summary_row = {
        'Person': 'SUMMARY',
        'Running_Balance': final_balances['Running_Balance'].sum(),
        'As_Of_Date': latest_date,
        'Status': f'Total Transactions: {total_transactions}, Date Range: {date_range}'
    }
    
    return pd.concat([final_balances, pd.DataFrame([summary_row])], ignore_index=True)

if __name__ == "__main__":
    generate_powerbi_datasets()
