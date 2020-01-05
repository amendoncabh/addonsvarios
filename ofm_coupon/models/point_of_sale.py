# -*- coding: utf-8 -*-
from odoo import api, models, fields, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    lines = fields.One2many(
        domain=[('line_coupon', '!=', 'reward_coupon')],
    )

    multi_coupon_ids = fields.One2many(
        comodel_name='pos.order.line',
        inverse_name='order_id',
        string="Coupon",
        required=False,
        index=True,
        readonly=True,
        domain=[('line_coupon', '=', 'reward_coupon')],
    )

    @api.multi
    def used_multi_coupon(self):
        multi_coupon = self.env['multi.coupon']

        for record in self:
            for line in record.lines:
                if line.multi_coupon_id and line.line_coupon != 'reward_coupon':
                    multi_coupon_obj = multi_coupon.browse(line.multi_coupon_id.id)
                    multi_coupon_obj.write({
                        'is_used': True,
                    })

    @api.model
    def create_from_ui(self, orders):
        order_ids = super(PosOrder, self).create_from_ui(orders)

        order_obj = self.env['pos.order'].browse(order_ids)
        order_obj.filtered(lambda order: not (order.is_void_order or order.is_return_order)).used_multi_coupon()

        return order_ids


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    line_coupon = fields.Selection(
        string="Line Coupon",
        selection=[
           ('no', 'No'),
           ('reward_coupon', 'Reward Coupon'),
        ],
        default='no',
        required=True,
    )

    multi_coupon_id = fields.Many2one(
        comodel_name="multi.coupon",
        string="Multi Coupon",
        required=False,
        readonly=True,
    )

    multi_coupon_barcode = fields.Char(
        string="Coupon Barcode",
        required=False,
        related='multi_coupon_id.barcode',
        readonly=True,
    )

    @api.model
    def _order_line_fields(self, line):
        fields_return = super(PosOrderLine, self)._order_line_fields(line)

        # default no
        fields_return[2].update({
            'line_coupon': line[2].get('line_coupon', 'no'),
            'multi_coupon_id': line[2].get('multi_coupon_id', False)
        })

        return fields_return
