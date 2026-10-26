from odoo import SUPERUSER_ID, api

OLD_LABELS = {
    'rent': 'Rent',
    'salary': 'Salaries',
    'electricity': 'Electricity / Water',
    'transport': 'Transport',
    'marketing': 'Marketing / Advertising',
    'repair': 'Repairs / Maintenance',
    'tax': 'Taxes / Licenses',
    'other': 'Other',
}


def migrate(cr, version):
    """Convert old category values into configurable expense types
    (only the ones that were actually used)."""
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'fred_store_expense' AND column_name = 'category_old'
    """)
    if not cr.fetchone():
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Type = env.sudo().env['fred.expense.type'].with_context(active_test=False)
    cache = {}
    cr.execute("SELECT id, category_old FROM fred_store_expense WHERE expense_type_id IS NULL")
    for rec_id, cat in cr.fetchall():
        name = OLD_LABELS.get(cat or 'other', cat or 'Other')
        if name not in cache:
            cache[name] = Type.search([('name', '=', name)], limit=1) or Type.create({'name': name})
        cr.execute("UPDATE fred_store_expense SET expense_type_id = %s WHERE id = %s",
                   (cache[name].id, rec_id))
    cr.execute("ALTER TABLE fred_store_expense DROP COLUMN category_old")
