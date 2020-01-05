# -*- coding: utf-8 -*-

from odoo import models, api, _,fields
from odoo.exceptions import except_orm


class AccountBillingNote(models.Model):
    _inherit = 'account.billing.note'

    address_billing_note = fields.Text(
        string="",
        required=False,
    )

    contact_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        required=False,
        domain=[('active', '=', True)],
    )

    partner_id = fields.Many2one(
        string="Customer",
    )

    is_hide_contact = fields.Boolean(
        string="",
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.is_hide_contact = False
            self.address_billing_note = self.partner_id.get_new_addr()
            self.contact_id = None
        elif not self.partner_id:
            self.is_hide_contact = True
            self.contact_id = None
            self.address_billing_note = None

    @api.onchange('contact_id')
    def _onchange_contact_id(self):
        if self.contact_id:
            self.address_billing_note = self.contact_id.get_new_addr()
        else:
            self.address_billing_note = self.partner_id.get_new_addr()

    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise except_orm(_('Error!'), _(u"Can't delete Billing Note that state is not Draft."))

        return super(AccountBillingNote, self).unlink()
