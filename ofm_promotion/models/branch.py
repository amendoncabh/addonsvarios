# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import fields
from odoo import models


class PosBranch(models.Model):
    _inherit = 'pos.branch'

    promotion_ids = fields.Many2many(
        'pos.promotion',
        'pos_branch_pos_promotion_rel',
        'pos_branch_id',
        'pos_promotion_id',
        domain=[('active', '=', True), ('date_end', '>=', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))]
    )
