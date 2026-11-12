# Loan Discount System (Odoo 18)

Accounting > Loans is NOT modified: the treasurer registers the bank loan there as before.
This app records the money given to customers (Discount Centers), with the same layout as the Loan form.

## Install
1. Copy `loan_discount_system` into addons, `pip install openpyxl`, restart Odoo, Upgrade/Install the app.
2. Give users the group *Loan Discount System / Treasurer*.

## Setup
Loan Discount System > Configuration > Company Settings > your company > tab *Loan Discount*:
Default Journal (Miscellaneous) and Interest Income Account.

## Flow
1. Loan Discount System > Treasure Distribution > Distributions > New
   Name, Customer, Amount Borrowed, Interest, Loan Date, Duration.
2. Compute (equal installments) or Upload (Excel: Date, Principal, Interest, Payment, Balance).
3. Pick the **Bank Loan** (from Accounting > Loans) at the top of the form: it shows the loan amount, what was
   already distributed and what is still available. Journal (Miscellaneous) and Ledger are in Loan Settings.
   The Loans model is auto-detected (field 'Amount Borrowed'); override with system parameter `lds.loan_model`.
4. Confirm  ->  Dr Customer receivable / Cr Ledger (Bank).
5. Each month press Pay on the line  ->  Dr Ledger (Bank) / Cr Receivable (principal) / Cr Interest income.
   Outstanding Balance decreases; the loan closes when all lines are paid.
