# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleSession(models.Model):
    _name = 'sale.session'
    _order = 'id desc'

    user_id = fields.Many2one(
        comodel_name='res.users',
        string="User",
        readonly=True,
        required=True,
        default=lambda self: self.env.uid,
    )

    config_id = fields.Many2one(
        comodel_name="pos.config",
        string="Pos Config"
    )

    config_name = fields.Char(
        string="Config",
        readonly=True,
        related="config_id.name",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related='config_id.company_id',
    )

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        related='config_id.branch_id',
    )

    login_number = fields.Integer(
        string='Login Sequence Number',
        default=0,
        track_visibility='onchange'
    )

    sequence_number = fields.Integer(
        string='Sequence Number',
        help='A session-unique sequence number for the order',
        default=1
    )

    sale_type = fields.Selection(
        string="Sale type",
        selection=[
           ('instore', 'In Store'),
           ('dropship', 'Dropship'),
        ],
        required=True,
    )

    @api.multi
    def login(self):
        self.ensure_one()
        self.write({
            'login_number': self.login_number + 1,
        })
