# Quick Start

1. **Clone & install**

   ```bash
   git clone https://github.com/<you>/BALANCE-pyexcel.git
   cd BALANCE-pyexcel
   poetry install --with dev
Create your CSV inbox

text
Copy
Edit
C:\FinanceCSVs\
    ├─ Jordyn\
    └─ Ryan\
Open Excel → Config sheet
* Set CsvInboxPath to C:\FinanceCSVs
* Enter user names

Run the ETL cell (=PY(etl_main(Config!B2))) → data appears in Transactions.

Classify any “?” rows in Queue_Review.

Done ✅ – check Dashboard for who owes whom.

(For deeper dives, read the other docs pages or the README.)