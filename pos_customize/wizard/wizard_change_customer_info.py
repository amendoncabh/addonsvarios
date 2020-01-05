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

from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.exceptions import except_orm
from odoo.tools.translate import _


class wizard_change_customer_info(models.TransientModel):
    _name = "wizard.chage.customer.info"

    @api.model
    def _default_name(self):
        customer_id = self.env.context["default_customer_id"]
        customer = self.env['res.partner'].browse([customer_id])
        return customer.name

    @api.model
    def _default_street(self):
        customer_id = self.env.context["default_customer_id"]
        customer = self.env['res.partner'].browse([customer_id])
        return customer.street

    @api.model
    def _default_street2(self):
        customer_id = self.env.context["default_customer_id"]
        customer = self.env['res.partner'].browse([customer_id])
        return customer.street2

    @api.model
    def _default_city(self):
        customer_id = self.env.context["default_customer_id"]
        customer = self.env['res.partner'].browse([customer_id])
        return customer.city

    @api.model
    def _default_vat(self):
        customer_id = self.env.context["default_customer_id"]
        customer = self.env['res.partner'].browse([customer_id])
        return customer.vat

    @api.model
    def _default_state_id(self):
        customer_id = self.env.context["default_customer_id"]
        customer = self.env['res.partner'].browse([customer_id])
        return customer.state_id.id

    @api.model
    def _default_zip(self):
        customer_id = self.env.context["default_customer_id"]
        customer = self.env['res.partner'].browse([customer_id])
        return customer.zip

    @api.model
    def _default_shop_id(self):
        customer_id = self.env.context["default_customer_id"]
        customer = self.env['res.partner'].browse([customer_id])
        return customer.shop_id

    @api.model
    def _default_phone(self):
        customer_id = self.env.context["default_customer_id"]
        customer = self.env['res.partner'].browse([customer_id])
        return customer.phone

    @api.model
    def _default_mobile(self):
        customer_id = self.env.context["default_customer_id"]
        customer = self.env['res.partner'].browse([customer_id])
        return customer.mobile

    customer_id = fields.Many2one(
        'res.partner'
    )
    name = fields.Char(
        'Name',
        default=_default_name
    )
    street = fields.Char(
        'Address',
        default=_default_street
    )
    street2 = fields.Char(
        'Road',
        default=_default_street2
    )
    city = fields.Char(
        'City',
        default=_default_city
    )
    vat = fields.Char(
        'TaxID',
        default=_default_vat
    )
    state_id = fields.Many2one(
        'res.country.state',
        default=_default_state_id
    )
    zip = fields.Char(
        'Zip',
        default=_default_zip
    )
    shop_id = fields.Char(
        'Branch',
        default=_default_shop_id
    )
    phone = fields.Char(
        'Phone',
        default=_default_phone
    )
    mobile = fields.Char(
        'Mobile',
        default=_default_mobile
    )

    @api.multi
    def confirm_change(self):
        old_customer = self.customer_id
        active_id = self.env.context["active_id"]
        pos_order = self.env['pos.order'].browse([active_id])
        pos_order.write({'printed': False, 'printed_first': False})

        old_log = ""
        new_log = ""

        if not pos_order.tax_invoice:
            raise except_orm(_('Error!'), _('This order not have tax invoice'))
        if not pos_order.partner_id:
            raise except_orm(_('Error!'), _('Please provide a customer'))

        domain = {}

        partner_old = old_customer.name or "-"
        partner_new = self.name or "-"

        old_log = partner_old + " || "
        new_log = partner_new + " || "
        domain.update({'name': partner_new})

        old_log += "street:%s || " %(old_customer.street or "-")
        new_log += "street:%s || " %(self.street or "-")
        domain.update({'street': self.street})

        old_log += "street2:%s || " %(old_customer.street2 or " ")
        new_log += "street2:%s || " %(self.street2 or " ")
        domain.update({'street2': self.street2})

        old_log += "city:%s || " % (old_customer.city or " ")
        new_log += "city:%s || " % (self.city or " ")
        domain.update({'city': self.city})

        old_log += "vat:%s || " % (old_customer.vat or " ")
        new_log += "vat:%s || " % (self.vat or " ")
        domain.update({'vat': self.vat})

        old_log += "state:%s || " % (old_customer.state_id.name or " ")
        new_log += "state:%s || " % (self.state_id.name or " ")
        domain.update({'state_id': self.state_id.id})

        old_log += "zip:%s || " % (old_customer.zip or " ")
        new_log += "zip:%s || " % (self.zip or " ")
        domain.update({'zip': self.zip})

        old_log += "branch:%s || " % (old_customer.shop_id or " ")
        new_log += "branch:%s || " % (self.shop_id or " ")
        domain.update({'shop_id': self.shop_id})

        old_log += "phone:%s || " % (old_customer.phone or " ")
        new_log += "phone:%s || " % (self.phone or " ")
        domain.update({'phone': self.phone})

        old_log += "mobile:%s || " % (old_customer.mobile or " ")
        new_log += "mobile:%s || " % (self.mobile or " ")
        domain.update({'mobile': self.mobile})

        date_now = datetime.now() + timedelta(hours=7)
        time_at_now = (date_now).strftime('%Y-%m-%d')

        new_inv_ref = self.tax_invoice = pos_order.session_id.config_id.branch_id.sequence_tax_invoice_id.with_context({
            'date': time_at_now
        }).next_by_id()

        vals = {
            'old_log': old_log,
            'new_log': new_log,
            'old_invoice_ref': pos_order.tax_invoice,
            'new_invoice_ref': new_inv_ref,
            'pos_order_id': pos_order.id,
            'date': (datetime.now() + timedelta(hours=7)),
            'user_id': self._uid,
        }
        self.env['customer.change.log'].create(vals)
        pos_order.tax_invoice = new_inv_ref

        if domain:
            self.customer_id.write(domain)

class customer_change_log(models.Model):
    _name = "customer.change.log"

    date = fields.Date('Modify Date')
    user_id = fields.Many2one(
        'res.users',
        'User Modify',
        index=True,
    )
    pos_order_id = fields.Many2one(
        'pos.order',
        index=True,
    )
    old_log = fields.Char("old detail")
    new_log = fields.Char("new detail")
    old_invoice_ref = fields.Char("Old Invoice")
    new_invoice_ref = fields.Char("New Invoice")