from odoo import models, fields, api


class PhoneUserAccess(models.Model):
    _name = 'phone.user.access'
    _description = 'Phone Shop User Access Rights'
    _rec_name = 'user_id'
    _order = 'id desc'

    # =========================================================
    # USER
    # =========================================================

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade'
    )

    user_login = fields.Char(
        string='Login (Username)',
        related='user_id.login',
        store=True,
        readonly=True
    )

    user_email = fields.Char(
        string='Email',
        related='user_id.email',
        store=True,
        readonly=True
    )

    # =========================================================
    # ALLOWED MENUS (TABS)
    # =========================================================

    allow_dashboard = fields.Boolean(string='Dashboard', default=True)
    allow_pos = fields.Boolean(string='POS / Sell', default=True)
    allow_phones = fields.Boolean(string='Phones & Stock', default=True)
    allow_trade_in = fields.Boolean(string='Trade-In / Exchange', default=True)
    allow_debts = fields.Boolean(string='Debt & Installments', default=True)
    allow_purchases = fields.Boolean(string='Purchases', default=True)          # ← MPYA
    allow_suppliers = fields.Boolean(string='Suppliers', default=True)
    allow_staff = fields.Boolean(string='Staff / Users', default=False)
    allow_reports = fields.Boolean(string='Reports', default=True)
    allow_settings = fields.Boolean(string='Configuration', default=False)

    # =========================================================
    # STATUS
    # =========================================================

    active = fields.Boolean(string='Active', default=True)

    notes = fields.Text(string='Notes')

    # =========================================================
    # COMPUTE: ALLOWED TABS AS JSON STRING
    # =========================================================

    allowed_tabs = fields.Char(
        string='Allowed Tabs (JSON)',
        compute='_compute_allowed_tabs',
        store=True
    )

    @api.depends(
        'allow_dashboard',
        'allow_pos',
        'allow_phones',
        'allow_trade_in',
        'allow_debts',
        'allow_purchases',          # ← MPYA
        'allow_suppliers',
        'allow_staff',
        'allow_reports',
        'allow_settings',
    )
    def _compute_allowed_tabs(self):
        for record in self:
            tabs = []
            if record.allow_dashboard:
                tabs.append('dashboard')
            if record.allow_pos:
                tabs.append('pos')
            if record.allow_phones:
                tabs.append('phones')
            if record.allow_trade_in:
                tabs.append('trade_in')
            if record.allow_debts:
                tabs.append('debts')
            if record.allow_purchases:          # ← MPYA
                tabs.append('purchases')
            if record.allow_suppliers:
                tabs.append('suppliers')
            if record.allow_staff:
                tabs.append('staff')
            if record.allow_reports:
                tabs.append('reports')
            if record.allow_settings:
                tabs.append('settings')

            record.allowed_tabs = ','.join(tabs) if tabs else ''

    # =========================================================
    # CREATE USER (KUTOKA CONFIGURATION)
    # =========================================================

    @api.model
    def create_user_with_access(self, vals):
        """
        Unda Odoo user mpya + access rights
        vals = {
            'name': 'Juma Hamisi',
            'login': 'juma',
            'password': 'juma123',
            'email': 'juma@shop.co.tz',
            'allowed_tabs': ['dashboard', 'pos', 'phones'],
            'group_ids': [...]
        }
        """
        name = vals.get('name', '').strip()
        login = vals.get('login', '').strip()
        password = vals.get('password', '').strip()
        email = vals.get('email', '').strip()
        allowed_tabs = vals.get('allowed_tabs', [])

        if not name or not login or not password:
            raise ValueError('Name, login, and password are required.')

        # 1. Create Odoo user
        user_vals = {
            'name': name,
            'login': login,
            'password': password,
            'email': email or False,
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('base.group_partner_manager').id,
            ])],
        }

        user = self.env['res.users'].create(user_vals)

        # 2. Create access record
        access_vals = {
            'user_id': user.id,
            'allow_dashboard': 'dashboard' in allowed_tabs,
            'allow_pos': 'pos' in allowed_tabs,
            'allow_phones': 'phones' in allowed_tabs,
            'allow_trade_in': 'trade_in' in allowed_tabs,
            'allow_debts': 'debts' in allowed_tabs,
            'allow_purchases': 'purchases' in allowed_tabs,          # ← MPYA
            'allow_suppliers': 'suppliers' in allowed_tabs,
            'allow_staff': 'staff' in allowed_tabs,
            'allow_reports': 'reports' in allowed_tabs,
            'allow_settings': 'settings' in allowed_tabs,
            'active': True,
        }

        access = self.create(access_vals)

        return {
            'user_id': user.id,
            'access_id': access.id,
            'login': user.login,
        }

    # =========================================================
    # UPDATE USER ACCESS
    # =========================================================

    def update_access(self, allowed_tabs):
        """Update allowed tabs for existing user"""
        for record in self:
            record.write({
                'allow_dashboard': 'dashboard' in allowed_tabs,
                'allow_pos': 'pos' in allowed_tabs,
                'allow_phones': 'phones' in allowed_tabs,
                'allow_trade_in': 'trade_in' in allowed_tabs,
                'allow_debts': 'debts' in allowed_tabs,
                'allow_purchases': 'purchases' in allowed_tabs,          # ← MPYA
                'allow_suppliers': 'suppliers' in allowed_tabs,
                'allow_staff': 'staff' in allowed_tabs,
                'allow_reports': 'reports' in allowed_tabs,
                'allow_settings': 'settings' in allowed_tabs,
            })

    # =========================================================
    # GET CURRENT USER ACCESS
    # =========================================================

    @api.model
    def get_current_user_access(self):
        """
        Return allowed tabs ya user aliye login.

        Tunatumia active_test=False ili hata kama access rule ni inactive,
        method bado inaipata — kisha tuna-decide kama user ana ruhusa au la.
        """
        user = self.env.user

        # Tafuta access record — hata inactive (ili admin aone)
        access = self.with_context(active_test=False).search(
            [('user_id', '=', user.id)], limit=1
        )

        # Kama hana access record → angalia kama ni admin
        if not access:
            if user.has_group('base.group_system'):
                return ['dashboard', 'pos', 'phones', 'trade_in',
                        'debts', 'purchases', 'suppliers', 'staff',
                        'reports', 'settings']
            return ['dashboard']

        # Kama access record ni INACTIVE → hana ruhusa ya menus zozote
        if not access.active:
            return []

        tabs = []
        if access.allow_dashboard:
            tabs.append('dashboard')
        if access.allow_pos:
            tabs.append('pos')
        if access.allow_phones:
            tabs.append('phones')
        if access.allow_trade_in:
            tabs.append('trade_in')
        if access.allow_debts:
            tabs.append('debts')
        if access.allow_purchases:          # ← MPYA
            tabs.append('purchases')
        if access.allow_suppliers:
            tabs.append('suppliers')
        if access.allow_staff:
            tabs.append('staff')
        if access.allow_reports:
            tabs.append('reports')
        if access.allow_settings:
            tabs.append('settings')

        return tabs

    # =========================================================
    # TOGGLE ACTIVE / INACTIVE (kwa ajili ya UI)
    # =========================================================

    def action_toggle_active(self):
        """
        Toggle active state ya access rule NA Odoo user.
        Inaitwa kutoka kwenye dashboard.js.
        """
        for record in self:
            new_active = not record.active

            # 1) Update access rule
            record.active = new_active

            # 2) Update Odoo user (ili user ashindwe kulogin)
            if record.user_id:
                record.user_id.sudo().write({'active': new_active})

        return True