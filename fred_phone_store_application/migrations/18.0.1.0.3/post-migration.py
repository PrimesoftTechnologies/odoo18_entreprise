from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Convert old category values to the new configurable expense types."""
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'fred_store_expense' AND column_name = 'category_old'
    """)
    if not cr.fetchone():
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute("""
        SELECT id, category_old FROM fred_store_expense
        WHERE expense_type_id IS NULL
    """)
    for rec_id, cat in cr.fetchall():
        xmlid = 'fred_phone_store_application.expense_type_%s' % (cat or 'other')
        etype = env.ref(xmlid, raise_if_not_found=False) or env.ref(
            'fred_phone_store_application.expense_type_other', raise_if_not_found=False)
        if etype:
            cr.execute("UPDATE fred_store_expense SET expense_type_id = %s WHERE id = %s",
                       (etype.id, rec_id))
    cr.execute("ALTER TABLE fred_store_expense DROP COLUMN category_old")
