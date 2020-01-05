# -*- coding: utf-8 -*-

import logging

from odoo import fields, api, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    return_approver_id = fields.Many2one(
        comodel_name="res.users",
        string="Return Approver",
        required=False,
        readonly=True,
    )

    return_approve_datetime = fields.Datetime(
        string="Return Approve Time",
        required=False,
        readonly=True,
    )

    @api.multi
    @api.depends('picking_type_name')
    def _compute_invisible_reverse(self):
        super(StockPicking, self)._compute_invisible_reverse()
        for record in self:
            if not record.reverse_invisible and record.group_id:
                if self.env['sale.order'].search([('procurement_group_id', '=', record.group_id.id)]):
                    record.reverse_invisible = True
