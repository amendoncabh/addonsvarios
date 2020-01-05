# -*- coding: utf-8 -*-


from odoo import api
from odoo import fields
from odoo import models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    pos_id = fields.Many2one(
        comodel_name="pos.order",
        string="POS ID",
        required=False,
        copy=True,
    )

    change_rounding = fields.Float(
        string='Rounding',
        digits=0,
        track_visibility='onchange',
        store=True,
        readonly=True,
    )

    @api.multi
    def name_get(self):
        return [(r.id, r.number) for r in self]
