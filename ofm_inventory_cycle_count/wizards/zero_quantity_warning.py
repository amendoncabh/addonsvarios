# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError



class ImportCounted(models.TransientModel):
    _name = 'zero.quantity.warning'
    _description = "Warning when qauntity of product is 0"

    @api.multi
    def action_approve(self, data):
        for item in self:
            cycle_count_id = item.env[data['active_model']].browse(data['active_id'])
            cycle_count_id.approved = True
            cycle_count_id.state = 'confirm'

            
            