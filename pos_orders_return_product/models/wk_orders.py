# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    approver_id = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        required=False,
        readonly=True,
    )

    approve_datetime = fields.Datetime(
        string="Approve Time",
        required=False,
        readonly=True,
    )

    # @api.model
    # def create_from_ui(self, orders):
    #     order_ids = super(PosOrder, self).create_from_ui(orders)
    #     order_objs = self.env['pos.order'].browse(order_ids)
    #     result = {}
    #     order_list = []
    #     order_line_list = []
    #     statement_list = []
    #     for order_obj in order_objs:
    #         vals = {}
    #         vals['lines'] = []
    #         if hasattr(order_objs[0], 'return_status'):
    #             if not (order_obj.is_void_order or order_obj.is_return_order):
    #                 vals['return_status'] = order_obj.return_status
    #                 vals['existing'] = False
    #                 vals['id'] = order_obj.id
    #             else:
    #                 order_obj.return_order_id.return_status = order_obj.return_status
    #                 vals['existing'] = True
    #                 vals['id'] = order_obj.id
    #                 vals['original_order_id'] = order_obj.return_order_id.id
    #                 vals['return_status'] = order_obj.return_order_id.return_status
    #                 for line in order_obj.lines:
    #                     line_vals = {}
    #                     if line.original_line_id:
    #                         line_vals['id'] = line.original_line_id.id
    #                         line_vals['line_qty_returned'] = line.original_line_id.line_qty_returned
    #                         line_vals['existing'] = True
    #                         order_line_list.append(line_vals)
    #         vals['statement_ids'] = order_obj.statement_ids.ids
    #         vals['name'] = order_obj.name
    #         vals['inv_no'] = order_obj.inv_no
    #         vals['the_one_card_no'] = order_obj.the_one_card_no
    #         vals['amount_total'] = order_obj.amount_total
    #         vals['pos_reference'] = order_obj.pos_reference
    #         vals['date_order'] = order_obj.date_order
    #         vals['branch_id'] = [order_obj.branch_id.id, order_obj.branch_id.name]
    #         if order_obj.invoice_id:
    #             vals['invoice_id'] = order_obj.invoice_id.id
    #         else:
    #             vals['invoice_id'] = False
    #         if order_obj.partner_id:
    #             vals['partner_id'] = [order_obj.partner_id.id, order_obj.partner_id.name]
    #         else:
    #             vals['partner_id'] = False
    #         if (not hasattr(order_objs[0], 'return_status') or (
    #                 hasattr(order_objs[0], 'return_status') and not (order_obj.is_void_order or order_obj.is_return_order))):
    #             vals['id'] = order_obj.id
    #             for line in order_obj.lines:
    #                 vals['lines'].append(line.id)
    #                 line_vals = {}
    #                 # LINE DATAA
    #                 line_vals['create_date'] = line.create_date
    #                 line_vals['discount'] = line.discount
    #                 line_vals['display_name'] = line.display_name
    #                 line_vals['id'] = line.id
    #                 line_vals['order_id'] = [line.order_id.id, line.order_id.name]
    #                 line_vals['price_subtotal'] = line.price_subtotal
    #                 line_vals['price_subtotal_incl'] = line.price_subtotal_incl
    #                 line_vals['price_unit'] = line.price_unit
    #                 line_vals['product_id'] = [line.product_id.id, line.product_id.name]
    #                 line_vals['qty'] = line.qty
    #                 line_vals['write_date'] = line.write_date
    #                 line_vals['promotion_condition_id'] = line.promotion_condition_id.id
    #                 line_vals['promotion_name'] = line.promotion_name
    #                 line_vals['free_product_id'] = line.free_product_id.id
    #                 line_vals['promotion'] = line.promotion
    #                 line_vals['promotion_id'] = line.promotion_id.id
    #                 line_vals['prorate_amount'] = line.prorate_amount
    #                 line_vals['prorate_amount_exclude'] = line.prorate_amount_exclude
    #                 if hasattr(line, 'line_qty_returned'):
    #                     line_vals['line_qty_returned'] = line.line_qty_returned
    #                 # LINE DATAA
    #                 order_line_list.append(line_vals)
    #             for statement_id in order_obj.statement_ids:
    #                 statement_vals = {}
    #                 # STATEMENT DATAA
    #                 statement_vals['amount'] = statement_id.amount
    #                 statement_vals['id'] = statement_id.id
    #                 statement_vals['credit_card_no'] = statement_id.credit_card_no
    #                 statement_vals['credit_card_no_encrypt'] = statement_id.credit_card_no_encrypt
    #                 statement_vals['approve_code'] = statement_id.approve_code
    #                 if statement_id.journal_id:
    #                     currency = statement_id.journal_id.currency_id or statement_id.journal_id.company_id.currency_id
    #                     statement_vals['journal_id'] = [statement_id.journal_id.id,
    #                                                     statement_id.journal_id.name + " (" + currency.name + ")"]
    #                 else:
    #                     statement_vals['journal_id'] = False
    #                 statement_list.append(statement_vals)
    #         order_list.append(vals)
    #     result['orders'] = order_list
    #     result['orderlines'] = order_line_list
    #     result['statements'] = statement_list
    #     result['order_ids'] = order_ids
    #     return result

    @api.multi
    def cancel_multi_coupon(self):
        multi_coupon = self.env['multi.coupon']

        for record in self:
            if record.is_void_order or record.is_return_order:
                for line in record.multi_coupon_ids:
                    multi_coupon_obj = multi_coupon.browse(line.multi_coupon_id.id)
                    multi_coupon_obj.write({
                        'is_canceled': True,
                    })

    @api.model
    def create_from_ui(self, orders):
        order_ids = super(PosOrder, self).create_from_ui(orders)

        order_objs = self.env['pos.order'].browse(order_ids)

        for order_obj in order_objs:
            if order_obj.is_void_order or order_obj.is_return_order:
                order_obj.cancel_multi_coupon()

        return order_ids


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _domain_pos_manager(self):
        group = self.env.ref('point_of_sale.group_pos_manager')
        users = []
        for user in group.users:
            users.append(user.id)
        return [('id', 'in', users)]

    order_loading_options = fields.Selection(
        [("current_session", "Load Orders Of Current Session"),
         ("all_orders", "Load All Past Orders"),
         ("n_days", "Load Orders Of Last 'n' Days")],
        default='current_session',
        string="Loading Options"
    )

    number_of_days = fields.Integer(
        string='Number Of Past Days',
        default=1,
    )

    return_order_loading_options = fields.Selection(
        [("current_session", "Load Orders Of Current Session"),
         ("all_orders", "Load All Past Orders"),
         ("n_days", "Load Orders Of Last 'n' Days")],
        default='n_days',
        string="Loading Options"
    )
    
    return_number_of_days = fields.Integer(
        string='Number Of Past Days',
        default=30,
    )

    @api.constrains('number_of_days')
    def number_of_days_validation(self):
        if self.order_loading_options == 'n_days':
            if not self.number_of_days or self.number_of_days < 0:
                raise ValidationError("Please provide a valid value for the field 'Number Of Past Days'!!!")
