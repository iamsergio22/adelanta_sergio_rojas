from odoo import models, api
from odoo import api, fields, models, _, Command
from odoo.tools import (frozendict)



class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _onchange_partner_id_user_level(self):
        if self.partner_id and self.partner_id.user_level_id:
            level = self.partner_id.user_level_id.id
            domain = [('applicable_user_levels', 'in', [level])]
            return {'domain': {'payment_term_id': domain}}