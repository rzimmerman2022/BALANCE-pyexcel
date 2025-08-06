import re

import pandas as pd
from dateutil.parser import parse

_money = re.compile(r"[^\d\-.]")   # strips $, commas, spaces

def expense_history_df(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={
        "Name": "Person",
        "Date of Purchase": "Date",
        "Merchant": "Merchant",
        "Actual Amount ": "Amount",
        "Allowed Amount ": "Allowed",
        "Description ": "Notes",
    })
    df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = df["Amount"].astype(str).str.replace(_money,"",regex=True).astype(float)
    df["Allowed"]= df["Allowed"].astype(str).str.replace(_money,"",regex=True).replace({"":0}).astype(float)
    df["Category"] = "ExpenseHistory"
    return df[["Date","Person","Account","Merchant","Amount","Category","Notes"]]

def transaction_ledger_df(path: str) -> pd.DataFrame:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    hdr = next(i for i,l in enumerate(lines) if l.startswith('"Name","Date of Purchase"'))
    df  = pd.read_csv(pd.compat.StringIO("".join(lines[hdr:])))
    df  = df.rename(columns={
        "Name":"Person","Date of Purchase":"Date",
        "Merchant Description ":"MerchantDesc",
        "Actual Amount ":"Amount","Description ":"Notes",
    })
    df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = df["Amount"].astype(str).str.replace(_money,"",regex=True).astype(float)
    df["Category"]= df["Category"].str.strip()
    return df[["Date","Person","Account","Merchant","Amount","Category","Notes"]]

def rent_allocation_df(path:str)->pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={
        "Month":"Period","Ryan's Rent (43%) ":"RyanShare","Jordyn's Rent (57%)":"JordynShare"
    })
    df["Period"] = df["Period"].apply(lambda s: parse(s,dayfirst=False,yearfirst=False))
    for c in ("RyanShare","JordynShare"):
        df[c]=df[c].astype(str).str.replace(_money,"",regex=True).astype(float)
    return df[["Period","RyanShare","JordynShare"]]

def rent_history_df(path:str)->pd.DataFrame:
    raw = pd.read_csv(path,header=0)
    raw = raw.rename(columns={raw.columns[0]:"Category"})        # fixes blank first header
    long= raw.melt(id_vars="Category",var_name="Period",value_name="Amount").dropna()
    long[["Month","Kind"]] = long["Period"].str.extract(r"(\w+ \d{4}) (Budgeted|Actual)")
    long["Period"] = long["Month"].apply(parse)
    long["Amount"] = long["Amount"].astype(str).str.replace(_money,"",regex=True).astype(float)
    long = long.pivot_table(index=["Period","Category"],columns="Kind",values="Amount").reset_index()
    return long
