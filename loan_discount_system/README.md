# Loan Discount System (Odoo 18)

## Install
1. Copy folder `loan_discount_system` into your addons path.
2. `pip install openpyxl` (needed for Excel upload).
3. Restart Odoo, Apps > Update Apps List, install **Loan Discount System**.
4. Give users the group *Loan Discount System / Treasurer*.

## Setup (per company)
Loan Discount System > Configuration > Company Settings > open company > tab **Loan Discount**.
- Treasury company: Loan Journal, Bank Loan Payable, Interest Expense, Due from Group Companies, Interest Recovery.
- Each Discount Center: Loan Journal, Interest Expense, Due to HQ.

## Flow
1. Loan Discount System app > Loans > Bank Loans > New (name, bank e.g. KCB, amount, rate, months).
2. Compute, or Upload the bank's Excel schedule (Date, Principal, Interest, Payment, Balance).
3. Settings tab: pick the Odoo Loan record and press **Sync Odoo Loan** to compare outstanding.
4. Confirm. Posts: Dr Bank / Cr Bank Loan Payable.
5. Distribution tab: add each company, amount, markup. Confirm each. Posts inter-company entries in both companies.
6. Generate Allocations > Accrue Interest (all). Each company is charged its share of bank interest + markup.
7. Repayments: press Pay on a schedule line > Post. Outstanding updates. Dr Loan Payable, Dr Interest, Cr Bank.
8. Company pays treasury: Settle on the allocation. Posts both sides.
