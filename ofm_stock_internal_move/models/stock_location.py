# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockLocation(models.Model):
    _inherit = "stock.location"


    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=160):
        branch_id = self._context.get('branch_id', False)
        if branch_id:
            branch = self.env['pos.branch'].browse(branch_id)
            company_id = branch.pos_company_id.id
            warehouse_code = branch.warehouse_id.code
            recs = self.search(
                [
                    ('company_id', '=', company_id),
                    ('complete_name', 'like', warehouse_code + '/')
                ] + args
            )
            if name:
                name = name.upper()
                recs = recs.filtered(
                    lambda x: name in x.name.upper()
                )
            return recs.sudo().name_get()
        return super(StockLocation, self).name_search(name, args, operator, limit)