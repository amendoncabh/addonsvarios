# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

import odoo.exceptions
from odoo import api
from odoo import fields
from odoo import models
from odoo import tools

_logger = logging.getLogger(__name__)

class res_users(models.Model):

    _inherit = 'res.users'

    pos_config = fields.Many2one(
        'pos.config',
        'Default Point of Sale',
        domain=[('state', '=', 'active')]
    )

    ignore_repeat = odoo.fields.Boolean(
        related='partner_id.ignore_repeat',
        inherited=True,
    )
    vat = odoo.fields.Char(
        related='partner_id.vat',
        inherited=True,
    )
    branch_id = fields.Integer(
        related='partner_id.branch_id',
        inherited=True,
    )
    branch_ids = fields.Many2many(
        'pos.branch',
        'pos_branch_res_users_rel',
        'user_id',
        'branch_id',
        'POS Branch',
        copy=False,
    )

    @api.model
    def create(self, vals):
        vals['vat'] = '0000000000000'
        vals['ignore_repeat'] = False
        user_id = super(res_users, self).create(vals)
        user_id.partner_id.write({'customer': False})

        return user_id

    @api.onchange('login')
    def on_change_login(self):
        if self.login and not tools.single_email_re.match(self.login):
            self.email = self.login + '@temp.com'
        super(res_users, self).on_change_login()
