# -*- coding: utf-8 -*-

from openerp import fields, models


class PosCashBoxReason(models.Model):

    _name = 'pos.cash.box.reason'

    name = fields.Char(
        string='Reason',
        size=32,
        required=True,
    )
