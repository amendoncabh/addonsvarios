# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import sets

import openerp.addons.decimal_precision as dp
from openerp import fields, models, api
from openerp.tools.translate import _


class POSSessionSequence(models.Model):
    _name = 'pos.session.sequence'
    _description = 'POS Session Sequence'

    size = fields.Char(
        'Padding',
    )
    res_model = fields.Char(
        'Res Model',
    )
    branch_id = fields.Many2one(
        'pos.branch',
        'Branch Location',
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        copy=False,
    )
    branch_code = fields.Char(
        'Branch Code',
        required=True,
    )
    sequence_id = fields.Many2one(
        'ir.sequence',
        string='Session Sequence',
        ondelete='restrict',
    )