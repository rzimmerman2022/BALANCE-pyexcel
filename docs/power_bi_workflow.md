fect—seeing the two owner folders laid out like that means you’re ready for the Power BI “From Folder” workflow.

1 ⃣ Decide where the data should live
Option	When to choose it	Steps
Keep inside the repo (what you have now)
…\BALANCE-pyexcel-repository\CSVs\{Owner}\*.csv	• You’re the only user
• You don’t plan to push the repo to GitHub (or you’ve already added /CSVs/ to .gitignore)	Nothing to move. Just remember to run process_pdfs.py … CSVs {Owner} so new files land in the same tree.
Move outside the repo (privacy-safe)	• You’ll eventually publish the repo
• You want a very slim repo history	1. mkdir C:\BALANCE_data\CSVs
2. robocopy CSVs C:\BALANCE_data\CSVs /E
3. Add to .gitignore:
  /CSVs/
  csv_inbox_real/

Either layout works with Power BI; just pick one and stick with it.

2 ⃣ Build the Power BI report
Open Power BI Desktop → Get Data → Folder.
Browse to the folder that holds the owner sub-folders, e.g.
…\BALANCE-pyexcel-repository\CSVs or C:\BALANCE_data\CSVs.

In the dialog, click Transform Data (not Load).
This opens Power Query.

Filter to the CSV files only

In the preview table, keep rows where Extension = .csv.

Remove columns you don’t need (Size, Date accessed, etc.).

Combine / Transform → Combine Files.
Power BI will automatically:

Read the first file as an example.

Promote headers.

Append all owner files into one query called Combined.

Verify column types

TransDate → Date

Amount → Decimal number

Leave Owner, RawMerchant, etc. as Text.

Close & Apply.
Now you’re in the report canvas with a single table of all transactions.

3 ⃣ Create the visuals
Visual	How
Month-over-Month Spend	Clustered column or line chart. Axis = Year-Month (build a Date hierarchy or a “yyyy-mm” custom column). Values = Sum Amount (set conditional colour if negative).
Top 10 Merchants (current month)	Add a slicer for Year-Month, then a Top N horizontal bar chart: Axis = RawMerchant, Value = Sum Amount, filter Top 10.
Credits vs Charges Donut	Create a grouping field (e.g., ChargeCredit = if [Amount] < 0 then "Charge" else "Credit"), then a donut visual with Sum Amount.
KPI Cards	Four Card visuals: Sum Charges, Sum Credits, Net (Sum), Distinct count of RawMerchant. Use teal (#00A6A6) for the primary colour.
Slicers	Add slicers for Owner, AccountLast4, and Year-Month.

Tip: turn on “Sync slicers” so the same filters apply across pages if you create additional sheets.

4 ⃣ (Optional) Dynamic “sheet” per owner
Power BI doesn’t create new pages on refresh, but you can replicate the Excel feel:

Method A – Bookmarks

Duplicate the page for each owner.

Pre-filter each page to one owner via the slicer, then lock it.

Rename the page tabs “Jordyn”, “Ryan”, …

Method B – One page + slicer

Keep a single page with a slicer for Owner.

Users pick the owner they want; the visuals update instantly.

5 ⃣ Refresh workflow
Run your PDF-to-CSV pipeline (process_pdfs.py) to drop fresh CSVs in the same folder.

Open the .pbix file and click Refresh (or schedule refresh if you later use Power BI Service).

Everything updates—no VBA, no COM automation required.

Quick recap
Keep (or move) your CSVs folder—Power BI can read either.

Use Get Data → Folder to auto-combine owner CSVs.

Build modern visuals with slicers and KPI cards.

Refresh is one click. Done!

Let me know if you’d like screenshots or a step-by-step GIF of the Power Query setup.
