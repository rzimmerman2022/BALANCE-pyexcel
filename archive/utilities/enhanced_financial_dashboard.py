"""
Enhanced Financial Dashboard Generator
Creates comprehensive financial reports and summaries for the BALANCE project
"""

from datetime import datetime

import pandas as pd


def generate_financial_dashboard():
    """Generate comprehensive financial dashboard and reports"""
    
    print("🏦 Enhanced Financial Dashboard Generator")
    print("=" * 50)
    
    # Load the Power BI datasets we just created
    try:
        transactions = pd.read_csv("powerbi_transaction_details.csv")
        monthly_summary = pd.read_csv("powerbi_monthly_summary.csv")
        balance_history = pd.read_csv("powerbi_balance_history.csv")
        current_status = pd.read_csv("powerbi_current_status.csv")
        
        print(f"✅ Loaded {len(transactions)} transactions")
        print(f"✅ Loaded {len(monthly_summary)} monthly summaries")
        print(f"✅ Loaded {len(balance_history)} balance history points")
        print("✅ Loaded current status")
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None
    
    # Convert date columns
    transactions['Date'] = pd.to_datetime(transactions['Date'])
    balance_history['Date'] = pd.to_datetime(balance_history['Date'])
    
    print("\n📊 FINANCIAL SUMMARY REPORT")
    print("=" * 50)
    
    # 1. Current Balance Status
    print("💰 CURRENT BALANCE STATUS:")
    for _, row in current_status.iterrows():
        if row['Person'] != 'SUMMARY':
            balance = row['Running_Balance']
            status = "owes money" if balance < 0 else "is owed money" if balance > 0 else "is even"
            print(f"  • {row['Person']}: ${abs(balance):,.2f} ({status})")
    
    # 2. Transaction Summary
    latest_date = transactions['Date'].max()
    earliest_date = transactions['Date'].min()
    total_days = (latest_date - earliest_date).days
    
    print("\n📈 TRANSACTION SUMMARY:")
    print(f"  • Period: {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}")
    print(f"  • Duration: {total_days} days")
    print(f"  • Total Transactions: {len(transactions):,}")
    print(f"  • Average per day: {len(transactions)/total_days:.1f}")
    
    # 3. Monthly Breakdown
    print("\n📅 MONTHLY BREAKDOWN (Last 6 Months):")
    recent_monthly = monthly_summary.tail(12)  # Last 12 entries (6 months x 2 people)
    for month in recent_monthly['Month'].unique()[-6:]:
        month_data = recent_monthly[recent_monthly['Month'] == month]
        print(f"  • {month}:")
        for _, row in month_data.iterrows():
            print(f"    - {row['Person']}: ${row['Total_Paid']:,.2f} paid, {row['Transaction_Count']} transactions")
    
    # 4. Category Analysis
    print("\n🏷️ SPENDING ANALYSIS:")
    category_summary = transactions.groupby(['Transaction_Type', 'Person']).agg({
        'Amount_Paid': 'sum',
        'Transaction_Number': 'count'
    }).round(2)
    
    for (category, person), data in category_summary.iterrows():
        print(f"  • {person} - {category}: ${data['Amount_Paid']:,.2f} ({data['Transaction_Number']} transactions)")
    
    # 5. Top Expenses
    print("\n💸 TOP 10 LARGEST TRANSACTIONS:")
    top_expenses = transactions.nlargest(10, 'Amount_Absolute')[
        ['Date', 'Person', 'Description_Clean', 'Amount_Paid', 'Transaction_Type']
    ]
    for _, row in top_expenses.iterrows():
        print(f"  • {row['Date'].strftime('%Y-%m-%d')} | {row['Person']} | ${row['Amount_Paid']:,.2f} | {row['Description_Clean'][:50]}...")
    
    # 6. Recent Activity (Last 30 days)
    recent_date = latest_date - pd.Timedelta(days=30)
    recent_transactions = transactions[transactions['Date'] > recent_date]
    
    print("\n🕐 RECENT ACTIVITY (Last 30 Days):")
    print(f"  • Recent Transactions: {len(recent_transactions)}")
    recent_summary = recent_transactions.groupby('Person').agg({
        'Amount_Paid': 'sum',
        'Transaction_Number': 'count'
    }).round(2)
    
    for person, data in recent_summary.iterrows():
        print(f"  • {person}: ${data['Amount_Paid']:,.2f} ({data['Transaction_Number']} transactions)")
    
    # 7. Balance Trend Analysis
    print("\n📈 BALANCE TREND ANALYSIS:")
    final_balances = balance_history.groupby('Person')['Running_Balance'].last()
    for person, balance in final_balances.items():
        print(f"  • {person} final balance: ${balance:,.2f}")
    
    # 8. Generate summary statistics
    total_money_moved = transactions['Amount_Absolute'].sum()
    avg_transaction = transactions['Amount_Absolute'].mean()
    
    print("\n📊 OVERALL STATISTICS:")
    print(f"  • Total money moved: ${total_money_moved:,.2f}")
    print(f"  • Average transaction: ${avg_transaction:.2f}")
    print(f"  • Largest transaction: ${transactions['Amount_Absolute'].max():,.2f}")
    print(f"  • Smallest transaction: ${transactions['Amount_Absolute'].min():.2f}")
    
    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"financial_dashboard_report_{timestamp}.txt"
    
    with open(report_file, 'w') as f:
        f.write("BALANCE PROJECT - FINANCIAL DASHBOARD REPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write current status
        f.write("CURRENT BALANCE STATUS:\n")
        for _, row in current_status.iterrows():
            if row['Person'] != 'SUMMARY':
                balance = row['Running_Balance']
                status = "owes money" if balance < 0 else "is owed money" if balance > 0 else "is even"
                f.write(f"  {row['Person']}: ${abs(balance):,.2f} ({status})\n")
        
        f.write(f"\nTotal Transactions: {len(transactions):,}\n")
        f.write(f"Date Range: {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}\n")
        f.write(f"Total Money Moved: ${total_money_moved:,.2f}\n")
    
    print(f"\n💾 Detailed report saved: {report_file}")
    print("🎉 Financial Dashboard Complete!")
    
    return {
        'transactions': len(transactions),
        'balance_ryan': final_balances.get('Ryan', 0),
        'balance_jordyn': final_balances.get('Jordyn', 0),
        'total_money_moved': total_money_moved,
        'report_file': report_file
    }

if __name__ == "__main__":
    generate_financial_dashboard()
