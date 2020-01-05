# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import except_orm
from odoo.tools import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    type_sale_ofm = fields.Boolean(
        string='Type Sales OFM',
        readonly=True
    )
