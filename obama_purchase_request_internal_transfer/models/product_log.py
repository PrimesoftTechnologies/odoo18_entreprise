from markupsafe import Markup

from odoo import models, _
from odoo.tools import html2plaintext

# technical / noisy fields that are never logged
SKIP_PREFIXES = ('message_', 'activity_', 'website_message', 'rating_', 'access_', 'my_activity')
SKIP_FIELDS = {
    'id', 'display_name', 'write_date', 'write_uid', 'create_date', 'create_uid',
    '__last_update', 'message_ids', 'message_follower_ids', 'message_partner_ids',
}
MAX_LEN = 300


class ProductChangeLogMixin(models.AbstractModel):
    """Posts a log note on the chatter describing what changed on a product."""
    _name = 'obama.product.change.log.mixin'
    _description = 'Product change log (chatter)'

    # ------------------------------------------------------------------
    def _obama_log_fields(self, vals):
        names = []
        for fname in vals:
            field = self._fields.get(fname)
            if not field or fname in SKIP_FIELDS or fname.startswith(SKIP_PREFIXES):
                continue
            if getattr(field, 'tracking', False):
                continue  # Odoo already logs tracked fields natively
            names.append(fname)
        return names

    def _obama_format(self, fname):
        self.ensure_one()
        field = self._fields[fname]
        val = self[fname]
        ftype = field.type
        if ftype in ('binary', 'image'):
            return '__binary__'
        if ftype == 'many2one':
            res = val.display_name or '-'
        elif ftype in ('one2many', 'many2many'):
            res = ', '.join(val.mapped('display_name')) or '-'
        elif ftype == 'selection':
            mapping = dict(field._description_selection(self.env))
            res = mapping.get(val, val) or '-'
        elif ftype == 'boolean':
            res = _('Yes') if val else _('No')
        elif ftype == 'html':
            res = html2plaintext(val or '').strip() or '-'
        elif val in (False, None, ''):
            res = '-'
        else:
            res = str(val)
        return res if len(res) <= MAX_LEN else res[:MAX_LEN] + '...'

    def _obama_post_changes(self, changes):
        self.ensure_one()
        if not hasattr(self, 'message_post'):
            return
        items = Markup('').join(
            Markup('<li><strong>%s</strong>: %s</li>') % (
                label, _('updated') if old is None else Markup('%s &rarr; %s') % (old, new))
            for label, old, new in changes)
        body = Markup('<p>%s</p><ul>%s</ul>') % (_('Product updated:'), items)
        self.message_post(
            body=body, message_type='notification', subtype_xmlid='mail.mt_note')

    def _obama_write_and_log(self, vals, super_write):
        """Run super_write(vals) and log the differences."""
        ctx = self.env.context
        if ctx.get('obama_no_log') or ctx.get('install_mode') or not self:
            return super_write(vals)
        fnames = self._obama_log_fields(vals)
        if not fnames:
            return super_write(vals)
        old = {rec.id: {f: rec._obama_format(f) for f in fnames} for rec in self}
        res = super_write(vals)
        for rec in self:
            changes = []
            for fname in fnames:
                label = rec._fields[fname].string or fname
                new = rec._obama_format(fname)
                if new == '__binary__':
                    changes.append((label, None, None))
                elif new != old.get(rec.id, {}).get(fname):
                    changes.append((label, old[rec.id][fname], new))
            if changes:
                rec._obama_post_changes(changes)
        return res


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'obama.product.change.log.mixin']

    def write(self, vals):
        # flag so the variant (inverse writes) does not log the same change twice
        return self._obama_write_and_log(
            vals,
            lambda v: super(ProductTemplate, self.with_context(obama_from_template=True)).write(v))


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'obama.product.change.log.mixin']

    def write(self, vals):
        if self.env.context.get('obama_from_template'):
            return super().write(vals)
        return self._obama_write_and_log(vals, lambda v: super(ProductProduct, self).write(v))
