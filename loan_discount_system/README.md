# Loan Discount System (Odoo 18)

Discount Centers are handled as CUSTOMERS of the treasury company. Everything is posted in ONE company
with ONE journal. Each Discount Center's debt sits in its own Receivable account (customer statement / aging).

## Install
1. Copy `loan_discount_system` into your addons path, `pip install openpyxl`, restart Odoo.
2. Update Apps List, install (or upgrade) *Loan Discount System*.
3. Give users the group *Loan Discount System / Treasurer*.

## Setup (treasury company only)
Loan Discount System > Configuration > Company Settings > treasury company > tab *Loan Discount*:
Default Journal, Bank Loan Payable, Interest Expense, Interest Recovery/Income.
Each Discount Center must exist as a Contact (partner) with a Receivable account.

## Where things are
- Accounting > Accounting > **Loans**: Bank Loan form (schedule, repayments, distribution, allocations, Odoo link).
  The existing Loans menu is re-pointed to this form on install/upgrade. Uninstalling restores it.
- App **Loan Discount System** > Treasure Distribution > Distributions / Customer Repayment Schedule
- App **Loan Discount System** > Configuration > Company Settings

## Flow
1. Bank Loans > New > Compute or Upload Excel > Confirm   (Dr Bank / Cr Loan Payable)
2. Distribution tab: Discount Center + amount + markup > Confirm   (Dr Customer receivable / Cr Bank)
3. Generate Allocations > Accrue   (Dr Customer receivable / Cr Interest income)
4. Pay on schedule line > Post   (Dr Loan payable + Interest expense / Cr Bank)
5. Settle on allocation when the Discount Center pays   (Dr Bank / Cr Customer receivable)
