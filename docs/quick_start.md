# Quick Start

Follow these steps to see BALANCE-pyexcel in action with **your** bank exports.

---

## 1  Clone & install

```bash
git clone https://github.com/<your-github-handle>/BALANCE-pyexcel.git
cd BALANCE-pyexcel
poetry install --with dev         # installs main + dev/test deps
2 Create a CSV inbox
text
Copy
Edit
C:\FinanceCSVs\
   ├── Jordyn\
   └── Ryan\
Drop your raw bank CSVs into the matching owner folder.

3 Point Excel to the inbox
Open BALANCE-pyexcel.xlsm (or copy template.xlsm and rename).

Go to the Config sheet.

Set CsvInboxPath → C:\FinanceCSVs\

Fill in Owner names exactly as your folder names (Jordyn, Ryan).

4 Run the ETL
In the Config sheet, click the Run ETL button or type in any cell:

excel
Copy
Edit
=PY(etl_main(Config!B2))
Python-in-Excel will:

Read every CSV in your inbox.

Normalize and de-duplicate the data.

Write results to the Transactions sheet.

Queue any new “unknown” rows in Queue_Review.

5 Classify “?” rows
Open the Queue_Review sheet, mark each row:

Y – shared expense

N – personal expense

S – split, then enter a %
Run ETL again to sync those decisions.

6 Check the Dashboard
Head over to Dashboard to see:

Net balance (who owes whom)

Month-over-month spend

Top merchants and categories

Done ✅

Next steps
Automate with the CLI – see CLI Usage.

Add a new bank – edit the YAML in Schema Registry.

Build a Power BI report – follow Power BI Integration.

Happy balancing!

pgsql
Copy
Edit

**What changed**

| Tweak | Benefit |
|-------|---------|
| Bullet-proof folder & sheet names | Prevents typos on first run. |
| Call-out of *Run ETL* button **or** formula | Works whether users enabled the VBA helper or not. |
| Clear next-step links | Guides users deeper into docs without cluttering the quick start. |