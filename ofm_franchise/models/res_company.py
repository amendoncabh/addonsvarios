# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Company(models.Model):
    _inherit = "res.company"

    contact_ids = fields.One2many(
        comodel_name="company.contact",
        inverse_name="company_id",
        string="Key Contact",
        required=False,
        index=True,
    )

    company_type = fields.Selection(
        string='Company Type',
        selection=[
           ('personal', 'Personal'),
           ('corporate', 'Corporate'),
        ],
        required=True,
        default='personal',
    )

    state = fields.Selection(
        selection=[
           ('active', 'Active'),
           ('expire', 'Expire'),
           ('cancel', 'Cancel'),
        ],
        required=True,
        default='active',
    )

    @api.multi
    def action_com_expire(self):
        self.write({'state': 'expire'})
        return True

    @api.multi
    def action_com_cancel(self):
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def action_com_active(self):
        self.write({'state': 'active'})
        return True


class CompanyContact(models.Model):
    _name = "company.contact"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        index=True,
        ondelete='cascade',
    )

    owner_name = fields.Char(
        string="Owner Name",
        required=False,
    )

    contact_name = fields.Char(
        string="Contact_name",
        required=False,
    )

    telephone = fields.Char(
        string="Telephone",
        required=False,
    )

    mobile = fields.Char(
        string="Mobile",
        required=False,
    )

    email = fields.Char(
        string="Email",
        required=False,
    )
