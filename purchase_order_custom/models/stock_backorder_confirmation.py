from odoo import models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self:
            # Angalia kama ni Delivery au Receipt inayohusika na operations
            if picking.state in ['assigned', 'confirmed', 'waiting']:
                
                # Angalia kama kuna bidhaa iliyopungua (Demand > Quantity iliyofanyika)
                has_partial_qty = False
                for move in picking.move_ids_without_package:
                    # Inachukua quantity kulingana na toleo la Odoo (quantity au quantity_done)
                    done_qty = getattr(move, 'quantity', None)
                    if done_qty is None:
                        done_qty = getattr(move, 'quantity_done', 0.0)
                        
                    if move.product_uom_qty > done_qty:
                        has_partial_qty = True
                        break
                
                # Kama kuna upungufu (maana yake backorder itatokea), kagua attachment
                if has_partial_qty:
                    # Angalia kama kuna attachment iliyowekwa kwenye hii picking (chatter / paperclip)
                    attachment_count = self.env['ir.attachment'].search_count([
                        ('res_model', '=', 'stock.picking'),
                        ('res_id', '=', picking.id)
                    ])
                    
                    if attachment_count == 0:
                        msg_attachments = self.env['ir.attachment'].search_count([
                            ('res_model', '=', 'mail.message'),
                            ('res_id', 'in', picking.message_ids.ids)
                        ])
                        attachment_count += msg_attachments
                    
                    # Kama badohakuna attachment, mzuie hapa hapa kabla ya pop-up haijaja!
                    if attachment_count == 0:
                        raise UserError(
                            f"You cannot proceed! Please attach the required document to this Delivery/Receipt ({picking.name}) in the attachment section below before validating the shortage items."
                        )

        return super().button_validate()