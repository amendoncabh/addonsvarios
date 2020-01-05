# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        required=False,
        readonly=True,
    )

    acc_name_en = fields.Char(
        string="Account Name (EN)",
        required=False,
    )

    _sql_constraints = [
        ('unique_number', 'check(1=1)', 'Account Number must be unique'),
    ]

    @api.depends('sanitized_acc_number', 'branch_id')
    # @api.onchange('acc_number', 'branch_id')
    def _onchange_sanitized_acc_number(self):
        for bank in self:
            bank.sanitized_acc_number += bank.branch_id.branch_name

    @api.model
    def default_get(self, default_fields):
        res = super(ResPartnerBank, self).default_get(default_fields)
        asset_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if active_model == 'res.partner' and asset_id:
            partner_id = self.env['res.partner'].browse(asset_id)
            branch_id = partner_id.branch_id.id
            res['branch_id'] = branch_id
        return res