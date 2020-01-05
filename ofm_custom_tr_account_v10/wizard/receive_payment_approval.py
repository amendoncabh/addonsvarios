# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ReturnPicking(models.TransientModel):
    _name = 'receive.payment.approval'

    def default_return_reason_id(self):
        active_id = self._context.get('active_id', False)

        if active_id:
            account_payment_id = self.env['account.payment'].browse(active_id)
            line_id = account_payment_id.invoice_line.filtered(lambda x: x.paid_amount != 0)
            if line_id:
                return line_id.invoice_id.return_reason_id.id
            else:
                return False
        else:
            return False

    return_reason_id = fields.Many2one(
        comodel_name="return.reason",
        string="Reason",
        required=True,
        default=default_return_reason_id
    )

    pos_security_pin = fields.Char(
        string='PIN',
        size=32,
        required=True,
        help='A Security PIN used to protect sensible functionality in the Point of Sale'
    )

    manager_id = fields.Many2one(
        comodel_name='res.users',
        string='Manager',
        required=True,
    )

    @api.constrains('pos_security_pin')
    def _check_pin(self):
        if self.pos_security_pin and not self.pos_security_pin.isdigit():
            raise UserError(_("Security PIN can only contain digits"))

    def check_pin_match_manager(self):
        if self.manager_id.pos_security_pin != self.pos_security_pin:
            raise UserError(_("Security PIN incorrect!"))

    @api.multi
    def action_post(self):
        for rec in self:
            active_id = rec.env.context.get('active_id', False)
            if active_id:
                if self.manager_id and self.pos_security_pin:
                    self.check_pin_match_manager()
                payment_id = self.env['account.payment'].browse(active_id)
                branch_id = payment_id.branch_id.id
                payment_id.with_context(branch_id=branch_id).post()
            else:
                return True
