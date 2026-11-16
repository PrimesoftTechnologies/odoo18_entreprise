# -*- coding: utf-8 -*-
"""Pre-create review_required (False) so that old bank entries are NOT flagged for review,
and widen the journal short code to 6 characters."""


def migrate(cr, version):
    if not version:
        return
    cr.execute("ALTER TABLE account_move ADD COLUMN IF NOT EXISTS review_required boolean DEFAULT false")
    cr.execute("UPDATE account_move SET review_required = false WHERE review_required IS NULL")
    cr.execute("ALTER TABLE account_journal ALTER COLUMN code TYPE varchar(6)")
