# Sign-Convention Analysis

## 1.1 net_effect calculation (verbatim)
```python
# --- Standard expenses / ledger ---
net_effect_ryan   = round(allowed_ryan   - (actual_paid if payer == "Ryan"   else 0.0), 2)
net_effect_jordyn = round(allowed_jordyn - (actual_paid if payer == "Jordyn" else 0.0), 2)

# --- Rent rows (Ryan assumed payer) ---
net_effect = round(ryan_share   - full_rent, 2)   # Ryan row
net_effect = round(jordyn_share - 0.0,      2)   # Jordyn row
```

### Example rows – input → calculation
- **Ryan**, NA, Rent:  actual=2119.72, allowed=911.48 → net_effect = -1208.24

## 1.2 Balance accumulation
Code:
```python
summary_df = audit_df.groupby("person")["net_effect"].sum().reset_index().rename(columns={"net_effect": "net_owed"})
```

### Interpretation
*Positive* net_effect → the person **owes** the partner (they under-paid).
*Negative* net_effect → the person **is owed** (they over-paid).

*Positive* net_owed → cumulative amount the person still owes.
*Negative* net_owed → cumulative amount the person should receive.

### 10-transaction running-balance sample
|   idx | date                | merchant                                | person   |   net_effect |   running_balance |
|------:|:--------------------|:----------------------------------------|:---------|-------------:|------------------:|
|     1 | 2024-07-04 00:00:00 | FRYS-FOOD-DRG #051 CHANDLER AZ          | Ryan     |            0 |                 0 |
|     2 | 2024-07-04 00:00:00 | FRYS-FOOD-DRG #051 CHANDLER AZ          | Jordyn   |            0 |                 0 |
|     3 | 2024-07-06 00:00:00 | TOTAL WINE AND MORE PHOENIX AZ          | Ryan     |            0 |                 0 |
|     4 | 2024-07-06 00:00:00 | TOTAL WINE AND MORE PHOENIX AZ          | Jordyn   |            0 |                 0 |
|     5 | 2024-07-06 00:00:00 | AMAZON.COM*R71IE4QJ2 SEATTLE WA         | Ryan     |            0 |                 0 |
|     6 | 2024-07-06 00:00:00 | AMAZON.COM*R71IE4QJ2 SEATTLE WA         | Jordyn   |            0 |                 0 |
|     7 | 2024-07-07 00:00:00 | IN-N-OUT PRESCOTT PRESCOTT AZ           | Ryan     |            0 |                 0 |
|     8 | 2024-07-07 00:00:00 | IN-N-OUT PRESCOTT PRESCOTT AZ           | Jordyn   |            0 |                 0 |
|     9 | 2024-07-08 00:00:00 | AMTRAK MOBIL1900710219973 WASHINGTON DC | Ryan     |            0 |                 0 |
|    10 | 2024-07-08 00:00:00 | AMTRAK MOBIL1900710219973 WASHINGTON DC | Jordyn   |            0 |                 0 |

## 1.3 Current sign conventions
• Positive net_effect means **the person owes** their partner  
• Negative net_effect means **the person is owed**  
• Positive net_owed means **cumulative amount owed**  
• Negative net_owed means **cumulative amount to be received**  
*No flips detected between expense types; rent rows obey the same rule.*
