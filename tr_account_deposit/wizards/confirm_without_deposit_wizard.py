# -*- coding: utf-8 -*-

from odoo import api, models


class ConfirmWithoutDeposit(models.TransientModel):
    _name = 'confirm.without.deposit.wizard'

    @api.multi
    def action_confirm(self):
        for rec in self:
            active_id = rec._context.get('active_id', False)

            if active_id:
                sale_id = rec.env['sale.order'].browse(active_id)

                return sale_id.action_confirm_so()
