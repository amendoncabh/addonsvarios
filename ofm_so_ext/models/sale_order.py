# -*- coding: utf-8 -*-

import logging
import time
import json
import pickle
import ast
import copy
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import partial

import odoo.addons.decimal_precision as dp

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import except_orm
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


def check_int_value(val):
    try:
        int(val)
        return True
    except ValueError:
        return False


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _default_branch(self):
        return self.env.user.branch_id

    def get_warehouse_id(self, branch_id):
        warehouse_id = self.env['pos.branch'].browse(branch_id).warehouse_id.id

        return warehouse_id

    @api.model
    def _default_warehouse_id(self):
        # super(SaleOrder, self)._default_warehouse_id()
        branch_id = self.env.user.branch_id.id
        warehouse_id = self.get_warehouse_id(branch_id)
        return warehouse_id

    def _get_default_type_sale_ofm(self):
        type_sale_ofm = self._context.get('type_sale_ofm', False)
        if type_sale_ofm:
            return type_sale_ofm
        else:
            return False

    state = fields.Selection(
        selection=[
            ('draft', 'Quotation'),
            ('sent', 'SO Draft'),
            ('sale', 'Sales Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        readonly=True,
        copy=False,
        index=True,
        track_visibility='onchange',
        default='draft'
    )

    partner_id = fields.Many2one(
        domain=[('parent_id', '=', False)],
    )

    type_sale_ofm = fields.Boolean(
        string='Type Sales OFM',
        default=_get_default_type_sale_ofm,
        readonly=True
    )

    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
        required=True,
        readonly=True,
        default=_default_warehouse_id
    )

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        required=True,
        default=_default_branch,
    )

    quotation_no = fields.Char(
        string='Quotation No.',
        readonly=True
    )

    customer_type = fields.Selection(
        string="Customer Type",
        related='partner_id.customer_payment_type',
    )

    is_delivery_fee_by_item = fields.Boolean(
        string='Delivery Fee By Item',
        default=False,
        readonly=True,
    )

    purchase_order_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='sale_order_id',
        string='Purchase Order',
        readonly=True,
    )

    amount_discount_by_order = fields.Monetary(
        string='Discount By See',
        track_visibility='always',
    )

    amount_discount_by_sor = fields.Monetary(
        string='Discount By Sor',
        readonly=True,
        store=True,
        compute='compute_amount_discount_by_sor',
    )

    amount_discount_by_sor_show = fields.Monetary(
        string='Discount By Sor',
        readonly=True,
        compute='compute_amount_discount_by_sor_show',
    )

    amount_delivery_fee_special = fields.Monetary(
        string='Amount Delivery Fee Special',
        track_visibility='always',
    )

    amount_delivery_fee_by_order = fields.Monetary(
        string='Amount Delivery Fee By Order',
        track_visibility='always',
    )

    amount_delivery_fee_by_order_origin = fields.Monetary(
        string='Amount Delivery Fee By Order Origin',
        track_visibility='always',
    )

    amount_delivery_fee = fields.Monetary(
        string='Amount Delivery Fee',
        track_visibility='always',
        compute='compute_delivery_fee',
    )

    amount_discount_by_order_show = fields.Monetary(
        string='Discount By See',
        readonly=True,
        compute='compute_amount_discount_by_order_show',
    )

    amount_delivery_fee_special_show = fields.Monetary(
        string='Amount Delivery Fee Special',
        related='amount_delivery_fee_special',
        readonly=True,
    )

    amount_delivery_fee_by_order_show = fields.Monetary(
        string='Amount Delivery Fee By Order',
        related='amount_delivery_fee_by_order',
        readonly=True,
    )

    customer_max_aging = fields.Float(
        string="Credit Limit",
        readonly=True,
        related='partner_id.max_aging',
    )

    customer_aging_balance = fields.Float(
        string="Credit Balance",
        readonly=True,
        related='partner_id.aging_balance',
    )

    customer_trust = fields.Selection(
        string='Degree of trust',
        readonly=True,
        related='partner_id.trust',
    )

    contact_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        required=True,
    )

    so_date_order = fields.Datetime(
        string="SO Date",
        required=False,
        readonly=True,
    )

    date_order = fields.Datetime(
        string="QU Date",
    )

    before_discount = fields.Monetary(
        string="Before Discount",
        readonly=True,
    )

    before_discount_show = fields.Monetary(
        string='Before Discount',
        related='before_discount',
        readonly=True,
    )

    pos_sale_reference = fields.Char(
        string='Pos Sale Order Reference',
        readonly=True
    )

    is_hide_action_cancel_so = fields.Boolean(
        string='Hide Action Cancel SO',
        compute='compute_is_hide_action_cancel_so',
        default=True,
    )

    purchase_count = fields.Integer(
        string='Purchase',
        compute='compute_purchase_count',
    )

    order_line_show = fields.One2many(
        comodel_name='sale.order.line',
        string='Order Lines',
        compute='compute_order_line',
    )

    invoice_validated_count = fields.Integer(
        string='# of Invoices',
        compute='_get_invoiced_validated',
        readonly=True
    )

    delivery_method = fields.Selection(
        selection=[
            ('instore', 'In Store'),
            ('dropship', 'Dropship'),
        ],
        compute='compute_delivery_method',
    )

    discount_approval_manager = fields.Many2one(
        'res.users', 
        string="Discount Approving Manager")

    discount_approval_time = fields.Datetime(
        string = "Discount Approval Time"
    )

    the_one_card_no = fields.Char(
        string="The One Card No.",
        readonly=True,
    )
    # Check member language pref. then select name to display
    member_name = fields.Char(
        string='Member Name',
        readonly=True,
    )
    phone_number = fields.Char(
        string='Member Phone Number',
        readonly=True,
    )
    # national_id = field.Char(
    #     string='National ID',
    #     readonly=True,
    # )
    points_expiry_this_year = fields.Integer(
        string='Point Expiry This Year',
        readonly=True,
    )
    points_balance = fields.Integer(
        string='Points Balance',
        readonly=True,
    )
    membercard = fields.Text(
        string='Membercard dict',
        readonly=True,
    )
    t1c_set = fields.Boolean(
        string='t1c set flag',
        readonly=True,
    )
    pos_offline = fields.Boolean(
        string='POS online flag',
        readonly=True,
    )

    return_status = fields.Selection([
            ('-', 'Not Returned'),
            ('Fully-Returned', 'Fully-Returned'),
            ('Partially-Returned', 'Partially-Returned'),
            ('Non-Returnable', 'Non-Returnable')]
        , default='-'
        , copy=False,
        string='Status'
    )

    session_id = fields.Many2one(
        comodel_name="sale.session",
        string="Sale Session ID",
        required=False,
    )

    @api.depends('state', 'order_line.invoice_status')
    def _get_invoiced_validated(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also hte default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.

        The invoice_ids are obtained thanks to the invoice lines of the SO lines, and we also search
        for possible refunds created directly from existing invoices. This is necessary since such a
        refund is not directly linked to the SO.
        """
        for order in self:
            invoice_ids = order.order_line.mapped('invoice_lines').mapped('invoice_id').filtered(
                lambda r: all([
                    r.type in ['out_invoice', 'out_refund'],
                    r.state not in ['draft', 'cancel']
                ])
            )
            refunds = invoice_ids.search(
                [
                    ('origin', 'like', order.name),
                    ('company_id', '=', order.company_id.id)
                ]
            ).filtered(
                lambda r: all([
                    r.type in ['out_invoice', 'out_refund'],
                    r.state not in ['draft', 'cancel']
                ])
            )
            invoice_ids |= refunds.filtered(
                lambda r: order.name in [origin.strip() for origin in r.origin.split(',')]
            )
            # Search for refunds as well
            refund_ids = self.env['account.invoice'].browse()
            if invoice_ids:
                for inv in invoice_ids:
                    refund_ids += refund_ids.search(
                        [
                            ('type', '=', 'out_refund'),
                            ('origin', '=', inv.number),
                            ('origin', '!=', False),
                            ('journal_id', '=', inv.journal_id.id),
                            ('state', 'not in', ['draft', 'cancel'])
                        ]
                    )

            order.update({
                'invoice_validated_count': len(set(invoice_ids.ids + refund_ids.ids)),
            })

    @api.multi
    @api.depends('type_sale_ofm')
    def compute_delivery_method(self):
        for rec in self:
            if rec.type_sale_ofm:
                rec.delivery_method = 'dropship'
            else:
                rec.delivery_method = 'instore'

    @api.multi
    @api.depends('amount_total', 'before_discount', 'amount_discount_by_order')
    def compute_amount_discount_by_sor(self):
        for rec in self:
            extra_fee = 0
            if rec.amount_delivery_fee_special:
                extra_fee += abs(rec.amount_delivery_fee_special)
            if rec.amount_delivery_fee_by_order:
                extra_fee += abs(rec.amount_delivery_fee_by_order)
            rec.amount_discount_by_sor = abs((rec.before_discount + extra_fee - rec.amount_total) - rec.amount_discount_by_order)

    @api.multi
    def compute_amount_discount_by_sor_show(self):
        for record in self:
            record.amount_discount_by_sor_show = (-1) * abs(record.amount_discount_by_sor)

    @api.multi
    def compute_amount_discount_by_order_show(self):
        for record in self:
            record.amount_discount_by_order_show = (-1) * abs(record.amount_discount_by_order)

    @api.multi
    @api.depends('amount_delivery_fee_special', 'amount_delivery_fee_by_order')
    def compute_delivery_fee(self):
        for rec in self:
            amount_delivery_fee_special = rec.amount_delivery_fee_special if rec.amount_delivery_fee_special else 0
            amount_delivery_fee_by_order = rec.amount_delivery_fee_by_order if rec.amount_delivery_fee_by_order else 0

            rec.amount_delivery_fee = amount_delivery_fee_special + amount_delivery_fee_by_order

    @api.multi
    @api.depends('order_line')
    def compute_order_line(self):
        for rec in self:
            rec.order_line_show = rec.order_line.filtered(
                lambda line_rec: not line_rec.is_line_discount_delivery_promotion
                or line_rec.promotion
            )

    @api.multi
    @api.depends('purchase_order_ids')
    def compute_purchase_count(self):
        for rec in self:
            if rec.purchase_order_ids:
                rec.purchase_count = len(rec.purchase_order_ids.ids)
            else:
                rec.purchase_count = 0

    @api.multi
    @api.depends('state')
    def compute_is_hide_action_cancel_so(self):
        for rec in self:
            picking_done_ids = rec.picking_ids.filtered(
                lambda picking_rec: picking_rec.state == 'done'
            )

            if not picking_done_ids:
                for purchase_id in rec.purchase_order_ids:
                    picking_done_ids = purchase_id.picking_ids.filtered(
                        lambda picking_rec: picking_rec.state == 'done'
                    )

                    if picking_done_ids:
                        break

            if any([
                picking_done_ids,
                rec.state != 'sale',
            ]):
                rec.is_hide_action_cancel_so = True
            else:
                rec.is_hide_action_cancel_so = False

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()

        self.partner_invoice_id = False
        self.partner_shipping_id = False
        self.contact_id = False

        ctx = dict(self._context)
        ctx.update({
            'is_customer': False
        })

        parnter_obj = self.env['res.partner']

        self.partner_invoice_id = parnter_obj.with_context(ctx).search([
            ('type', '=', 'invoice'),
            ('parent_id', '=', self.partner_id.id),
        ], limit=1)
        self.partner_shipping_id = parnter_obj.with_context(ctx).search([
            ('type', '=', 'delivery'),
            ('parent_id', '=', self.partner_id.id),
        ], limit=1)
        self.contact_id = parnter_obj.with_context(ctx).search([
            ('type', '=', 'contact'),
            ('parent_id', '=', self.partner_id.id),
        ], limit=1)

    def generate_so_no(self, branch_id, date_order):
        ctx = dict(self._context)

        prefix = 'SO-'
        ctx.update({'res_model': self._name})

        prefix = prefix + branch_id.branch_code + '%(y)s%(month)s'
        so_no = branch_id.with_context(ctx).next_sequence(date_order, prefix, 5) or '/'

        return so_no

    def generate_qu_no(self, branch_id, date_order):
        ctx = dict(self._context)

        prefix = 'QU-'
        ctx.update({'res_model': 'quotation.order'})

        prefix = prefix + branch_id.branch_code + '%(y)s%(month)s'
        qu_no = branch_id.with_context(ctx).next_sequence(date_order, prefix, 5) or '/'

        return qu_no

    @api.multi
    def shipping_fee_process(self):
        so_line_obj = self.env['sale.order.line']
        so_delivery_fee_special = self.env['ir.config_parameter'].get_param('so_delivery_fee_special')
        for record in self:
            if record.type_sale_ofm:
                # calculate new shipping fee
                shipping_fee_line = False
                shipping_special_line = False
                amount_total = 0
                total_amount_shipping_special = 0
                for line in record.order_line:
                    if line.is_type_delivery_by_order:
                        shipping_fee_line = line
                    elif line.is_type_delivery_special:
                        shipping_special_line = line
                    else:
                        amount_total += (line.price_unit * line.product_uom_qty)
                        if line.product_id.is_delivery_fee_ofm:
                            total_amount_shipping_special += (line.product_id.delivery_fee_ofm * line.product_uom_qty)
                if amount_total < 499:
                    record.amount_delivery_fee_by_order = so_delivery_fee_special
                    if shipping_fee_line:
                        shipping_fee_line.price_unit = so_delivery_fee_special
                    else:
                        account_tax = self.env['account.tax']
                        user_id = record.env.user
                        vat_product = self.env['ir.config_parameter'].get_param(
                            'vat_product'
                        )
                        vat_out = account_tax.search([
                            ('company_id', '=', user_id.company_id.id),
                            ('type_tax_use', '=', 'sale'),
                            ('amount', '=', vat_product)
                        ]).ids
                        sol = self.set_order_line_fee_delivery(
                            vat_out,
                            so_delivery_fee_special,
                            [],
                            self.env.ref('ofm_so_ext.product_delivery_fee'),
                        )
                        sol[0][2].update({
                            'order_id': record.id,
                        })
                        record.order_line += so_line_obj.with_context({
                            'partner_id': record.partner_id.id,
                            'pricelist_branch_id': record.branch_id.id,
                        }).create(sol[0][2])
                # >= 499 no shipping fee
                else:
                    record.amount_delivery_fee_by_order = 0
                    if shipping_fee_line:
                        shipping_fee_line.unlink()

                if record.is_delivery_fee_by_item and total_amount_shipping_special > 0:
                    record.amount_delivery_fee_special = total_amount_shipping_special
                    if shipping_special_line:
                        shipping_special_line.price_unit = total_amount_shipping_special
                    else:
                        account_tax = self.env['account.tax']
                        user_id = record.env.user
                        vat_product = self.env['ir.config_parameter'].get_param(
                            'vat_product'
                        )
                        vat_out = account_tax.search([
                            ('company_id', '=', user_id.company_id.id),
                            ('type_tax_use', '=', 'sale'),
                            ('amount', '=', vat_product)
                        ]).ids
                        sol = self.with_context({
                            'is_type_delivery_special': True,
                        }).set_order_line_fee_delivery(
                            vat_out,
                            total_amount_shipping_special,
                            [],
                            self.env.ref('ofm_so_ext.product_delivery_fee_special')
                        )
                        sol[0][2].update({
                            'order_id': record.id,
                        })
                        record.order_line += so_line_obj.with_context({
                            'partner_id': record.partner_id.id,
                            'pricelist_branch_id': record.branch_id.id,
                        }).create(sol[0][2])
                else:
                    record.amount_delivery_fee_special = 0
                    if shipping_special_line:
                        shipping_special_line.unlink()

                self.env.cr.commit()

    def search_read_so_from_ui(self):
        SaleOrderLineModel = self.env['sale.order.line']
        PartnerIdModel = self.env['res.partner']
        ProrateModel = self.env['pos.promotion.prorate']

        id = self._context.get('object_id', self.id)

        if not id:
            raise except_orm(_('Error!'), _(u"No Sale Order ID"))

        sale_order_id = self.search_read(
            [('id', '=', id)],
            []
        )
        if sale_order_id:
            sale_order_id = sale_order_id[0]
            order_line = sale_order_id.get('order_line', False)
            if order_line and len(order_line):
                sale_order_id['order_line'] = SaleOrderLineModel.search_read([
                    ('id', 'in', order_line)
                ], [])
                for line in sale_order_id['order_line']:
                    line_obj = SaleOrderLineModel.browse([line.get('id')])
                    is_coupon = line_obj.product_id.is_coupon
                    line['is_coupon'] = is_coupon
                    if 'prorate_ids' in line and len(line['prorate_ids']):
                        line['prorate_ids'] = ProrateModel.search_read([
                            ('id', 'in', line['prorate_ids'])
                        ], [])

            partner_id = sale_order_id.get('partner_id', False)
            if partner_id and len(partner_id):
                sale_order_id['partner_id'] = PartnerIdModel.search_read([
                    ('id', '=', partner_id[0])
                ], [])

            partner_invoice_id = sale_order_id.get('partner_invoice_id', False)
            if all([
                partner_invoice_id,
                len(partner_invoice_id),
                'id' not in partner_invoice_id
            ]):
                sale_order_id['partner_invoice_id'] = PartnerIdModel.search_read([
                    ('id', '=', partner_invoice_id[0])
                ], [])

            partner_shipping_id = sale_order_id.get('partner_shipping_id', False)

            if all([
                partner_shipping_id,
                len(partner_shipping_id),
                'id' not in partner_shipping_id
            ]):
                sale_order_id['partner_shipping_id'] = PartnerIdModel.search_read([
                    ('id', '=', partner_shipping_id[0])
                ], [])

            contact_id = sale_order_id.get('contact_id', False)
            if all([
                contact_id,
                len(contact_id),
                'id' not in contact_id
            ]):
                sale_order_id['contact_id'] = PartnerIdModel.search_read([
                    ('id', '=', contact_id[0])
                ], [])

            membercard = sale_order_id.get('membercard', False)
            if membercard and len(membercard):
                sale_order_id['membercard'] = ast.literal_eval(membercard)

        else:
            return False

        records = [sale_order_id]
        return records

    @api.model
    def call_api_check_qty_from_ui(self):

        warning = []
        sale_id = self._context.get('order_id', False)

        if sale_id:
            sale_id = self.browse(sale_id)
        else:
            return {
                'status': 'fail',
                'message': 'Api Context fail',
                'length': 0,
                'records': [],
                'warning': warning,
            }

        if sale_id.type_sale_ofm:
            messages = sale_id.call_api_check_qty_from_ofm()
            for line in sale_id.order_line:
                line.onchange_check_qty_with_qty_available()
        else:
            messages = sale_id.check_product_id_availability()

        for message in messages:
            warning.append({
                'header': 'Warning',
                'body': message,
            })

        if sale_id.state == 'draft' and not len(sale_id.order_line.filtered(lambda l: l.is_danger)):
            sale_id.action_quotation_send_so()

        records = sale_id.search_read_so_from_ui()

        if not records:
            return {
                'status': 'fail',
                'message': 'Api Record fail',
                'length': 0,
                'records': [],
                'warning': warning,
            }
        return {
            'length': len(records),
            'records': records,
            'warning': warning,
        }

    def call_api_check_qty_from_ofm(self):
        tr_call_api = self.env['tr.call.api']

        tr_call_api.call_api_check_qty_from_ofm(self)
        self.check_delivery_fee()
        self.shipping_fee_process()
        partner_id = self.env['res.partner'].search(
            [('vat', '=', self.env['ir.config_parameter'].get_param('prs_default_vendor'))])

        return_massage = []

        for line in self.order_line:
            line.check_product_prs_zero(partner_id, self.company_id.id, self.branch_id.id)
            notify = line.with_context({
                'text': self._context.get('order_id', False),
            }).show_notify_product_status_incorrect()
            if notify:
                return_massage.append(notify)
            notify = line.show_notify_product_prs_zero()
            if notify:
                return_massage.append(notify)

        return return_massage

    def check_qty_with_qty_available(self, order_line):
        for line in order_line:
            line.onchange_check_qty_with_qty_available()
            if line.is_danger:
                return True
        return False

    def check_delivery_fee(self):
        if self.is_delivery_fee_by_item:
            for order_id in self.order_line:
                order_id.onchange_get_delivery_fee()
        else:
            for order_id in self.order_line:
                order_id.is_delivery_fee_ofm = False
                order_id.delivery_fee_ofm = 0

    def check_product_id_availability(self):
        product_not_availabililty = []
        for order_line_id in self.order_line:
            if order_line_id.product_id.type == 'product':
                precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                product_qty = order_line_id.product_uom._compute_quantity(
                    order_line_id.product_uom_qty,
                    order_line_id.product_id.uom_id
                )
                if float_compare(
                        order_line_id.product_id.with_context({
                            'location': order_line_id.branch_id.warehouse_id.lot_stock_id.id
                        }).virtual_available,
                        product_qty,
                        precision_digits=precision
                ) == -1:
                    is_available = order_line_id._check_routing()
                    if not is_available:
                        order_line_id.update({
                            'is_danger': True,
                        })
                        msg_product_availiable = """
                                - You plan to sell {0} {1} {2} 
                                but \nThe stock on hand is {3} {4}.
                                """.format(
                            order_line_id.product_id.name,
                            order_line_id.product_uom_qty,
                            order_line_id.product_uom.name,
                            order_line_id.product_id.with_context({
                                'location': order_line_id.branch_id.warehouse_id.lot_stock_id.id
                            }).qty_available,
                            order_line_id.product_id.uom_id.name
                        )

                        product_not_availabililty.append(
                            msg_product_availiable
                        )
                    else:
                        order_line_id.update({
                            'is_danger': False,
                        })
                else:
                    order_line_id.update({
                        'is_danger': False,
                    })
        return product_not_availabililty

    def check_line_availability(self):
        product_not_availabililty = self.check_product_id_availability()

        if not self._context.get('no_warning', False) and len(product_not_availabililty) > 0:
            for product_warning in product_not_availabililty:
                self.env.user.notify_warning(
                    "Warning: Not enough inventory!",
                    product_warning,
                    True
                )

            if self.state == 'sent':
                return True
            else:
                return False
        else:
            return False

    def check_po_sent_to_ofm(self):
        is_send_purchase_success = True

        if self.purchase_order_ids:
            for po_id in self.purchase_order_ids.filtered(
                    lambda x: x.state != 'cancel'
            ):
                if po_id.state != 'sent':
                    is_send_purchase_success = False
                    break

            if not is_send_purchase_success:
                raise except_orm(_('Error!'), _(u"This Sale Order can't change state because Purchase Order can't sent."))

            return is_send_purchase_success
        else:
            raise except_orm(_('Error!'), _(u"This Sale Order can't create Purchase Order."))

    def check_customer_credit_balance(self):
        customer_balance = self.get_customer_credit_balance()

        if self.state == 'sent' \
                and self.partner_id.customer_payment_type == 'credit' \
                and customer_balance < 0:
            raise except_orm(_('Error!'), _(u"This customer have Credit Balance less then 0."))

    def validate_so(self):
        self.check_customer_credit_balance()

        if self.type_sale_ofm:
            self.call_api_check_qty_from_ofm()
            is_danger = self.check_qty_with_qty_available(self.order_line)
        else:
            is_danger = self.check_line_availability()

        return is_danger

    def create_purchase_order(self):
        po_obj = self.env['purchase.order']
        if self.type_sale_ofm:
            ctx = dict(self._context)
            ctx.update({
                'sale_order_id': self,
            })

            if not self.purchase_order_ids:
                po_ids = po_obj.with_context(
                    ctx
                ).create_purchase_order_by_sale_order()
            else:
                purchase_order_ids = self.purchase_order_ids.filtered(
                    lambda x: x.state not in ['cancel']
                )
                if purchase_order_ids:
                    po_ids = self.purchase_order_ids
                else:
                    po_ids = po_obj.with_context(
                        ctx
                    ).create_purchase_order_by_sale_order()
            return po_ids

    def send_purchase_order_to_ofm(self, po_ids):
        for po_id in po_ids:
            if po_id.state == 'draft':
                po_id.check_quantity_order_line()
                po_id.call_api_check_qty_from_ofm()
                po_id = self.env['purchase.order'].browse(po_id.id)
                qty_not_available = po_id.check_qty_with_qty_available(po_id.ofm_purchase_order_line_ids)

                if not qty_not_available:
                    po_id.call_action_send_pr_header()

    @api.multi
    def action_confirm_so(self):
        for rec in self:
            is_danger = self.validate_so()

            ctx = dict(rec._context)
            ctx.update({
                'is_from_so': True,
            })

            if not is_danger:
                if rec.type_sale_ofm:
                    po_ids = rec.create_purchase_order()
                    rec.with_context(ctx).send_purchase_order_to_ofm(po_ids)
                    is_send_purchase_success = rec.check_po_sent_to_ofm()
                else:
                    is_send_purchase_success = True

                if is_send_purchase_success:
                    if 'SO-' not in rec.name.upper():
                        rec.update({
                            'name': rec.generate_so_no(rec.branch_id, rec.date_order),
                        })

                    rec.with_context(ctx).action_confirm()
                    rec.write({
                        'state': 'sale',
                        'so_date_order': datetime.now(),
                    })

                    if rec.type_sale_ofm:
                        action = rec.env.ref('ofm_so_ext.dropship_sales_order_action').read()[0]
                    else:
                        action = rec.env.ref('sale.action_orders').read()[0]

                    action['view_mode'] = 'form'

                    for act_view in action['views']:
                        if 'form' in act_view:
                            action['views'] = [act_view]
                            break

                    action['res_id'] = self.id

                    return action
                else:
                    return False
            else:
                return False

    @api.multi
    def action_cancel_so(self):
        ctx = dict(self._context)
        for rec in self:
            res = rec.write({'state': 'cancel'})

            for invoice in rec.invoice_ids:
                if invoice.state not in ('paid','cancel'):
                    invoice.action_invoice_cancel()

            for picking_id in rec.picking_ids:
                picking_id.action_cancel()

            #if this cancel action did not come from the API then proceed to cancel the PO
            if 'from_api' not in ctx.keys():
                for po_id in rec.purchase_order_ids:
                    po_id.action_cancel_from_sale()

        return res

    @api.multi
    def action_quotation_send_so(self):
        for rec in self:
            if rec.state == 'draft':
                is_danger = self.validate_so()

                if not is_danger:
                    amount_day_expire = rec.env['ir.config_parameter'].search([
                        ('key', '=', 'so_quotation_expire_amount_day')
                    ]).value

                    amount_day_expire = int(amount_day_expire) if amount_day_expire else 7
                    date_order = datetime.strptime(rec.date_order, '%Y-%m-%d %H:%M:%S')
                    validity_date = date_order + timedelta(days=amount_day_expire)

                    res = rec.write({
                        'name': 'Draft',
                        'quotation_no': self.name,
                        'state': 'sent',
                        'validity_date': validity_date,
                    })

                    return res
            else:
                return False

    @api.multi
    def action_view_purchase(self):
        for rec in self:
            purchase_order_ids = rec.purchase_order_ids

            if purchase_order_ids:
                action = rec.env.ref('ofm_purchase_request.ofm_purchase_order_action').read()[0]
                domain = ''.join([
                    "[",
                    "('type_purchase_ofm', '=', 1),",
                    "('id', 'in', {0}),".format(purchase_order_ids.ids),
                    "]",
                ])
                action['domain'] = domain

                return action

            raise except_orm(_('Error!'), _(u"No Purchase Order."))

    def set_order_line_fee_delivery(self, vat_out, fee_amount, line_value, product):

        line_fee_delivery = {
            u'discount': 0.0,
            u'discount_amount': 0.0,
            u'price_unit': fee_amount,
            u'product_id': product.id,
            u'product_uom_qty': 1,
            u'tax_id': [[6, 0, vat_out]],
            u'name': product.name,
            u'is_danger': False,
        }

        if self._context.get('is_type_delivery_special', False):
            line_fee_delivery.update({'is_type_delivery_special': True})
        else:
            line_fee_delivery.update({'is_type_delivery_by_order': True})

        line_value.append([0, 0, line_fee_delivery])

        return line_value

    def set_order_line_discount_see(self, vat_out, discount_see_amount, line_value, session_id):

        line_discount_see = {
            u'discount': 0.0,
            u'discount_amount': 0.0,
            u'price_unit': discount_see_amount * -1,
            u'product_id': session_id.config_id.promotion_discount_product_id.id,
            u'product_uom_qty': 1,
            u'is_type_discount_f_see': True,
            u'tax_id': [[6, 0, vat_out]],
            u'name': 'Discount by Order',
            u'is_danger': False,
        }

        line_value.append([0, 0, line_discount_see])

        return line_value

    def prepare_line_values(self, lines):
        pos_order_ids = []
        lines_promotion = []
        for line in lines:
            lines_promotion.append(line)

        pos_promotion_sum = OrderedDict()

        for line_promotion in lines_promotion:
            key = (
                line_promotion[2].get('promotion_condition_id', 0),
                line_promotion[2]['product_id'],
                line_promotion[2].get('free_product_id', 0)
            )
            if pos_promotion_sum.get(key, False):
                qty = sum([
                    line_promotion[2]['product_uom_qty'],
                    pos_promotion_sum[key]['product_uom_qty']
                ])
                id = pos_promotion_sum[key]['id']
            else:
                qty = line_promotion[2]['product_uom_qty']
                id = line_promotion[2]['id']

            pos_promotion_sum[key] = {
                u'discount': line_promotion[2]['discount'],
                u'is_type_delivery': line_promotion[2].get('is_type_delivery', False),
                u'is_type_delivery_special': line_promotion[2].get('is_type_delivery_special', False),
                u'is_type_delivery_by_order': line_promotion[2].get('is_type_delivery_by_order', False),
                u'discount_amount': line_promotion[2]['discount_amount'],
                u'promotion_condition_id': line_promotion[2].get('promotion_condition_id', False),
                u'promotion_id': line_promotion[2].get('promotion_id', False),
                u'promotion_type': line_promotion[2]['promotion_type'],
                u'reward_type': line_promotion[2]['reward_type'],
                u'prorate_amount': line_promotion[2]['prorate_amount'],
                u'prorate_amount_exclude': line_promotion[2]['prorate_amount_exclude'],
                u'prorate_vat': line_promotion[2]['prorate_vat'],
                u'prorate_amount_2': line_promotion[2].get('prorate_amount_2', 0),
                u'prorate_amount_exclude_2': line_promotion[2].get('prorate_amount_exclude_2', 0),
                u'prorate_vat_2': line_promotion[2].get('prorate_vat_2', 0),
                u'promotion': line_promotion[2]['promotion'],
                u'promotion_name': line_promotion[2]['promotion_name'],
                u'free_product_id': line_promotion[2].get('free_product_id', False),
                u'id': id,
                u'price_unit': line_promotion[2]['price_unit'],
                u'product_id': line_promotion[2]['product_id'],
                u'product_uom_qty': qty,
                u'iface_line_tax_included': line_promotion[2]['iface_line_tax_included'],
                u'force_add': line_promotion[2].get('force_add', False),
                u'delivery_fee_ofm': line_promotion[2].get('delivery_fee_ofm', False),
                u'product_status_odoo': line_promotion[2].get('product_status_odoo', False),
                u'prorate_ids': line_promotion[2].get('prorate_ids', False),
                u'is_type_discount_f_see': line_promotion[2].get('is_type_discount_f_see', False),
            }
            if pos_promotion_sum[key].get('promotion_name', False):
                pos_promotion_sum[key]['name'] = pos_promotion_sum[key]['promotion_name']

            if line_promotion[2].get('tax_ids', None):
                pos_promotion_sum[key].update({
                    u'tax_id': line_promotion[2]['tax_ids'],
                })

        for pos_promotion_one in pos_promotion_sum:
            pos_order_ids.append([0, 0, pos_promotion_sum[pos_promotion_one]])

        return pos_order_ids

    @api.model
    def _order_fields(self, ui_order, pos_session_id):

        process_line = partial(self.env['pos.order.line']._order_line_fields)

        res = {
            'user_id': ui_order['user_id'] or False,
            'session_id': ui_order['pos_session_id'] or False,
            'lines': [process_line(l) for l in ui_order['lines']] if ui_order['lines'] else False,
            'pos_sale_reference': ui_order['name'],
            'partner_id': ui_order['partner_id'] or False,
            'date_order': ui_order['creation_date'],
            'validity_date': ui_order.get('validity_date', False),
            'note': ui_order.get('note', False),
            'partner_invoice_id': ui_order.get('partner_invoice_id', False),
            'contact_id': ui_order.get('contact_id', False),
            'partner_shipping_id': ui_order.get('partner_shipping_id', False),
            'payment_term_id': ui_order.get('payment_term_id', False),
            'branch_id': pos_session_id.config_id.branch_id.id,
            'type_sale_ofm': ui_order.get('type_sale_ofm', False),
            'amount_delivery_fee_by_order': ui_order.get('amount_delivery_fee_by_order', False),
            'amount_delivery_fee_special': ui_order.get('amount_delivery_fee_special', False),
            'amount_discount_by_order': ui_order.get('amount_discount_by_order', False),
            'warehouse_id': self.get_warehouse_id(pos_session_id.config_id.branch_id.id),
            'discount_approval_manager': ui_order.get('discount_approval_manager', False),
            'discount_approval_time': ui_order.get('discount_approval_time', False),
            'before_discount': ui_order.get('before_discount', False),
        }

        if 'expire_this_year' in ui_order['membercard'] and \
                not check_int_value(ui_order['membercard']['expire_this_year']):
            ui_order['membercard']['expire_this_year'] = 0

        if 'balance_points' in ui_order['membercard'] and \
                not check_int_value(ui_order['membercard']['balance_points']):
            ui_order['membercard']['balance_points'] = 0

        if ui_order['t1c_set'] is True and ui_order['pos_offline'] is not True:
            res.update({
                'the_one_card_no': ui_order['membercard']['the_one_card_no'],
                'phone_number': ui_order['membercard']['phone'],
                'points_expiry_this_year': ui_order['membercard']['expire_this_year'],
                'points_balance': ui_order['membercard']['balance_points'],
                'member_name': ui_order['membercard']['member_name'],
                'membercard': ui_order['membercard'],
                't1c_set': ui_order['t1c_set'],
                'pos_offline': ui_order['pos_offline'],
            })
        elif ui_order['t1c_set'] is True and ui_order['pos_offline'] is True:
            res.update({
                'the_one_card_no': ui_order['membercard']['the_one_card_no'],
                'phone_number': ui_order['membercard']['phone'],
                't1c_set': ui_order['t1c_set'],
                'pos_offline': ui_order['pos_offline'],
            })

        return res

    @api.model
    def create_from_ui(self, orders):
        # Keep only new orders
        submitted_references = [o['data']['name'] for o in orders]
        pos_order = self.search([('pos_sale_reference', 'in', submitted_references)])
        existing_orders = pos_order.read(['pos_sale_reference'])
        existing_references = set([o['pos_sale_reference'] for o in existing_orders])
        orders_to_save = [o for o in orders if o['data']['name'] not in existing_references]
        pos_order_existing = [o for o in orders if o['data']['name'] in existing_references]
        order_ids = []
        ctx = dict(self._context)

        start = time.time()

        order = None

        for tmp_order in orders_to_save:
            ctx.update({
                'process_order_type': 'create'
            })
            order = tmp_order['data']

        for sale_order_update in pos_order_existing:
            ctx.update({
                'process_order_type': 'write'
            })
            order = sale_order_update['data']
        pos_order = self.with_context(ctx)._process_order(order)
        order_ids.append(pos_order.id)
        self.env.cr.commit()

        str_time_stamp = 'create_from_ui end', str(time.time() - start)
        _logger.info(str_time_stamp)

        # return dict for display
        order_ids_dict = self.search_read([
            ('id', 'in', order_ids)
        ], ['id', 'name', 'quotation_no', 'partner_id', 'date_order', 'amount_total', 'state'])

        return order_ids_dict

    @api.model
    def _process_order(self, pos_order):
        pos_session = self.env['sale.session'].browse(pos_order['pos_session_id'])
        if not pos_order.get('order_id', False):
            process_order_type = self._context.get('process_order_type', False)
            pos_order['order_id'] = 0
        else:
            process_order_type = 'write'

        if not pos_order.get('partner_id', False):
            pos_order['partner_id'] = 1

        order_dict = self._order_fields(pos_order, pos_session)

        account_tax = self.env['account.tax']
        user_id = self.env['res.users'].browse(order_dict['user_id'])
        vat_product = self.env['ir.config_parameter'].get_param(
            'vat_product'
        )
        vat_out = account_tax.search([
            ('company_id', '=', user_id.company_id.id),
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', vat_product)
        ]).ids

        ctx = dict(self._context)
        ctx.update({
            'partner_id': order_dict['partner_id'],
            'pricelist_branch_id': pos_session.config_id.branch_id.id,
            'no_warning': True,
        })

        order_line = self.prepare_line_values(order_dict['lines'])

        if order_dict.get('amount_delivery_fee_by_order', False):
            order_line = self.set_order_line_fee_delivery(
                vat_out,
                order_dict['amount_delivery_fee_by_order'],
                order_line,
                self.env.ref('ofm_so_ext.product_delivery_fee')
            )

        if order_dict.get('amount_delivery_fee_special', False):
            order_line = self.with_context({
                'is_type_delivery_special': True,
            }).set_order_line_fee_delivery(
                vat_out,
                order_dict['amount_delivery_fee_special'],
                order_line,
                self.env.ref('ofm_so_ext.product_delivery_fee_special')
            )

        order_dict.update({
            'order_line': order_line
        })

        if process_order_type == 'create':
            order = self.with_context(ctx).create(order_dict)
        else:
            params = (
                pos_order.get('order_id', 0),
                order_dict['pos_sale_reference'],
            )
            query_str = """
                    select id
                    from sale_order
                    where
                    id = %s
                    or pos_sale_reference = '%s'
                """ % params
            self.env.cr.execute(query_str)
            result = self.env.cr.dictfetchall()
            order = self.browse(result[0]['id'])
            order.order_line.unlink()
            del order_dict['date_order']
            order.with_context(ctx).write(order_dict)

        #if product is coupon then remove danger for that line
        for line in order.order_line:
            is_danger = line.is_danger
            is_coupon = line.product_id.is_coupon
            if is_danger and is_coupon:
                line.is_danger = False

        if order.state == 'draft':
            if not len(order.order_line.filtered(lambda l: l.is_danger)):
                order.with_context(ctx).action_quotation_send_so()
        if pos_session.sequence_number <= pos_order['sequence_number']:
            pos_session.write({'sequence_number': pos_order['sequence_number'] + 1})
            pos_session.refresh()

        return order

    @api.multi
    def print_form(self):
        for record in self:
            if record.state in ('draft', 'sent'):
                report_name = 'qu.form.jasper'
            elif record.state == 'sale':
                report_name = 'so.form.jasper'

            return record.env['report'].get_action(record, report_name)

    @api.multi
    def print_deposit_form(self):
        return {}

    def modify_cn_from_dict(self, cn_obj, order_lines_by_inv_line_id):
        # update line line_qty_returned
        # also, prepare credit note line on the return order lines
        original_cn_obj = cn_obj.invoice_line_ids
        name_mapping = [(line.product_id, line.name) for line in original_cn_obj if not line.promotion_id]
        if name_mapping:
            special_discount_name = name_mapping[-1][1]
            
        total_prorate_amount = 0
        total_prorate_amount_see = 0
        to_delete_line = self.env['account.invoice.line']
        for cn_line in cn_obj.invoice_line_ids:
            if cn_line.price_unit >= 0 and cn_line.origin_inv_line_id in order_lines_by_inv_line_id:
                item = order_lines_by_inv_line_id[cn_line.origin_inv_line_id]

                so_line = item.get('line')
                qty = item.get('qty')
                if not so_line.line_qty_returned:
                    so_line.line_qty_returned = qty
                else:
                    so_line.line_qty_returned += qty

                # ratio prorate depend on return qty
                ratio = qty / so_line.product_uom_qty
                cn_line.write({
                    'quantity': qty,
                    'prorate_amount': so_line.prorate_amount * ratio,
                    'prorate_amount_exclude': so_line.prorate_amount_exclude * ratio,
                    'prorate_vat': so_line.prorate_vat * ratio,
                })
                if so_line.prorate_amount_2:
                    cn_line.write({
                        'prorate_amount_2': so_line.prorate_amount_2 * ratio,
                        'prorate_amount_exclude_2': so_line.prorate_amount_exclude_2 * ratio,
                        'prorate_vat_2': so_line.prorate_vat_2 * ratio,
                    })
                    total_prorate_amount_see += so_line.prorate_amount_2 * ratio
                total_prorate_amount += so_line.prorate_amount * ratio
            else:
                # not exist on return dict
                to_delete_line += cn_line

        #
        # add discount line if prorate > 0
        if total_prorate_amount > 0:
            discount_product = self.env['pos.config'].search([
                ('branch_id', '=', self.branch_id.id),
                ('promotion_discount_product_id', '!=', False)
                ], limit=1).promotion_discount_product_id
            # print total_prorate_amount, find discount line

            discount_line = cn_obj.invoice_line_ids.filtered(lambda l: l.product_id.id == discount_product.id and l.price_unit < 0)[0]
            if discount_line:
                if total_prorate_amount_see > 0:
                    discount_line_see = discount_line.copy({
                        'quantity': 1,
                        'price_unit': -1 * total_prorate_amount_see,
                        'description': 'ส่วนลดพิเศษที่คืน',
                        'prorate_amount': 0,
                        'prorate_amount_exclude': 0,
                        'prorate_vat': 0,
                        'prorate_amount_2': 0,
                        'prorate_amount_exclude_2': 0,
                        'prorate_vat_2': 0,
                        'is_type_discount_f_see': True,
                    })
                    lines_tax_ids = cn_obj.invoice_line_ids.filtered(lambda l: len(l.invoice_line_tax_ids))
                    if len(lines_tax_ids):
                        discount_line_see.write({
                            'invoice_line_tax_ids': [(6, 0, lines_tax_ids[0].invoice_line_tax_ids.ids)]
                        })
                    else:
                        discount_line_see.write({
                            'invoice_line_tax_ids': [(6, 0, [])]
                        })
                    total_prorate_amount -= total_prorate_amount_see

                discount_line_sor = discount_line.copy({
                    'quantity': 1,
                    'price_unit': -1 * total_prorate_amount,
                    'description': 'ส่วนลดสินค้าที่คืน',
                    'prorate_amount': 0,
                    'prorate_amount_exclude': 0,
                    'prorate_vat': 0,
                    'prorate_amount_2': 0,
                    'prorate_amount_exclude_2': 0,
                    'prorate_vat_2': 0,
                    'is_type_discount_f_see': False,
                })
                lines_tax_ids = cn_obj.invoice_line_ids.filtered(lambda l: len(l.invoice_line_tax_ids))
                if len(lines_tax_ids):
                    discount_line_sor.write({
                        'invoice_line_tax_ids': [(6, 0, lines_tax_ids[0].invoice_line_tax_ids.ids)]
                    })
                else:
                    discount_line_sor.write({
                        'invoice_line_tax_ids': [(6, 0, [])]
                    })

        for line in to_delete_line:
            line.unlink() 

        cn_obj._onchange_invoice_line_ids()
        cn_obj._compute_amount()
        # import pdb; pdb.set_trace()
        for cn_line in cn_obj.invoice_line_ids: #reverting to original name for special discount
            if cn_line.promotion_id and cn_line.is_type_discount_f_see: #only change name if there is a special discount line
                cn_line.write({
                    'name': special_discount_name,
                })

        #reverting to original name for special discount
        for cn_line in cn_obj.invoice_line_ids: 
            #only change name if there is a special discount line
            if cn_line.promotion_id and cn_line.is_type_discount_f_see: 
                cn_line.write({
                    'name': special_discount_name,
                })

    @api.model
    def return_so_from_ui(self):
        so_id = self._context.get('order_id', False)
        call_request_reverse = self._context.get('call_request_reverse', True)
        return_reason_id = self._context.get('return_reason_id', False)
        return_approver_id = self._context.get('return_approver_id', False)
        return_approve_datetime = self._context.get('return_approve_datetime', False)
        order_lines = self._context.get('order_lines', False)

        if any([
            not so_id,
            not return_reason_id,
            not return_approver_id,
            not return_approve_datetime,
            not order_lines,
        ]):
            return {
                'status': 'fail',
                'message': 'Api Context fail',
                'length': 0,
                'records': [],
            }

        so_id = self.browse(so_id)
        if so_id.state not in ('sale', 'done'):
            raise UserError(_('Can return sale only state Sale and Lock'))

        original_pickings = so_id.picking_ids.filtered((lambda picking: picking.origin == so_id.name))
        
        for original_picking in original_pickings:
            if original_picking.state == 'assigned':
                # prepare, create move stock to be done
                self.env['stock.immediate.transfer'].action_confirm_stock_immediate_transfer(original_picking)
                break

        order_lines_by_inv_line_id = {}
        move_lines = []
        for order_line in order_lines:
            line_id = order_line.get('id', False)
            qty = order_line.get('qty', False)
            if not line_id or not qty:
                raise UserError(_('Context line fail'))

            line = so_id.order_line.filtered(lambda l: l.id == line_id)
            if line:
                if not (line.invoice_lines and line.invoice_lines.id):
                    raise UserError(_('There is no invoice line'))

                if line.line_qty_returned and line.line_qty_returned >= line.product_uom_qty:
                    # raise UserError(_('Already Return line'))
                    continue
                elif line.line_qty_returned and line.line_qty_returned + qty > line.product_uom_qty:
                    # raise UserError(_('Cannot return over remaining qty'))
                    continue
                order_lines_by_inv_line_id[line.invoice_lines.id] = {
                    'line': line,
                    'qty': qty,
                }

                move_lines.append({
                    'product_id': line.product_id.id,
                    'product_qty': qty,
                })
            else:
                raise UserError(_('Not found line ID'))

        ctx = dict(self._context)
        ctx.update({
            'active_id': original_picking.id,
            'active_model': original_picking._name,
            'is_force_assign': True,
            'return_reason_id': return_reason_id,
            'return_approver_id': return_approver_id,
            'return_approve_datetime': return_approve_datetime,
        })
        return_picking_id = self.env['stock.return.picking'].with_context(
            ctx
        ).create_return_picking_from_dict(
            original_picking,
            move_lines
        )
        new_ctx = dict(self.env.context.copy())
        new_ctx.update({
            'is_not_invoice_open_auto': False,
            'is_replace_origin': False,
            'skip_modify_cn': False,
        })
        return_picking_id.action_update_stock_move_date_to_now()
        return_picking_id.action_confirm()
        return_picking_id.force_assign()
        self.env['stock.immediate.transfer'].with_context(
            new_ctx
        ).action_confirm_stock_immediate_transfer(return_picking_id)

        # find credit not from picking # in def create cn, there is update picking id
        cn_obj = self.env['account.invoice'].search([('picking_id', '=', return_picking_id.id)])

        so_id.modify_cn_from_dict(cn_obj, order_lines_by_inv_line_id)

        # validate credit note to be state open
        cn_obj.action_invoice_open()

        account_payment_id = False
        if cn_obj.state == 'open' and so_id.sale_payment_type != 'credit':
            # check context to create account payment or not
            if self._context.get('is_create_payment', True):
                account_payment_id = self.env['account.payment'].create_payment_from_account_invoice(cn_obj)

        if so_id.type_sale_ofm and call_request_reverse:
            self.call_prs_request_reverse()

        return {
            'status': 'success',
            'account_invoice_id': cn_obj.id,
            'return_picking_id': return_picking_id.id,
            'account_payment_id': account_payment_id and account_payment_id.id or False,
        }

    def call_prs_request_reverse(self):
        so_id = self._context.get('order_id', False)
        return_reason_id = self._context.get('return_reason_id', False)
        return_approver_id = self._context.get('return_approver_id', False)
        return_approve_datetime = self._context.get('return_approve_datetime', False)
        order_lines = self._context.get('order_lines', False)

        so_id = self.browse(so_id)

        dict_lines = {order_line['id']: order_line['qty'] for order_line in order_lines}
        line_ids = so_id.order_line.filtered(
            lambda x: x.id in [key for key, value in dict_lines.items()]
        )

        product_qty_map = {}
        product_ids = []
        for line in line_ids:
            if dict_lines.get(line.id, False):
                product_qty_map.update({
                    line.product_id.id: dict_lines[line.id]
                })
        product_ids = [line.product_id.id for line in line_ids]

        purchase_order_line = self.env['purchase.order.line']
        purchase_order = self.env['purchase.order']
        stock_return_picking = self.env['stock.return.picking']
        stock_picking = self.env['stock.picking']
        purchase_order_line_ids = so_id.purchase_order_ids.mapped('order_line')
        purchase_order_line += purchase_order_line_ids.filtered(
            lambda x: x.product_id.id in product_ids
        )
        purchase_order += purchase_order_line.mapped('order_id')
        for purchase_order_id in purchase_order:
            picking_id = min(purchase_order_id.picking_ids.ids)
            ctx = dict(self._context)
            ctx.update({
                'active_id': picking_id,
                'active_model': purchase_order_id.picking_ids._name,
                'is_force_assign': True,
                'return_reason_id': return_reason_id,
                'return_approver_id': return_approver_id,
                'return_approve_datetime': return_approve_datetime,
            })
            stock_return_picking_id = stock_return_picking.with_context(
                ctx
            ).create({
                'return_reason_id': return_reason_id
            })

            stock_return_picking_id.with_context(ctx).create_returns()

            picking_id = max(purchase_order_id.picking_ids.ids)

            stock_picking_id = stock_picking.browse(picking_id)
            for move_line in stock_picking_id.move_lines:
                if move_line.product_id.id not in product_ids:
                    move_line.unlink()
                else:
                    product_qty = product_qty_map.get(move_line.product_id.id, 0)
                    move_line.write({
                        'product_uom_qty': product_qty
                    })
            stock_picking_id.action_confirm()
            stock_picking_id.action_request_reverse()

        return True

    @api.model
    def create(self, vals):

        if vals.get('branch_id', False):
            branch_id = self.env['pos.branch'].browse(
                vals.get('branch_id')
            )
        else:
            raise UserError(_(u"Don't Have Branch ID"))

        date_order = vals.get('date_order', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        name_no = self.generate_qu_no(branch_id, date_order)
        vals.update({'name': name_no,
                     'quotation_no': name_no
                     })
        res = super(SaleOrder, self).create(vals)
        return res

    @api.onchange('branch_id')
    def onchange_branch(self):
        for item in self:
            item.warehouse_id = item.branch_id.warehouse_id.id


    @api.model
    def cancel_quotaions(self):
        """Cron job for auto change state quatations from draft to cancel
            if  Expiration Date <= (the days that run cron_job)
        """
        _logger.info('run cronjob cancel_quotaions in model sale.order')
        self._cr.execute(""" 
                select so.validity_date,so.id
                from sale_order so 
                where ((so.validity_date)::date  < (now()::date))
                and state in ('draft','sent')
                and sale_payment_type is null 
                """)
        sale_order_dict = self._cr.dictfetchall()
        for sale_order_line in sale_order_dict:
            sale_order_obj = self.env['sale.order'].search(
                [('id', '=', sale_order_line.get('id', False)), ])
            sale_order_obj.action_cancel()
            _logger.info('Cancel Quatation Name: {}'.format(sale_order_obj[0].name))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def default_check_partner(self):
        partner_id = self._context.get('partner_id', False)

        if partner_id:
            return True
        else:
            raise except_orm(_('Error!'), _(u"Please select Customer."))

    is_partner_id = fields.Boolean(
        string='Check Partner',
        default=default_check_partner,
        store=False,
    )

    branch_id = fields.Many2one(
        "pos.branch",
        related='order_id.branch_id',
        string="Branch",
    )

    prorate_amount = fields.Float(
        string='Prorate Amount',
        default=0,
        store=True,
        readonly=True,
    )

    product_qty_available = fields.Integer(
        string='Quantity Available',
        readonly=True
    )

    is_danger = fields.Boolean(
        string='Highlight Red Row',
        default=True,
    )

    product_status_correct = fields.Boolean(
        string='Product Status Correct',
        readonly=True
    )

    product_uom_show = fields.Many2one(
        comodel_name='product.uom',
        string='Unit of Measure',
        readonly=True,
        related='product_uom'
    )

    price_unit_show = fields.Float(
        string='Unit Price',
        required=True,
        digits=dp.get_precision('Product Price'),
        related='price_unit',
        readonly=True,
    )

    tax_id_show = fields.Many2many(
        comodel_name='account.tax',
        string='Taxes',
        readonly=True,
        related='tax_id'
    )

    product_status = fields.Char(
        string='Product Status',
    )

    product_status_show = fields.Char(
        string='Product Status',
        related='product_status',
        readonly=True,
        store=False,
    )

    is_delivery_fee_ofm = fields.Boolean(
        string='IsDeliveryFee',
    )

    is_type_delivery_special = fields.Boolean(
        string="Type Delivery Special",
        default=False,
    )

    is_type_delivery_by_order = fields.Boolean(
        string="Type Delivery F'See or < 499",
        default=False,
    )

    is_type_discount = fields.Boolean(
        string="Type Discount",
        default=False,
    )

    is_type_discount_f_see = fields.Boolean(
        string="Type Discount F'See",
        default=False,
    )

    price_subtotal_wo_discount = fields.Float(
        # compute="_compute_amount_line_all",
        digits=0,
        string='Subtotal w/o Tax'
    )
    price_subtotal_wo_discount_incl = fields.Float(
        # compute="_compute_amount_line_all",
        digits=0,
        string='Subtotal'
    )

    promotion_id = fields.Many2one(
        comodel_name='pos.promotion',
        string='Promotion ID',
        readonly=True,
        ondelete='restrict'
    )

    promotion_condition_id = fields.Many2one(
        comodel_name='pos.promotion.condition',
        string='Promotion Condition ID',
        readonly=True,
        ondelete='restrict'
    )

    promotion_type = fields.Selection(
        related='promotion_id.promotion_type',
        selection=[
            ('step', 'Step'),
            ('loop', 'Loop'),
            ('mapping', 'Loop(Mapping)'),
        ],
        string='Promotion Type',
        readonly=True,
    )

    reward_type = fields.Selection(
        string='Reward Type',
        selection=[
            ('discount', 'Discount'),
            ('product', 'Product'),
        ],
        readonly=True,
    )

    promotion_name = fields.Char(
        string='Promotion',
        readonly=True,
    )

    promotion = fields.Boolean(
        'Is Promotion'
    )

    free_product_id = fields.Many2one(
        comodel_name='product.product',
        string="Reward Product",
        required=False,
        readonly=True,
    )

    prorate_amount = fields.Float(
        string='Prorate Amount',
        default=0,
        store=True,
        readonly=True,
    )

    prorate_amount_exclude = fields.Float(
        string='Prorate Amount Exclude Vat',
        default=0,
        store=True,
        readonly=True,
    )

    prorate_vat = fields.Float(
        string='Prorate Vat',
        default=0,
        store=True,
        readonly=True,
    )

    prorate_amount_2 = fields.Float(
        string='Prorate Amount See',
        default=0,
        store=True,
        readonly=True,
    )

    prorate_amount_exclude_2 = fields.Float(
        string='Prorate Amount Exclude Vat See',
        default=0,
        store=True,
        readonly=True,
    )

    prorate_vat_2 = fields.Float(
        string='Prorate Vat See',
        default=0,
        store=True,
        readonly=True,
    )

    delivery_fee_ofm = fields.Float(
        string='DeliveryFee',
    )

    delivery_fee_ofm_show = fields.Float(
        string='DeliveryFee',
        readonly=True,
        related='delivery_fee_ofm',
    )

    is_best_deal_promotion = fields.Boolean(
        string="Best Deal Promotion",
    )

    force_add = fields.Boolean(
        string="Force Add Promotion",
        default=False,
    )

    is_line_discount_delivery_promotion = fields.Boolean(
        string="Flag Line is Discount delivery Promotion",
        default=False,
        readonly=True,
    )

    product_status_odoo = fields.Char(
        string='Product Status Odoo',
    )

    product_status_ofm = fields.Char(
        string='Product Status OFM',
        translate=True
    )

    is_prs_price_zero = fields.Boolean(
        string="Price PRS Zero",
        default=False,
    )

    line_qty_returned = fields.Integer(
        string="Returned Qty",
        readonly=True,
    )

    prorate_ids = fields.One2many(
        comodel_name="pos.promotion.prorate",
        inverse_name="sale_line_id",
        string="Prorate Detail",
        readonly=True,
    )

    def check_line_discount_delivery_promotion(self, vals):
        is_type_delivery_by_order = vals.get('is_type_delivery_by_order', False)
        is_type_delivery_f_see = vals.get('is_type_delivery_f_see', False)
        is_type_delivery_special = vals.get('is_type_delivery_special', False)
        is_type_discount = vals.get('is_type_discount', False)
        is_type_discount_f_see = vals.get('is_type_discount_f_see', False)
        promotion = vals.get('promotion', False)
        product_uom_qty = vals.get('product_uom_qty', False)
        price_unit = vals.get('price_unit', False)

        if any([
            is_type_delivery_by_order,
            is_type_delivery_f_see,
            is_type_delivery_special,
            is_type_discount,
            is_type_discount_f_see,
            all([
                promotion,
                any([
                    price_unit < 0,
                    product_uom_qty < 0,
                ])
            ])
        ]):
            vals.update({
                'is_line_discount_delivery_promotion': True,
                'is_danger': False,
            })

        return vals

    def update_name_product_promotion_free(self, vals):
        promotion = vals.get('promotion', False)
        product_uom_qty = vals.get('product_uom_qty', False)
        price_unit = vals.get('price_unit', False)

        if all([
            promotion,
            price_unit >= 0,
            product_uom_qty > 0,
        ]):
            product_id = vals.get('product_id', False)

            if product_id:
                product_id = self.env['product.product'].browse(product_id)

                vals.update({
                    'name': ''.join([
                        'แถม: ',
                        '[',
                        product_id.default_code,
                        ']',
                        ' ',
                        product_id.product_tmpl_id.name
                    ])
                })

        return vals

    @api.multi
    @api.depends('product_id')
    def compute_product_status_name_abb(self):
        for rec in self:
            if rec.product_id:
                if rec.product_id.prod_status == u'NonStock':
                    rec.product_status = 'Non Stock'
                else:
                    rec.product_status = 'Stock'

    @api.onchange('product_uom_qty', 'product_status')
    def onchange_check_qty_with_qty_available(self):
        is_danger = False

        if any([
            all([
                self.product_uom_qty > self.product_qty_available,
                self.product_id.prod_status != u'NonStock'
            ]),
            not self.product_status_correct,
            self.is_prs_price_zero
        ]):
            is_danger = True

        if self.is_line_discount_delivery_promotion:
            is_danger = False

        if self.product_id.type == 'service':
            is_danger = False

        self.is_danger = is_danger

    @api.onchange('product_id')
    def onchange_product_status_name_abb(self):
        for rec in self:
            product_status_odoo = rec.product_id.prod_status
            rec.product_status_odoo = product_status_odoo

            if product_status_odoo == u'NonStock':
                rec.product_status = 'Non Stock'
            else:
                rec.product_status = 'Stock'

    @api.onchange('product_id')
    def onchange_get_delivery_fee(self):
        if self.product_id.is_delivery_fee_ofm:
            self.delivery_fee_ofm = self.product_id.delivery_fee_ofm

    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        res = super(SaleOrderLine, self)._prepare_order_line_procurement(group_id)
        res.update({
            'branch_id': self.branch_id.id
        })
        return res

    def show_notify_product_status_incorrect(self):
        if self.product_id \
                and self.product_id.type != 'service' \
                and not self.is_line_discount_delivery_promotion \
                and not self.product_status_correct:
            default_code = self.product_id.default_code if self.product_id.default_code else ''
            message_warning = default_code + ': Product Status Incorrect'
            message_warning += '<br/>' + 'สถานะของสินค้าไม่ตรงกัน'
            message_warning += '<br/>' + 'สถานะ ofm: ' + self.product_status_ofm
            if self._context.get('no_warning', False) or self._context.get('text', False):
                return message_warning
            else:
                self.env.user.notify_warning(
                    "Warning",
                    message_warning,
                    True
                )
        return False

    def check_product_prs_zero(self, partner_id, company_id, branch_id):
        if self.product_id \
                and self.product_id.type != 'service' \
                and not self.is_line_discount_delivery_promotion \
                and self.product_id.prod_status != 'Free' \
                and self.product_id.find_purchase_price_with_dropship(partner_id, company_id, branch_id) == 0:
            self.is_prs_price_zero = True
            self.is_danger = True
        else:
            self.is_prs_price_zero = False

        if self.product_id \
                and self.product_id.type == 'service' \
                and not self.is_line_discount_delivery_promotion \
                and self.product_id.prod_status != 'Free' \
                and self.product_id.find_purchase_price_with_dropship(partner_id, company_id, branch_id) == 0:
            self.is_danger = False

    def show_notify_product_prs_zero(self):
        if self.product_id and self.is_prs_price_zero:
            default_code = self.product_id.default_code if self.product_id.default_code else ''
            message_warning = default_code + ': Product Incorrect'
            message_warning += '<br/>' + 'ไม่สามารถซื้อสินค้าชิ้นนี้ได้'
            if self._context.get('no_warning', False) or self._context.get('text', False):
                return message_warning
            else:
                self.env.user.notify_warning(
                    "Warning",
                    message_warning,
                    True
                )
        return False

    def get_readonly_filed_save(self, vals):

        return vals

    @api.model
    def create(self, vals):
        vals = self.get_readonly_filed_save(vals)
        vals = self.check_line_discount_delivery_promotion(vals)
        vals = self.update_name_product_promotion_free(vals)

        res = super(SaleOrderLine, self).create(vals)

        return res

    @api.multi
    def write(self, vals):
        for rec in self:
            vals = rec.get_readonly_filed_save(vals)

            res = super(SaleOrderLine, rec).write(vals)

            return res

    @api.multi
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()

        res.update({
            'branch_id': self.branch_id.id,
            'so_id': self.id,
            'type_sale_ofm': self.type_sale_ofm,
        })

        return res

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        res.update({
            'promotion_id': self.promotion_id.id,
            'promotion_condition_id': self.promotion_condition_id.id,
            'promotion_name': self.promotion_name,
            'promotion': self.promotion,
            'free_product_id': self.free_product_id.id,
            'prorate_amount': self.prorate_amount,
            'prorate_amount_exclude': self.prorate_amount_exclude,
            'prorate_vat': self.prorate_vat,
            'prorate_amount_2': self.prorate_amount_2,
            'prorate_amount_exclude_2': self.prorate_amount_exclude_2,
            'prorate_vat_2': self.prorate_vat_2,
            'is_type_discount_f_see': self.is_type_discount_f_see,
            'reward_type': self.reward_type,
        })
        return res
