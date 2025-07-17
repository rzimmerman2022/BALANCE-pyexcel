# Schema Migration Plan - v1 to v2

## Overview
This document tracks the changes needed to migrate from the 29-column schema v1 to the 24-column schema v2.

## Key Changes Across All Schemas

1. **Description Field Mapping**
   - `jordyn_*` schemas: Keep mapping `Description` → `OriginalDescription`, but also create alias to `Description`
   - `ryan_monarch_v1`: Map `Merchant` → `Description` (in addition to keeping as `Merchant`)
   - `ryan_rocket_v1`: Map `Name` → `Description` (change from mapping to `Merchant`)

2. **Institution Field Consolidation**
   - `ryan_rocket_v1`: Change mapping from `Institution Name` → `InstitutionName` to `Institution Name` → `Institution`

3. **Fields to Remove from column_map**
   - Remove mappings for: `Note`, `Notes`, `CustomName`, `IgnoredFrom`, `TaxDeductible`, `Source`
   - These will automatically go to `Extras` field if present

## Schema-Specific Changes

### jordyn_chase_checking_v1.yaml
- ✅ Already maps to `Description` via alias
- ❌ Remove `Note` from any mappings
- ✅ Keep `Institution` in extras_ignore

### jordyn_discover_card_v1.yaml
- ✅ Already maps to `Description` via alias
- ❌ Remove `Note` from any mappings
- ✅ Keep current structure

### jordyn_wells_v1.yaml / jordyn_wellsfargo_visa_v1.yaml
- ✅ Already maps to `Description` via alias
- ❌ Remove `Note` from any mappings
- ✅ Keep `Statement Period Description` → `StatementPeriodDesc`

### ryan_monarch_v1.yaml
- ❌ Add: `Merchant` → `Description` mapping (keep original `Merchant` → `Merchant` too)
- ❌ Remove: `Notes` → `Notes` mapping (let it go to Extras)
- ✅ Keep `Original Statement` → `OriginalStatement`

### ryan_rocket_v1.yaml
- ❌ Change: `Name` → `Merchant` to `Name` → `Description`
- ❌ Add: `Name` → `Merchant` as secondary mapping
- ❌ Change: `Institution Name` → `InstitutionName` to `Institution Name` → `Institution`
- ❌ Remove: `Note` → `Notes`, `Custom Name` → `CustomName`, `Tax Deductible` → `TaxDeductible`
- ✅ Keep `Original Date` → `OriginalDate`

### jordyn_pdf_v1.yaml
- Check if updates needed based on header signature

## Testing Order

1. Start with `ryan_rocket_v1.yaml` (most changes needed)
2. Then `ryan_monarch_v1.yaml` (moderate changes)
3. Then Jordyn schemas (minimal changes)
4. Finally PDF schema

## Validation Checklist

For each schema after updating:
- [ ] Run smoke test on single file
- [ ] Check that Description field is populated
- [ ] Verify no warnings about missing critical fields
- [ ] Confirm deprecated fields go to Extras
- [ ] Validate column count matches new schema