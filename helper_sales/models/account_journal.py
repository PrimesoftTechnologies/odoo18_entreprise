# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # Standard Odoo allows 5 characters; 6 are needed for codes like INV/HW
    code = fields.Char(size=6)
