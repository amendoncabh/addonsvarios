# -*- coding: utf-8 -*-

from odoo import fields
from odoo import models
from odoo import fields, models, api, _



class AccountJournal(models.Model):
    _inherit = 'account.journal'

    redeem_type_id = fields.Many2one(
        comodel_name='redeem.type',
        string='Redeem Type'
    )

    @api.onchange('redeem_type_id')
    def onchange_redeem_type(self):
        self.code = self.redeem_type_id.code
