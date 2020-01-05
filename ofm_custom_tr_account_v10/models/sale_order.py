# -*- coding: utf-8 -*-

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()

        picking_id_current = self._context.get('picking_id_current', False)

        res.update({
            'branch_id': self.branch_id.id,
            'so_id': self.id,
            'picking_id': picking_id_current,
        })

        return res
