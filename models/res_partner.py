from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    user_level_id = fields.Many2one(
        'adelanta.user.level',
        string='Nivel de Usuario'
    )
