# -*- coding: utf-8 -*-

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def create_picking_from_so(self):
        for move in self:
            move.assign_picking()

    @api.multi
    def action_confirm(self):
        res = super(StockMove, self).action_confirm()
        if self._context.get('is_from_so', False):
            for record in self:
                record.picking_id.force_assign()
        return res