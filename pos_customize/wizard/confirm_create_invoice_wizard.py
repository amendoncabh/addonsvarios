
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api
from odoo import fields
from odoo import models
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT


class ConfirmCreateInvoiceWizard(models.TransientModel):
    _name = 'confirm.create.invoice.wizard'
    _description = "wizard confirm before create invoice"

    order_id = fields.Many2one(
        comodel_name="pos.order",
        string="order id",
        required=False,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=False,
    )

    warning_text = fields.Char(
        compute='_compute_warning_text',
        track_visibility='onchange',
    )

    @api.multi
    def action_confirm(self):
        active_id = self._context.get('active_id', False)
        if active_id:
            self.env['pos.order'].browse(active_id).action_pos_order_invoice()

    @api.depends('order_id', 'partner_id')
    def _compute_warning_text(self):
        for record in self:
            total_address = record.partner_id._display_address(without_company=True)
            total_address = '<br/>'.join(total_address.splitlines())

            record.warning_text = "Receipt no: " + record.order_id.inv_no + "<br/>"\
                                  + "Customer: " + record.partner_id.name + "<br/>"\
                                  + "Address: " + total_address

