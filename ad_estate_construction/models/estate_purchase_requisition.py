from odoo import models, fields, api, _
from odoo.exceptions import UserError

class EstatePurchaseRequisition(models.Model):
    _name = 'estate.purchase.requisition'
    _description = 'Site Purchase Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Requisition Ref', required=True, default='New', copy=False)
    project_id = fields.Many2one('estate.project', string='Project', required=True, tracking=True)
    boq_id = fields.Many2one('estate.boq', string='BOQ Phase', domain="[('project_id', '=', project_id)]", required=True, tracking=True)
    requested_by_id = fields.Many2one('res.users', string='Site Engineer', default=lambda self: self.env.user, required=True, tracking=True)
    date_required = fields.Date(string='Date Required', required=True)

    line_ids = fields.One2many('estate.purchase.requisition.line', 'requisition_id', string='Requisition Items')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted to Manager'),
        ('approved', 'Approved'),
        ('done', 'PO Created'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.purchase.requisition') or 'REQ/0001'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        for line in self.line_ids:
            if line.qty_requested > line.boq_remaining_qty:
                raise UserError(_("Requested quantity (%s) for item '%s' exceeds remaining BOQ quantity (%s).") % (
                    line.qty_requested, line.product_id.display_name, line.boq_remaining_qty
                ))
        self.write({'state': 'approved'})

    def action_create_po(self):
        self.ensure_one()
        po_vals = {
            'project_id': self.project_id.id,
            'order_type': 'po',
            'partner_id': self.project_id.architect_id.id or self.env['res.partner'].search([], limit=1).id,
            'order_line': []
        }
        for line in self.line_ids:
            po_vals['order_line'].append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.display_name,
                'product_qty': line.qty_requested,
                'product_uom': line.product_id.uom_po_id.id or line.product_id.uom_id.id,
                'price_unit': line.boq_line_id.unit_rate or 0.0,
                'date_planned': self.date_required,
            }))
        po = self.env['purchase.order'].create(po_vals)
        self.write({'state': 'done'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
        }


class EstatePurchaseRequisitionLine(models.Model):
    _name = 'estate.purchase.requisition.line'
    _description = 'Purchase Requisition Line'

    requisition_id = fields.Many2one('estate.purchase.requisition', string='Requisition', ondelete='cascade', required=True)
    boq_line_id = fields.Many2one('estate.boq.line', string='BOQ Line Item', required=True)
    product_id = fields.Many2one('product.product', string='Material', related='boq_line_id.product_id', readonly=True)
    qty_requested = fields.Float(string='Requested Qty', default=1.0, required=True)
    boq_remaining_qty = fields.Float(string='BOQ Available Qty', related='boq_line_id.remaining_qty', readonly=True)

    @api.constrains('qty_requested')
    def _check_boq_quantity(self):
        for line in self:
            if line.qty_requested > line.boq_remaining_qty:
                raise UserError(_("Cannot request %s units of %s. Maximum remaining in BOQ is %s.") % (
                    line.qty_requested, line.product_id.display_name, line.boq_remaining_qty
                ))
