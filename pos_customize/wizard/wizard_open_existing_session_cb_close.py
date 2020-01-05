# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

__author__ = 'Papatpon'

class ConfirmCloseSession(models.TransientModel):
    _name = 'pos.config.confirm.close'
    _description = "Confirm Close Session"

    @api.multi
    def action_close(self):
        active_id = self._context.get('active_id')
        pos_config = self.env['pos.config'].browse(active_id)
        pos_config.open_existing_session_cb_close()
