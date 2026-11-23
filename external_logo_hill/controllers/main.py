import base64

from odoo import SUPERUSER_ID, api, http
from odoo.http import request
from odoo.modules.registry import Registry
from odoo.tools.mimetypes import guess_mimetype


class ExternalLogoHill(http.Controller):

    @http.route('/external_logo_hill/logo', type='http', auth='none', cors='*')
    def external_logo(self, dbname=None, company=None, **kw):
        """Inatoa External Logo kwa watumiaji ambao hawajalogin.
        Kama haijawekwa, inarudisha main logo ya kawaida."""
        fallback = '/web/binary/company_logo' + ('?dbname=%s' % dbname if dbname else '')

        db = request.db or dbname
        if not db:
            try:
                db = http.db_monodb()
            except Exception:
                db = None
        if not db:
            return request.redirect(fallback, local=True)

        data = None
        try:
            registry = Registry(db)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                companies = env['res.company'].search([], order='sequence, id')
                if company and str(company).isdigit():
                    companies = companies.filtered(lambda c: c.id == int(company)) or companies
                for comp in companies:
                    if comp.external_logo_hill:
                        data = base64.b64decode(comp.external_logo_hill)
                        break
        except Exception:
            data = None

        if not data:
            return request.redirect(fallback, local=True)

        mimetype = guess_mimetype(data, default='image/png')
        return request.make_response(data, headers=[
            ('Content-Type', mimetype),
            ('Cache-Control', 'public, max-age=300'),
        ])
