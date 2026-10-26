def migrate(cr, version):
    """Keep the old hard-coded 'category' values so they can be converted."""
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'fred_store_expense' AND column_name = 'category'
    """)
    if cr.fetchone():
        cr.execute("ALTER TABLE fred_store_expense RENAME COLUMN category TO category_old")
