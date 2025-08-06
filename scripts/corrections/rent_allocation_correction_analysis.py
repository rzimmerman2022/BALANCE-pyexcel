"""
Rent Allocation Correction Analysis
The current system has the rent allocation backwards - need to investigate and fix
"""

import pandas as pd


def analyze_rent_allocation_issue():
    """Analyze the rent allocation discrepancy"""
    
    print("🏠 RENT ALLOCATION CORRECTION ANALYSIS")
    print("=" * 60)
    
    # Load the rent allocation data
    try:
        rent_df = pd.read_csv("data/Consolidated_Rent_Allocation_20250527.csv")
        print(f"✅ Loaded rent allocation data: {len(rent_df)} months")
    except Exception as e:
        print(f"❌ Error loading rent data: {e}")
        return None
    
    print("\n📊 CURRENT SYSTEM (INCORRECT):")
    print("-" * 40)
    print("Current system shows:")
    print("• Ryan: Pays FULL rent ($2,090)")
    print("• Ryan: Owes 43% share ($931)")
    print("• Ryan: Net effect = -$1,159 (overpaid)")
    print("")
    print("• Jordyn: Pays $0")
    print("• Jordyn: Owes 57% share ($1,191)")
    print("• Jordyn: Net effect = +$1,191 (owes money)")
    
    print("\n✅ CORRECT SYSTEM (SHOULD BE):")
    print("-" * 40)
    print("Actual arrangement:")
    print("• Jordyn: Pays FULL rent ($2,090)")
    print("• Ryan: Owes 47% share ($983)")
    print("• Ryan: Net effect = +$983 (owes Jordyn)")
    print("")
    print("• Jordyn: Pays full rent ($2,090)")
    print("• Jordyn: Owed 47% from Ryan ($983)")
    print("• Jordyn: Net effect = -$983 (overpaid)")
    
    # Calculate the impact of this error
    print("\n🚨 IMPACT OF THE ERROR:")
    print("-" * 40)
    
    # Assuming recent rent is $2,090 and Ryan owes 47%
    recent_rent = 2090.00
    ryan_correct_share = recent_rent * 0.47  # $983
    jordyn_correct_share = recent_rent * 0.53  # $1,107
    
    # Current incorrect calculation (from system)
    ryan_current_net = -1159.00  # System shows Ryan overpaid
    jordyn_current_net = 1191.00  # System shows Jordyn owes
    
    # Correct calculation
    ryan_correct_net = ryan_correct_share  # Ryan owes this to Jordyn
    jordyn_correct_net = -jordyn_correct_share  # Jordyn overpaid by this amount
    
    print(f"Recent rent: ${recent_rent:,.2f}")
    print(f"Ryan's 47% share: ${ryan_correct_share:,.2f}")
    print(f"Jordyn's 53% share: ${jordyn_correct_share:,.2f}")
    print("")
    print("PER MONTH ERROR:")
    print(f"• Ryan net effect error: ${ryan_current_net - ryan_correct_net:,.2f}")
    print(f"• Jordyn net effect error: ${jordyn_current_net - jordyn_correct_net:,.2f}")
    
    # Calculate total error across all months
    num_months = len(rent_df)
    total_ryan_error = (ryan_current_net - ryan_correct_net) * num_months
    total_jordyn_error = (jordyn_current_net - jordyn_correct_net) * num_months
    
    print(f"\nTOTAL ERROR ACROSS {num_months} MONTHS:")
    print(f"• Ryan total error: ${total_ryan_error:,.2f}")
    print(f"• Jordyn total error: ${total_jordyn_error:,.2f}")
    print(f"• Combined error magnitude: ${abs(total_ryan_error) + abs(total_jordyn_error):,.2f}")
    
    print("\n⚠️  CURRENT BALANCE IMPACT:")
    print("-" * 40)
    print("The current balance showing Ryan owes Jordyn $30,864.05")
    print("is MASSIVELY WRONG due to this rent allocation error!")
    print("")
    print("If rent allocation is corrected:")
    print(f"• Ryan's balance would change by: ${total_ryan_error:,.2f}")
    print(f"• Jordyn's balance would change by: ${total_jordyn_error:,.2f}")
    print("")
    print("This could completely flip the balance relationship!")
    
    print("\n🔧 REQUIRED FIXES:")
    print("-" * 40)
    print("1. Update rent allocation CSV to show:")
    print("   - Jordyn pays full rent (not Ryan)")
    print("   - Ryan owes 47% (not 43%)")
    print("   - Jordyn owed 47% (not owes 57%)")
    print("")
    print("2. Regenerate comprehensive audit trail")
    print("3. Recalculate all balances")
    print("4. Verify with actual bank statements")
    
    print("\n💡 INVESTIGATION QUESTIONS:")
    print("-" * 40)
    print("1. Who actually pays the rent each month?")
    print("2. What is Ryan's exact percentage share?")
    print("3. When did this arrangement start?")
    print("4. Are there any months where the arrangement was different?")
    
    return {
        'monthly_error_ryan': ryan_current_net - ryan_correct_net,
        'monthly_error_jordyn': jordyn_current_net - jordyn_correct_net,
        'total_error_ryan': total_ryan_error,
        'total_error_jordyn': total_jordyn_error,
        'months_affected': num_months
    }

if __name__ == "__main__":
    analyze_rent_allocation_issue()
