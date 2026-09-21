from odoo import fields, models

class TimberResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    timber_board_percentage = fields.Float(
        string='Board Percentage (%)', 
        default=60.0, 
        config_parameter='timber.board_percentage',
        help="Weka asilimia inayokwenda kwenye mbao zilizotoka (Mfano: 60%)"
    )
    timber_waste_percentage = fields.Float(
        string='Waste Percentage (%)', 
        default=40.0, 
        config_parameter='timber.waste_percentage',
        help="Weka asilimia inayokwenda kwenye taka (Mfano: 40%)"
    )