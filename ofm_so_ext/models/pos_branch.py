# -*- coding: utf-8 -*-
from odoo import models, api


class SoExtPosBranch(models.Model):
    _inherit = "pos.branch"

    @api.model
    def create(self, vals):
        res = super(SoExtPosBranch, self).create(vals)

        warehouse_id = vals.get('warehouse_id', False)

        if warehouse_id:
            warehouse_id = self.env['stock.warehouse'].browse(warehouse_id)
            partner_id = warehouse_id.company_id.partner_id
            partner_id.update({
                'branch_id': res.id
            })

        return res