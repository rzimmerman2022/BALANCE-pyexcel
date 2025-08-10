#!/usr/bin/env python3
"""
Quick fix to display the analysis results that were already generated
"""

import json
from collections import defaultdict
from pathlib import Path


def display_analysis_results():
    """Load and display the analysis results with proper error handling"""
    
    # Load the results
    results_path = Path("analysis_output/comprehensive_analysis_results.json")
    
    if not results_path.exists():
        print("[ERROR] Results file not found. Please run the analysis first.")
        return
    
    with open(results_path) as f:
        results = json.load(f)
    
    # Print header
    print("\n" + "="*80)
    print("COMPREHENSIVE BALANCE ANALYSIS SUMMARY (FIXED)")
    print("="*80)
    
    # Basic stats
    data_quality = results.get('data_quality', {})
    print(f"\nFiles Analyzed: {data_quality.get('total_files_processed', 0)}")
    print(f"Total Transactions: {data_quality.get('total_transactions', 0):,}")
    print(f"File Types Found: {', '.join(data_quality.get('file_types_found', []))}")
    
    # Pattern summary
    print("\n[PATTERN ANALYSIS]")
    print("-"*40)
    
    # Aggregate patterns across all files
    total_by_pattern = defaultdict(int)
    pattern_analysis = results.get('pattern_analysis', {})
    
    for file_patterns in pattern_analysis.values():
        if isinstance(file_patterns, dict):
            for pattern, count in file_patterns.items():
                total_by_pattern[pattern] += count
    
    if total_by_pattern:
        for pattern, count in sorted(total_by_pattern.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"  {pattern}: {count}")
    else:
        print("  No patterns found in descriptions")
    
    # File-specific insights
    print("\n[FILE-SPECIFIC INSIGHTS]")
    print("-"*40)
    
    files_analyzed = results.get('files_analyzed', {})
    
    for filename, analysis in files_analyzed.items():
        if isinstance(analysis, dict) and 'error' not in analysis:
            print(f"\n{filename} ({analysis.get('file_type', 'unknown')}):")
            
            # Show what we found for each file type
            file_type = analysis.get('file_type')
            
            if file_type == 'expense_history':
                # Expense History specific insights
                if 'allowed_amount_analysis' in analysis:
                    allowed = analysis['allowed_amount_analysis']
                    adj_rate = allowed.get('adjustment_rate', 0)
                    print(f"  - Adjustment Rate: {adj_rate:.1f}%")
                    
                    adj_types = allowed.get('adjustment_types', {})
                    if adj_types:
                        print("  - Adjustment Breakdown:")
                        for adj_type, count in adj_types.items():
                            print(f"    * {adj_type}: {count}")
                
                if 'person_breakdown' in analysis:
                    print("  - Transaction Count by Person:")
                    for person, stats in analysis['person_breakdown'].items():
                        print(f"    * {person}: {stats['transaction_count']} transactions, ${stats['total_allowed']:,.2f} allowed")
            
            elif file_type == 'transaction_ledger':
                # Transaction Ledger specific insights
                if 'unique_features' in analysis:
                    unique_cols = analysis['unique_features'].get('unique_columns', [])
                    if unique_cols:
                        print(f"  - Unique Columns: {', '.join(unique_cols)}")
                
                if 'estimated_adjustments' in analysis:
                    est = analysis['estimated_adjustments']
                    print(f"  - Transactions with Special Instructions: {est.get('transactions_with_special_instructions', 0)} ({est.get('percentage', 0):.1f}%)")
                
                if 'running_balance_analysis' in analysis:
                    balance = analysis['running_balance_analysis']
                    print(f"  - Balance Range: ${balance.get('min_balance', 0):,.2f} to ${balance.get('max_balance', 0):,.2f}")
            
            elif file_type == 'rent_allocation':
                # Rent Allocation specific insights
                if 'total_months' in analysis:
                    print(f"  - Months Covered: {analysis['total_months']}")
                
                if 'split_analysis' in analysis and 'average_split' in analysis['split_analysis']:
                    split = analysis['split_analysis']['average_split']
                    print(f"  - Average Split: Ryan {split['ryan']:.1f}%, Jordyn {split['jordyn']:.1f}%")
                elif 'split_analysis' in analysis and 'total_rent' in analysis['split_analysis']:
                    totals = analysis['split_analysis']['total_rent']
                    print(f"  - Total Rent Paid: Ryan ${totals.get('ryan', 0):,.2f}, Jordyn ${totals.get('jordyn', 0):,.2f}")
                
                if 'rent_components' in analysis:
                    components = analysis['rent_components']
                    if components:
                        print(f"  - Rent Components: {', '.join(components[:5])}")  # Show first 5
            
            elif file_type == 'rent_history':
                # Rent History specific insights
                if 'variance_analysis' in analysis:
                    variance = analysis['variance_analysis']
                    avg_var = variance.get('average_variance', 0)
                    total_var = variance.get('total_variance', 0)
                    print(f"  - Average Monthly Variance: ${avg_var:,.2f}")
                    print(f"  - Total Variance: ${total_var:,.2f}")
                
                if 'months_covered' in analysis:
                    months = analysis['months_covered']
                    if months:
                        print(f"  - Period: {months[0]} to {months[-1]}")
    
    # Duplicate analysis
    dup_analysis = results.get('duplicate_analysis', {})
    if dup_analysis:
        print("\n[DUPLICATE ANALYSIS]")
        print("-"*40)
        dup_count = len(dup_analysis.get('potential_duplicates', []))
        cross_file = dup_analysis.get('cross_file_matches', 0)
        print(f"  - Potential Duplicates: {dup_count}")
        print(f"  - Cross-File Matches: {cross_file}")
        
        # Show a few examples if there are duplicates
        if dup_count > 0 and 'potential_duplicates' in dup_analysis:
            print("\n  Examples of duplicates:")
            for i, dup in enumerate(dup_analysis['potential_duplicates'][:3]):
                print(f"    {i+1}. {dup['fingerprint']} appears {dup['count']} times")
    
    # Business rules
    rules = results.get('business_rules', {})
    if rules and 'core_rules' in rules:
        print("\n[DISCOVERED BUSINESS RULES]")
        print("-"*40)
        for rule in rules['core_rules'][:5]:  # Show top 5 rules
            print(f"  {rule['priority']}. {rule['rule']}")
            if 'description' in rule:
                print(f"     {rule['description']}")
    
    # Recommendations
    recommendations = results.get('recommendations', [])
    if recommendations:
        print("\n[TOP RECOMMENDATIONS]")
        print("-"*40)
        for rec in recommendations[:3]:
            print(f"  [{rec['priority']}] {rec['recommendation']}")
            if 'rationale' in rec:
                print(f"     Reason: {rec['rationale']}")
    
    # Pattern examples
    if 'pattern_examples' in results:
        print("\n[PATTERN EXAMPLES]")
        print("-"*40)
        examples = results['pattern_examples']
        for pattern, pattern_examples in list(examples.items())[:3]:  # Show 3 pattern types
            if pattern_examples:
                print(f"  {pattern}:")
                for ex in pattern_examples[:2]:  # Show 2 examples per pattern
                    print(f"    - \"{ex}\"")
    
    print("\n[OK] Analysis complete! Full results saved in 'analysis_output' directory.")
    print("="*80)

if __name__ == "__main__":
    display_analysis_results()