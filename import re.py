import re
import pandas as pd
from typing import Dict, Optional, Tuple

class TransactionDescriptionParser:
    """
    Extracts structured information from raw transaction descriptions
    while preserving the original data for reference.
    """
    
    def __init__(self):
        # Define patterns for common reference number formats
        self.reference_patterns = {
            'amazon_order': re.compile(r'AMAZON\.COM\*([A-Z0-9]{8,12})', re.IGNORECASE),
            'paypal_ref': re.compile(r'PAYPAL\s*\*([A-Z0-9]+)', re.IGNORECASE),
            'check_number': re.compile(r'CHECK\s*#?\s*(\d{3,6})', re.IGNORECASE),
            'invoice_number': re.compile(r'INV(?:OICE)?\s*#?\s*([A-Z0-9-]+)', re.IGNORECASE),
            'confirmation': re.compile(r'CONF(?:IRMATION)?\s*#?\s*([A-Z0-9-]+)', re.IGNORECASE),
            'reference': re.compile(r'REF\s*#?\s*([A-Z0-9-]+)', re.IGNORECASE),
        }
        
        # Patterns for extracting location info
        self.location_patterns = {
            'state_code': re.compile(r'\s+([A-Z]{2})(?:\s|$)'),
            'city_state': re.compile(r'(?:^|\s)([A-Z\s]+)\s+([A-Z]{2})(?:\s|$)'),
        }
    
    def parse_transaction(self, original_description: str) -> Dict[str, Optional[str]]:
        """
        Parse a transaction description and extract structured information.
        
        Returns a dictionary with:
        - original: The raw description (preserved)
        - merchant: Clean merchant name
        - reference_type: Type of reference found (if any)
        - reference_number: The actual reference number
        - location: Extracted location info
        - description_clean: Cleaned description with refs removed
        """
        result = {
            'original': original_description,
            'merchant': None,
            'reference_type': None,
            'reference_number': None,
            'location': None,
            'description_clean': original_description.upper().strip()
        }
        
        # Extract reference numbers
        for ref_type, pattern in self.reference_patterns.items():
            match = pattern.search(original_description)
            if match:
                result['reference_type'] = ref_type
                result['reference_number'] = match.group(1)
                # Remove the reference from the clean description
                result['description_clean'] = pattern.sub('', result['description_clean']).strip()
                break
        
        # Extract location (usually at the end)
        location_match = self.location_patterns['state_code'].search(result['description_clean'])
        if location_match:
            result['location'] = location_match.group(1)
            # Remove location from clean description
            result['description_clean'] = result['description_clean'][:location_match.start()].strip()
        
        # The merchant would be derived from your existing merchant lookup rules
        # This is just the clean description after removing references and location
        result['merchant_base'] = result['description_clean']
        
        return result

# Example of how to integrate this with your existing pipeline
def enhance_descriptions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enhance a DataFrame with parsed description information.
    Preserves original data while adding structured fields.
    """
    parser = TransactionDescriptionParser()
    
    # Parse all descriptions
    parsed_data = df['OriginalDescription'].apply(parser.parse_transaction)
    
    # Extract the parsed fields into separate columns
    df['ReferenceType'] = parsed_data.apply(lambda x: x['reference_type'])
    df['ReferenceNumber'] = parsed_data.apply(lambda x: x['reference_number'])
    df['LocationCode'] = parsed_data.apply(lambda x: x['location'])
    df['DescriptionClean'] = parsed_data.apply(lambda x: x['description_clean'])
    
    # Your existing merchant normalization would still work on the original
    # or could work on DescriptionClean for better matching
    
    return df

# Example usage showing the layered approach
def demonstrate_layered_approach():
    """Show how different layers of description serve different purposes"""
    
    sample_transactions = pd.DataFrame({
        'OriginalDescription': [
            'AMAZON.COM*2K4Y83QL2 AMZN.COM/BILL WA',
            'AMAZON MARKETPLACE PMTS AMZN.COM/BILL WA',
            'TARGET #2382 CHARLOTTE NC',
            'CHECK #1234',
            'PAYPAL *JOHNDOE TRANSFER',
        ]
    })
    
    # Parse the descriptions
    enhanced_df = enhance_descriptions(sample_transactions)
    
    # Now you have multiple levels:
    # 1. OriginalDescription - for cross-referencing with bank statements
    # 2. ReferenceNumber - for matching with orders/invoices
    # 3. DescriptionClean - for merchant matching rules
    # 4. Merchant - normalized merchant name (from your existing logic)
    
    print("Layered Description Analysis:")
    print("=" * 80)
    for idx, row in enhanced_df.iterrows():
        print(f"\nTransaction {idx + 1}:")
        print(f"  Original: {row['OriginalDescription']}")
        print(f"  Reference: {row['ReferenceType']} = {row['ReferenceNumber']}")
        print(f"  Location: {row['LocationCode']}")
        print(f"  Clean: {row['DescriptionClean']}")
        print(f"  (Merchant normalization would produce: 'Amazon', 'Target', etc.)")

# Advanced: Creating a reference lookup table
def build_reference_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build an index of all reference numbers for quick lookup.
    This is useful for reconciliation and investigation.
    """
    # Filter to only rows with reference numbers
    refs = df[df['ReferenceNumber'].notna()].copy()
    
    # Create a reference lookup table
    reference_index = refs[['Date', 'Amount', 'Merchant', 'ReferenceType', 'ReferenceNumber', 'OriginalDescription']]
    
    # Sort by date for easier investigation
    reference_index = reference_index.sort_values('Date', ascending=False)
    
    return reference_index

if __name__ == "__main__":
    demonstrate_layered_approach()