def migrate(cr, version):
    """The log structure changed: drop old-style rows (create / header changes)."""
    cr.execute("SELECT to_regclass('apex_quotation_log')")
    if cr.fetchone()[0]:
        cr.execute("DELETE FROM apex_quotation_log")
