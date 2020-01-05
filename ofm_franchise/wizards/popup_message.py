# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PopUpMessage(models.TransientModel):
    _name = 'popup.message'
    _description = "Pop Up Message"

    name = fields.Char('Message')

    @api.multi
    def check_repeat_calculation(self, vals):
    	string = ','.join(vals.mapped('name'))
    	return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'popup.message',
            'target': 'new',
            'context': {'default_name': "Repeat Calculation.\n%s"%string}
        }