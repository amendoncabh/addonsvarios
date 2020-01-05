# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def action_confirm_stock_immediate_transfer(self, picking_id):
        stock_immediate_transfer_id = self.create({
            'pick_id': picking_id.id
        })

        ctx_picking_id = dict(self._context)
        ctx_picking_id.update({
            'picking_id_current': picking_id.id,
        })

        stock_immediate_transfer_id.with_context(ctx_picking_id).process()

        return stock_immediate_transfer_id
