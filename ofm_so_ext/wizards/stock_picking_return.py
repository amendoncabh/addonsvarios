# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

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
    @api.depends('location_id')
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
        for rec in self:
            return_approver_id = self._context.get('return_approver_id', False)
            return_approve_datetime = self._context.get('return_approve_datetime', False)
            update_dict = {}
            if return_approver_id and return_approve_datetime:
                update_dict = {
                    'return_approver_id': return_approver_id,
                    'return_approve_datetime': return_approve_datetime,
                }
            elif self.manager_id and self.pos_security_pin:
                rec.check_pin_match_manager()
                update_dict = {
                    'return_approver_id': self.manager_id.id,
                    'return_approve_datetime': fields.Datetime.now(),
                }

            res = super(ReturnPicking, rec).create_returns()

            return_picking_id = res.get('res_id', False)
            return_picking_id = self.env['stock.picking'].browse(return_picking_id) if return_picking_id else False
            if return_picking_id and len(update_dict):
                return_picking_id.write(update_dict)
            return res

    def create_return_picking_from_dict(self, picking_origin_id, move_lines_dict):
        ctx = dict(self._context or {})

        if not picking_origin_id or not move_lines_dict:
            return False

        return_reason_context = self._context.get('return_reason_id', False)
        if return_reason_context:
            domain = [('id', '=', return_reason_context)]
        else:
            return_reason_value = self.env['ir.config_parameter'].search([
                ('key', '=', 'so_auto_return_reason'),
            ]).value
            domain = [
                ('name', '=', return_reason_value),
                ('model', '=', 'purchase.order'),
            ]

        return_reason_id = self.env['return.reason'].search(domain)

        # self.env['stock.return.picking'] is equal to self
        stock_return_picking_id = self.with_context(ctx).create({
            'return_reason_id': return_reason_id.id,
            'location_id': picking_origin_id.location_id.id,
        })

        return_picking_action = stock_return_picking_id.with_context(ctx).create_returns()
        return_picking_id = return_picking_action.get('res_id', False)
        return_picking_id = self.env['stock.picking'].browse(return_picking_id) if return_picking_id else False

        move_product_dict = {}

        for move_line in move_lines_dict:
            move_line_dict = move_line
            if isinstance(move_line, list):
                move_line_dict = move_line[2]

            product_id = move_line_dict.get('product_id', False)
            product_qty = move_line_dict.get('product_qty', 0)

            move_product_dict.update({
                product_id: product_qty
            })

        for line_id in return_picking_id.move_lines:
            product_qty = move_product_dict.get(line_id.product_id.id, False)
            if product_qty:
                line_id.product_uom_qty = product_qty
            else:
                line_id.unlink()

        return return_picking_id
