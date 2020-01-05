# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

class ReturnPicking(models.TransientModel):
    _name = 'deposit.stock.return.picking'
    _description = 'Deposit Return Picking'


    return_reason_id = fields.Many2one(
        comodel_name="return.reason",
        string="Reason",
    )

    is_hide_pin_approve = fields.Boolean(
        string="Hide Pin Approve",
        compute="compute_hide_pin_approve",
    )

    pos_security_pin = fields.Char(
        string='PIN',
        size=32,
        help='A Security PIN used to protect sensible functionality in the Point of Sale'
    )

    manager_id = fields.Many2one(
        comodel_name='res.users',
        string='Manager',
    )

    @api.constrains('pos_security_pin')
    def _check_pin(self):
        if self.pos_security_pin and not self.pos_security_pin.isdigit():
            raise UserError(_("Security PIN can only contain digits"))

    def check_pin_match_manager(self):
        if self.manager_id.pos_security_pin != self.pos_security_pin:
            raise UserError(_("Security PIN incorrect!"))

    @api.multi
    def compute_hide_pin_approve(self):
        for rec in self:
            picking_id = rec.env['stock.picking'].browse(rec._context.get('active_id', 0))

            if picking_id:
                if picking_id.usage_src_location == 'internal' and picking_id.usage_dest_location == 'customer':
                    rec.is_hide_pin_approve = False
                else:
                    rec.is_hide_pin_approve = True
            else:
                rec.is_hide_pin_approve = True


    @api.multi
    def create_returns(self):
        journal_id = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)

        ctx = dict(self.env.context)
        ctx.update({
            'return_reason_id': self.return_reason_id.id,
            'default_journal_id': journal_id.id,
            'is_not_invoice_open_auto': False
        })

        active_id = self._context.get('active_id', False)
        if active_id:
            account_deposit = self.env['account.deposit'].search([('id', '=', active_id)])
            stock_return_picking_id = account_deposit.with_context(ctx).deposit_return_action()

            return stock_return_picking_id
