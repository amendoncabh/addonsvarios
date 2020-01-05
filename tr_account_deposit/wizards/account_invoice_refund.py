# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Trinity Roots co.,ltd. (<http://www.trinityroots.co.th>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from odoo import models, fields, osv
from odoo.tools.translate import _


class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""
    _inherit = "account.invoice.refund"

    account_refund_id = fields.Many2one(
        comodel_name='account.account',
        string='Refund Deposit Account',
    )
