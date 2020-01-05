# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class MultiCoupon(models.Model):
    _name = "multi.coupon"
    _rec_name = 'barcode'

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="",
        required=False,
        index=True,
        ondelete="cascade",
    )

    product_id_int = fields.Integer(
        string="Product ID",
        required=False,
        related='product_id.id',
    )

    pos_order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Pos Order",
        required=False,
        index=True,
        ondelete="cascade",
        readonly=True,
        relaled='pos_order_line_ids.id',
    )

    pos_order_line_ids = fields.One2many(
        comodel_name="pos.order.line",
        inverse_name="multi_coupon_id",
        string="Pos Order Lines",
        required=False,
    )

    barcode = fields.Char(
        string="Barcode",
        required=False,
        digit=15,
    )

    is_received = fields.Boolean(
        string="Received",
        default=False,
    )

    is_reserved = fields.Boolean(
        string="Reserved",
        default=False,
    )

    is_used = fields.Boolean(
        string="Used",
        default=False,
    )

    is_canceled = fields.Boolean(
        string="Canceled",
        default=False,
    )

    @api.multi
    def set_unreserved(self):
        self.write({
            'is_reserved': False,
        })

    def unreserved_process(self):
        coupon_unreserved_time = self.env['ir.config_parameter'].sudo().get_param("multi_coupon_unreserved_time")
        if coupon_unreserved_time:
            self._cr.execute("""
                select id from multi_coupon
                where
                    is_used is false
                    and is_canceled is false
                    and is_reserved = true
                    and write_date::timestamp + INTERVAL '%s MINUTE' <= timezone('utc', now());
            """, (int(coupon_unreserved_time), ))

            multi_coupon_ids = self._cr.dictfetchall()
            if len(multi_coupon_ids):
                self.env['multi.coupon'].browse([multi_coupon_id['id'] for multi_coupon_id in multi_coupon_ids]).set_unreserved()
