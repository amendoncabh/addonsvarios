# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from pytz import timezone

from odoo import models, fields, api
from odoo.exceptions import except_orm
from odoo.tools import logging, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.translate import _
import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class PurchaseOrdersConfirmAll(models.Model):
    _name = 'purchase.orders.confirm.all'

    @api.multi
    def action_approve(self):
        for record in self:
            active_ids = record._context.get('active_ids')
            porchase_orders = record.env['purchase.order'].search([
                ('id', 'in', active_ids)
            ])
            for porchase_order in porchase_orders:
                porchase_order.button_confirm()


class PurchaseRequestOFMHeader(models.Model):
    _inherit = 'purchase.order'
    _name = 'ofm.purchase.order.header'

    READONLY_STATES = {
        'sent': [('readonly', True)],
        'waiting': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('sent', 'Sent'),
            ('waiting', 'Waiting for Edit PR'),
            ('cancel', 'Cancelled'),
            ('purchase', 'Purchase Order')
        ],
        string='Status',
        readonly=True,
        index=True,
        copy=False,
        default='draft',
        track_visibility='onchange'
    )

    type_purchase_ofm = fields.Boolean(
        string='Purchase Request OFM',
        readonly=True
    )

    name = fields.Char(
        string='Order Reference',
        required=True,
        index=True,
        copy=False,
        default='New'
    )

    ofm_purchase_order_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='ofm_purchase_order_header_id',
        readonly=False,
    )

    ofm_purchase_order_line_ids = fields.One2many(
        comodel_name='ofm.purchase.order.line',
        inverse_name='ofm_purchase_order_header_id',
        string='OFM Order Line'
    )

    is_header_can_create_order_line = fields.Boolean(
        string='Order Line Can Create',
        default=True,
        compute='check_is_header_can_create_order_line',
    )

    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )

    amount_tax = fields.Monetary(
        string='Taxes',
        store=True,
        readonly=True,
        compute='_amount_all'
    )

    amount_total = fields.Monetary(
        string='Total',
        store=True,
        readonly=True,
        compute='_amount_all'
    )

    @api.multi
    @api.depends('name', 'partner_ref')
    def name_get(self):
        result = []
        for po in self:
            name = po.name

            result.append((po.id, name))
        return result

    @api.depends('ofm_purchase_order_line_ids.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.ofm_purchase_order_line_ids:
                amount_untaxed += line.price_subtotal
                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    taxes = line.taxes_id.compute_all(
                        line.price_unit,
                        line.ofm_purchase_order_header_id.currency_id,
                        line.product_qty,
                        product=line.product_id,
                        partner=line.ofm_purchase_order_header_id.partner_id
                    )
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.depends('ofm_purchase_order_line_ids.date_planned')
    def _compute_date_planned(self):
        for order in self:
            min_date = False
            order_line = order.ofm_purchase_order_line_ids
            for line in order_line:
                if not min_date or line.date_planned < min_date:
                    min_date = line.date_planned
            if min_date:
                order.date_planned = min_date

    def check_order_line_duplicate(self, vals):
        # 0 = Create, 1 = Edit, 2 = Delete, 3 = ??, 4 = Not Change
        product = []
        ofm_purchase_order_line_ids = vals.get('ofm_purchase_order_line_ids', False)
        if ofm_purchase_order_line_ids:
            for order_line in ofm_purchase_order_line_ids:
                product_id = False

                if order_line[0] in [0, 1]:
                    if order_line[2].get('product_id', False):
                        product_id = self.env['product.product'].browse(order_line[2].get('product_id'))
                    else:
                        product_id = self.ofm_purchase_order_line_ids.browse(order_line[1]).product_id
                elif order_line[0] == 4:
                    product_id = self.ofm_purchase_order_line_ids.browse(order_line[1]).product_id

                if product_id:
                    if product_id.default_code in product:
                        raise except_orm(_('Error!'), "\"" + product_id.name + "\"" + u' Duplicate')
                    else:
                        product.append(product_id.default_code)

    @api.depends('ofm_purchase_order_ids')
    def check_is_header_can_create_order_line(self):
        if self.ofm_purchase_order_ids:
            self.is_header_can_create_order_line = False
        else:
            self.is_header_can_create_order_line = True

    def call_api_create_so_ofm(self):
        tr_convert = self.env['tr.convert']
        ofm_sync_data = self.env['ofm.sync.data']

        api_req_header = ofm_sync_data.call_api_request_token_ofm()

        if api_req_header:
            is_new_pr_header = self._context.get('is_new_pr_header', False)

            if is_new_pr_header:
                purchase_order_ids = self.ofm_purchase_order_ids.filtered(
                    lambda po_rec: not po_rec.is_sent_ofm
                )
            else:
                order_id = self._context.get('order_id', False)
                purchase_order_ids = order_id if order_id else False

            if not purchase_order_ids:
                raise except_orm(_('Error!'), 'Don\'t have Purchase Request.')

            for purchase_order_id in purchase_order_ids:
                if purchase_order_id.state == u'draft':
                    purchase_order_id._amount_all_ofm()
                    order_line_ids = purchase_order_id.ofm_purchase_order_line_ids

                    i_vat_last_product = 0.0
                    order_line = []

                    for line in order_line_ids:
                        line_createon = str(tr_convert.convert_datetime_to_bangkok(line.create_date))
                        line_updateon = str(tr_convert.convert_datetime_to_bangkok(line.write_date))
                        line_transferon = str(tr_convert.convert_datetime_to_bangkok(datetime.now(timezone('UTC'))))

                        i_vat_last_product = line.taxes_id.amount
                        order_line.append({
                            'fono': '',
                            'prno': purchase_order_id.name,
                            'pid': line.product_id.default_code,
                            'qty': int(line.product_qty),
                            'unitprice': line.price_unit,
                            'deliveryfee': line.product_id.delivery_fee_ofm,
                            'discountrate': 0,
                            'createby': line.create_uid.id,
                            'createon': line_createon,
                            'updateby': line.write_uid.id,
                            'updateon': line_updateon,
                            'transferon': line_transferon,
                            'isbestdeal': 'True' if line.product_id.is_best_deal_promotion else 'False'
                        })

                    if self.sale_order_id:
                        ship_address = self.sale_order_id.partner_id
                        ship_contactor = self.sale_order_id.partner_id
                    else:
                        ship_address = self.branch_id
                        ship_contactor = self.create_uid.partner_id

                    shipaddr = ship_address.street[0:] if ship_address.street else ''
                    shipaddr += u' ' + ship_address.alley[0:] if ship_address.alley else ''
                    shipaddr += u' ' + ship_address.street2[0:] if ship_address.street2 else ''
                    shipaddr += u' ' + ship_address.moo[0:] if ship_address.moo else ''
                    shipaddr = list(shipaddr)
                    shipaddr1 = u''
                    shipaddr2 = u''
                    shipaddr3 = u''
                    shipaddr4 = u''

                    for index in range(0, len(shipaddr), 1):
                        if 0 <= index <= 49:
                            shipaddr1 += shipaddr[index]
                        elif 50 <= index <= 99:
                            shipaddr2 += shipaddr[index]
                        elif 100 <= index <= 149:
                            shipaddr3 += shipaddr[index]
                        elif 150 <= index <= 199:
                            shipaddr4 += shipaddr[index]

                    tambon = ship_address.tambon_id.name[0:] if ship_address.tambon_id.name else ''
                    aumphur = ship_address.amphur_id.name[0:] if ship_address.amphur_id.name else ''
                    province = ship_address.province_id.name[0:] if ship_address.province_id.name else ''
                    zip = ship_address.zip_id.name[0:] if ship_address.zip_id.name else ''

                    if ship_contactor.first_name:
                        shipcontactor = ship_contactor.first_name
                        if ship_contactor.last_name:
                            shipcontactor += ' ' + ship_contactor.last_name
                    else:
                        shipcontactor = ''

                    shipphoneno = ship_contactor.phone[0:] if ship_contactor.phone else ''

                    contactorname = shipcontactor
                    contactorphone = shipphoneno
                    contactorfax = ship_contactor.fax[0:] if ship_contactor.fax else ''
                    contactoremail = ship_contactor.email[0:] if ship_contactor.email else ''
                    contactormobileno = ship_contactor.mobile[0:] if ship_contactor.mobile else ''

                    createon = str(tr_convert.convert_datetime_to_bangkok(purchase_order_id.create_date))
                    updateon = str(tr_convert.convert_datetime_to_bangkok(purchase_order_id.write_date))
                    transferon = str(tr_convert.convert_datetime_to_bangkok(datetime.now(timezone('UTC'))))
                    deliverydate = str(tr_convert.convert_datetime_to_bangkok(purchase_order_id.date_planned))

                    if purchase_order_id.type_to_ofm == 'store':
                        type_to_ofm = 'manual'
                    elif purchase_order_id.type_to_ofm == 'fulfillment':
                        type_to_ofm = 'suggest'
                    else:
                        type_to_ofm = purchase_order_id.type_to_ofm

                    create_so_parameter = {
                        'prno': purchase_order_id.name,
                        'prchannel': type_to_ofm,
                        'documentno': purchase_order_id.name,
                        'storecode': purchase_order_id.branch_id.branch_code,
                        'deliverydate': deliverydate,
                        'deliveryfeebyitem': 0,
                        'deliveryfeebyorder': 0,
                        'shipcontactor': shipcontactor,
                        'shipphoneno': shipphoneno,
                        'shipaddr1': shipaddr1,
                        'shipaddr2': shipaddr2,
                        'shipaddr3': shipaddr3,
                        'shipaddr4': shipaddr4,
                        'shipsubdistrict': tambon,
                        'shipdistrict': aumphur,
                        'shipprovince': province,
                        'shippostcode': zip,
                        'shippingremark': self.comment_po if self.comment_po else '',
                        'contactorname': contactorname,
                        'contactorphone': contactorphone,
                        'contactorfax': contactorfax,
                        'contactoremail': contactoremail,
                        'contactormobileno': contactormobileno,
                        'discountrate': 0,
                        'vatrate': i_vat_last_product,
                        'totamt': purchase_order_id.amount_untaxed_ofm,
                        'discamt': 0,
                        'netamt': purchase_order_id.amount_untaxed_ofm,
                        'vatamt': purchase_order_id.amount_tax_ofm,
                        'sumamt': purchase_order_id.amount_total_ofm,
                        'createby': purchase_order_id.create_uid.id,
                        'createon': createon,
                        'updateby': purchase_order_id.write_uid.id,
                        'updateon': updateon,
                        'transferon': transferon,
                        'franchiseCustShippingID': purchase_order_id.branch_id.id,
                        'franchiseCustID': purchase_order_id.branch_id.id,
                        'documentStatus': purchase_order_id.state,
                        'prodTotamtIncVat': purchase_order_id.amount_total_ofm,
                        'items': order_line
                    }

                    ofm_sync_data.ofm_call_api('prs_api_url_create_so', api_req_header, create_so_parameter)

                    purchase_order_id.button_sent()
                    self.env.cr.commit()

            self.get_purchase_request_header_no()
            self.action_update_send()

    def create_purchase_order(self, order_line_collection, order_ids):
        if len(order_line_collection) == 0:
            return True

        for order_line_ids in order_line_collection:
            if len(order_line_ids) == 0:
                break

            if len(order_ids) > 0:
                purchase_order_id = order_ids[0]
                order_ids = []
            else:
                purchase_order = self.env['purchase.order']
                purchase_order_create_dict = {}

                for pr_field in purchase_order._fields:
                    if pr_field in self._fields:
                        if purchase_order._fields.get(pr_field).type == 'many2one':
                            purchase_order_create_dict.update({
                                pr_field: self[pr_field].id
                            })
                        elif purchase_order._fields.get(pr_field).type not in ['one2many', 'many2many']:
                            purchase_order_create_dict.update({
                                pr_field: self[pr_field]
                            })

                purchase_order_create_dict['ofm_purchase_order_header_id'] = self.id

                purchase_order_id = purchase_order.create(purchase_order_create_dict)

            if not purchase_order_id.is_sent_ofm:
                purchase_order_id.name = purchase_order_id.get_pr_no()

            for order_line_id in order_line_ids:
                order_line_id.write({
                        'order_id': purchase_order_id.id
                    })

        return order_ids

    def get_purchase_request_header_no(self):
        prefix = 'PRH-' + self.branch_id.branch_code + '%(y)s%(month)s'
        ctx = dict(self._context)
        ctx.update({'res_model': 'purchase.request.header.ofm'})
        self.name = self.branch_id.with_context(ctx).next_sequence(self.date_order, prefix, 5) or '/'

    def get_purchase_order_header_no(self):
        prefix = 'POH-' + self.branch_id.branch_code + '%(y)s%(month)s'
        ctx = dict(self._context)
        ctx.update({'res_model': self._name})

        self.write({
            'purchase_request_no': self.name,
            'name': self.branch_id.with_context(ctx).next_sequence(self.date_order, prefix, 5) or '/'
        })

    def get_order_line_by_product_status(self, order_line, amount_product_per_so):
        order_line_stock = []
        order_line_stock_temp = []
        order_line_stock_none = []
        order_line_stock_none_temp = []

        for line in order_line:
            if not line.order_id:
                if line.product_qty > line.product_qty_available\
                        and line.product_id.prod_status != u'NonStock':
                    raise except_orm(_('Error!'),
                                     'Product "' +
                                     line.product_id.name +
                                     '" can\'t send because '
                                     'Quantity more than Quantity Available in Product Order Line.')
                else:
                    if line.product_id.prod_status == u'NonStock':
                        if amount_product_per_so == 0:
                            order_line_stock_none.append(line)
                        else:
                            if len(order_line_stock_none_temp) < amount_product_per_so:
                                order_line_stock_none_temp.append(line)
                            else:
                                order_line_stock_none.append(order_line_stock_none_temp)
                                order_line_stock_none_temp = [line]
                    else:
                        if amount_product_per_so == 0:
                            order_line_stock.append(line)
                        else:
                            if len(order_line_stock_temp) < amount_product_per_so:
                                order_line_stock_temp.append(line)
                            else:
                                order_line_stock.append(order_line_stock_temp)
                                order_line_stock_temp = [line]

        # Append because order_line_stock_none_temp and order_line_stock_temp <= amount_product_per_so not insert
        order_line_stock_none.append(order_line_stock_none_temp)
        order_line_stock.append(order_line_stock_temp)

        return {
            'stock': order_line_stock,
            'non_stock': order_line_stock_none
        }

    @api.multi
    def action_send(self):
        for rec in self:
            tr_call_api = rec.env['tr.call.api']

            amount_product_per_so = int(rec.env['ir.config_parameter'].search([('key', '=', 'prs_amount_product_per_so')]).value)

            #Prepare Order Line by Product Status
            order_line_by_product_status = rec.get_order_line_by_product_status(rec.ofm_purchase_order_line_ids, amount_product_per_so)

            #Create Purchase Order by Product Status
            order_ids = [rec._context.get('order_id')] if rec._context.get('order_id', False) else []
            order_ids = rec.create_purchase_order(order_line_by_product_status.get('stock'), order_ids)
            rec.create_purchase_order(order_line_by_product_status.get('non_stock'), order_ids)

            rec.env.cr.commit()

            #Send Purchase to OFM by API
            if rec.ofm_purchase_order_ids:
                tr_call_api.call_api_create_so_ofm(rec)

    @api.multi
    def action_re_send(self):
        for rec in self:
            rec.action_send()

        return {}

    @api.multi
    def action_update_send(self):
        for rec in self:
            if rec.state == u'draft':
                amount_sent = 0
                for pr_no in rec.ofm_purchase_order_ids:
                    if pr_no.state == u'sent':
                        amount_sent += 1

                if amount_sent == len(rec.ofm_purchase_order_ids.ids):
                    rec.write({'state': 'sent'})
                else:
                    rec.action_waiting()

        return {}

    @api.multi
    def action_cancel(self):
        for rec in self:
            if rec.state == u'draft':
                rec.write({'state': 'cancel'})

        return {}

    @api.multi
    def action_waiting(self):
        for rec in self:
            if rec.state in ['draft', 'sent']:
                amount_draft = 0
                for pr_no in rec.ofm_purchase_order_ids:
                    if pr_no.state == u'draft':
                        amount_draft += 1

                if amount_draft > 0:
                    rec.write({'state': 'waiting'})

        return {}

    @api.multi
    def action_purchase(self):
        for rec in self:
            if rec.state == u'sent':
                amount_purchase = 0
                for pr_no in rec.ofm_purchase_order_ids:
                    if pr_no.state == u'purchase':
                        amount_purchase += 1

                if amount_purchase == len(rec.ofm_purchase_order_ids.ids):
                    rec.write({'state': 'purchase'})
                    rec.get_purchase_order_header_no()

        return {}

    @api.multi
    def action_view_pr_po(self):
        action = self.env.ref('ofm_purchase_request.ofm_purchase_request_action').read()[0]
        action['domain'] = [('ofm_purchase_order_header_id', '=', self.id)]

        return action


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def _default_branch_id(self):
        if self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id
            return branch_id
        else:
            raise except_orm(_('Error!'), _(u" Please Set Branch For This User "))

    @api.model
    def _default_picking_type(self):
        super(PurchaseOrder, self)._default_picking_type()

        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        branch_id = self.env.user.branch_id.id

        return self.get_picking_type(company_id, branch_id)

    @api.model
    def _default_partner_id(self):
        default_vendor = self.env['ir.config_parameter'].search([('key', '=', 'prs_default_vendor')]).value
        return self.partner_id.search([('vat', '=', default_vendor)]).id

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    state = fields.Selection(
        [
            ('draft', 'PR'),
            ('sent', 'PR Sent'),
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('to approve', 'To Approve'),
            ('purchase', 'Purchase Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled')
        ],
        string='Status',
        readonly=True,
        index=True,
        copy=False,
        default='draft',
        track_visibility='onchange'
    )

    type_purchase_ofm = fields.Boolean(
        string='Purchase Request OFM',
        readonly=True
    )

    type_to_ofm = fields.Selection(
        selection=[
            ('fulfillment', 'Suggest Fulfillment'),
            ('store', 'Send to Store'),
            ('customer', 'Send to Customer'),
        ],
        string='Type to OFM',
        readonly=True,
        default='store'
    )

    ofm_purchase_order_header_id = fields.Many2one(
        comodel_name='ofm.purchase.order.header',
        string='OFM Purchase Order Header',
        readonly=True
    )

    ofm_purchase_order_line_ids = fields.One2many(
        comodel_name='ofm.purchase.order.line',
        inverse_name='order_id',
        string='OFM'
    )

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        required=True,
        states=READONLY_STATES,
        change_default=True,
        track_visibility='always',
        default=_default_partner_id,
    )

    credit_limit_pass = fields.Boolean(
        string='Credit Limit Pass',
        default=False
    )

    date_planned = fields.Datetime(
        string='Scheduled Date',
        compute='_compute_date_planned',
        index=True,
        required=False,
    )

    vendor_so_no = fields.Char(
        string='Vendor Sale Order No.',
        readonly=True
    )

    vendor_invoice_no = fields.Char(
        string='Invoice No.',
        readonly=True
    )

    vendor_invoice_date = fields.Date(
        string='Invoice Date',
        readonly=True
    )

    vendor_cn_reference = fields.Char(
        string='Vendor CN',
        readonly=True,
    )
    vendor_cn_date = fields.Datetime(
        string='Vendor CN Date',
        readonly=True,
    )

    branch_id = fields.Many2one(
        comodel_name='pos.branch',
        string='Branch',
        default=_default_branch_id,
        required=True,
    )
    branch_code = fields.Char(
        related='branch_id.branch_code',
        readonly=True,
    )

    comment_po = fields.Text(
        string='Comment'
    )

    purchase_request_no = fields.Text(
        string='PR No.',
        readonly=True,
    )

    amount_untaxed_ofm = fields.Monetary(
        string='Untaxed Amount',
        readonly=True,
        track_visibility='always',
    )

    amount_tax_ofm = fields.Monetary(
        string='Taxes',
        readonly=True,
    )

    amount_total_ofm = fields.Monetary(
        string='Total',
        readonly=True,
    )

    dliamt_ofm = fields.Monetary(
        string='Deliver Amount',
        readonly=True,
        track_visibility='always'
    )

    dlidate_ofm = fields.Datetime(
        string='Scheduled Date',
        compute='_compute_date_planned',
        index=True,
        required=False,
    )

    deliverfee_ofm = fields.Monetary(
        string='Deliver Fee',
        readonly=True,
        track_visibility='always'
    )

    supdlifeeitem_ofm = fields.Monetary(
        string='Suppiler Deliver Fee',
        readonly=True,
        track_visibility='always'
    )

    supdlifeeorder_ofm = fields.Monetary(
        string='Suppiler Deliver Fee less than 499',
        readonly=True,
        track_visibility='always'
    )

    picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Deliver To',
        states=READONLY_STATES,
        required=True,
        default=_default_picking_type,
        help="This will determine picking type of incoming shipment"
    )

    is_sent_ofm = fields.Boolean(
        string='Flag Sent to OFM',
        readonly=True,
        default=False
    )

    date_purchase_request = fields.Datetime(
        string='PR Date',
        readonly=True
    )

    picking_count_all = fields.Integer(
        compute='_compute_picking_all',
        string='Receptions',
    )

    procurement_name = fields.Text(
        string='Procurement Name',
        readonly=True,
    )

    is_hide_product_incorrect = fields.Boolean(
        string='Product Incorrect',
        default=True,
    )

    @api.multi
    def action_create_picking(self):
        for rec in self:
            rec._create_picking()

            return True

    @api.onchange('company_id', 'branch_id')
    def onchange_clear_order_line(self):
        self.ofm_purchase_order_line_ids = False

    @api.onchange('company_id', 'branch_id')
    def onchange_get_deliver_to(self):
        self.picking_type_id = False
        picking_type_id = self.get_picking_type(self.company_id.id, self.branch_id.id)

        self.update({
            'picking_type_id': picking_type_id
        })

    @api.onchange('date_order')
    def onchange_get_order_line_date_plan(self):
        if self.type_purchase_ofm:
            for order_line_id in self.ofm_purchase_order_line_ids:
                seller = order_line_id.product_id._select_seller(
                    partner_id=order_line_id.partner_id,
                    quantity=order_line_id.product_qty,
                    date=order_line_id.order_id.date_order and order_line_id.order_id.date_order[:10],
                    uom_id=order_line_id.product_uom
                )
                order_line_id.date_planned = order_line_id._get_date_planned(seller).strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
        else:
            for line in self.order_line:
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id, quantity=line.product_qty,
                    date=line.order_id.date_order and line.order_id.date_order[:10], uom_id=line.product_uom)
                line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def onchange_is_hide_product_incorrect(self):
        is_hide_product_incorrect = True

        if self.state == 'draft':
            qty_not_available = self.check_qty_with_qty_available(self.ofm_purchase_order_line_ids)

            if qty_not_available:
                is_hide_product_incorrect = False

        self.is_hide_product_incorrect = is_hide_product_incorrect

    def _amount_all_ofm(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.ofm_purchase_order_line_ids:
                amount_untaxed += line.price_subtotal
                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    taxes = line.taxes_id.compute_all(line.price_unit, line.order_id.currency_id, line.product_qty,
                                                      product=line.product_id, partner=line.order_id.partner_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax

            order.update({
                'amount_untaxed_ofm': order.currency_id.round(amount_untaxed),
                'amount_tax_ofm': order.currency_id.round(amount_tax),
                'amount_total_ofm': amount_untaxed + amount_tax,
            })

    def get_pr_no(self):
        prefix = 'PR-' + self.branch_id.branch_code + '%(y)s%(month)s'
        ctx = dict(self._context)

        if self.type_purchase_ofm:
            ctx.update({'res_model': 'purchase.request.ofm'})
        else:
            ctx.update({'res_model': 'purchase.request'})

        pr_no = self.branch_id.with_context(ctx).next_sequence(self.date_order, prefix, 5) or '/'

        return pr_no

    def get_po_no(self):
        prefix = 'PO-' + self.branch_id.branch_code + '%(y)s%(month)s'
        ctx = dict(self._context)
        ctx.update({'res_model': self._name})
        if self.type_purchase_ofm:
            self.purchase_request_no = self.name

        self.name = self.branch_id.with_context(ctx).next_sequence(self.date_order, prefix, 5) or '/'
        # order.name = self.env['ir.sequence'].next_by_code('purchase.order') or '/'

    def get_order_line_by_product_status(self, order_line, amount_product_per_so):
        order_line_stock = []
        order_line_stock_temp = []
        order_line_stock_none = []
        order_line_stock_none_temp = []

        for line in order_line:
            if line.product_id.prod_status == u'NonStock':
                if amount_product_per_so == 0:
                    order_line_stock_none.append(line)
                else:
                    if len(order_line_stock_none_temp) < amount_product_per_so:
                        order_line_stock_none_temp.append(line)
                    else:
                        order_line_stock_none.append(order_line_stock_none_temp)
                        order_line_stock_none_temp = [line]
            else:
                if amount_product_per_so == 0:
                    order_line_stock.append(line)
                else:
                    if len(order_line_stock_temp) < amount_product_per_so:
                        order_line_stock_temp.append(line)
                    else:
                        order_line_stock.append(order_line_stock_temp)
                        order_line_stock_temp = [line]

        # Append because order_line_stock_none_temp and order_line_stock_temp <= amount_product_per_so not insert
        if len(order_line_stock_none_temp) > 0:
            order_line_stock_none.append(order_line_stock_none_temp)

        if len(order_line_stock_temp) > 0:
            order_line_stock.append(order_line_stock_temp)

        return {
            'stock': order_line_stock,
            'non_stock': order_line_stock_none
        }

    def get_invoice_form_staging_by_cron(self):
        order_ids = self.search([
            ('state', '=', 'completed'),
            ('vendor_invoice_no', '=', False),
            ('sale_order_id', '=', False)
        ])

        ctx = dict(self._context)
        ctx.update({
            'is_get_by_cron': True,
            'tracking_disable': True
        })

        for order_id in order_ids:
            try:
                _logger.info("purchase_order : " + order_id.name)
                ctx.update({
                    'force_company': order_id.company_id.id
                })
                order_id.with_context(ctx).action_get_invoice_from_staging()
            except Exception as e:
                _logger.error("purchase_order : " + order_id.name + e.message)

    def get_picking_type(self, p_company_id, p_branch_id):
        type_obj = self.env['stock.picking.type']
        company_id = p_company_id
        branch_id = p_branch_id
        warehouse_id = self.env['pos.branch'].browse(branch_id).warehouse_id.id
        types = type_obj.search([
            ('code', '=', 'incoming'),
            ('default_location_src_id.usage', '=', 'supplier'),
            ('warehouse_id', '=', warehouse_id),
        ])
        if not types:
            types = type_obj.search([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', warehouse_id),
            ])

        types = types.filtered(
            lambda x: x.branch_id.id == branch_id
        )
        return types[:1]

    @api.multi
    def action_view_picking(self):
        for rec in self:
            res = super(PurchaseOrder, rec).action_view_picking()

            if rec.group_id:
                picking_ids = rec.env['stock.picking'].search([
                    ('group_id', '=', rec.group_id.id),
                ]).ids

                context = res.get('context', {})
                context.update({
                    'group_id': rec.group_id.id
                })

                res['context'] = context

                if len(picking_ids) > 1:
                    res['domain'] = '[(\'id\', \'in\', ' + str(picking_ids) + ')]'
                    res['views'] = []
                    res['res_id'] = False

                return res
            else:
                return False

    def action_reordering_rule(self, mode):
        for order_line_id in self.ofm_purchase_order_line_ids:
            for procurement_id in order_line_id.procurement_ids:
                if mode == 'unlink':
                    if procurement_id.state == 'cancel':
                        procurement_id.reset_to_confirmed()

                    procurement_id.unlink()
                elif mode == 'cancel':
                    procurement_id.cancel()

    def check_date_planned(self, vals):
        for line in vals.get('order_line',[]):
            if not line[2].get('date_planned', False):
                date_planned = datetime.now()
                product_id = line[2].get('product_id', False)
                if product_id:
                    product = self.env['product.supplierinfo'].search([('product_id', '=', product_id)])
                    if product:
                        date_planned += timedelta(days=product.delay)
                line[2]['date_planned'] = date_planned
        return vals

    @api.multi
    def action_get_invoice_from_staging(self):
        for rec in self:
            is_get_by_cron = rec._context.get('is_get_by_cron', False)

            if rec.state == 'completed' \
                    and not rec.vendor_invoice_no:
                ofm_sync_data = rec.env['ofm.sync.data']
                inv_result = ofm_sync_data.get_invoice_from_staging(self, 'Invoice')
                inv_header = inv_result.get('inv_header', {})
                inv_detail = inv_result.get('inv_detail', {})

                if all([
                    len(inv_header) > 0,
                    len(inv_detail) > 0,
                ]):
                    inv_header = self.check_date_planned(inv_header)
                    rec.write(inv_header)
                    rec.order_line._compute_amount()

                    for order_line_id in rec.order_line:
                        order_line_id.onchange_product_status_name_abb()

                    rec.get_po_no()
                    rec.button_approve()
                    rec.ofm_purchase_order_header_id.action_purchase()

                    if not is_get_by_cron:
                        action = rec.env.ref('ofm_purchase_request.ofm_purchase_order_action').read()[0]
                        action['view_mode'] = 'form'
                        action['views'].pop(0)
                        action['res_id'] = rec.id

                        return action
                else:
                    if not is_get_by_cron:
                        raise except_orm(_('Error!'), 'No Invoice.')
                    else:
                        _logger.error('No Invoice.')

        return True

    @api.multi
    def action_cancel_pr_sent(self):
        for rec in self:
            if rec.state == u'sent':
                rec.write({'state': 'cancel'})

        return True

    @api.multi
    def action_create_picking(self):
        for rec in self:
            rec._create_picking()

            return True

    def check_state_before_update_status(self, state_to_be):
        is_update_state = False

        if self.type_purchase_ofm:
            is_update_state = True
        else:
            if state_to_be in ['draft', 'pending'] and self.state in [u'sent', u'cancel']:
                is_update_state = True
            elif state_to_be == 'sent' and self.state in [u'draft']:
                is_update_state = True
            elif state_to_be == 'completed' and self.state in [u'sent', u'pending']:
                is_update_state = True
            elif state_to_be == 'purchase' and self.state in [u'sent', u'draft']:
                is_update_state = True
            elif state_to_be == 'cancel' and self.state in [u'pending', u'draft']:
                is_update_state = True

        return is_update_state

    def check_order_line_duplicate(self, vals):
        # 0 = Create, 1 = Edit, 2 = Delete, 3 = ??, 4 = Not Change
        product = []
        product_duplicate = {}
        ofm_purchase_order_line_ids = vals.get('ofm_purchase_order_line_ids', False)
        if ofm_purchase_order_line_ids:
            for order_line in ofm_purchase_order_line_ids:
                product_id = False

                if order_line[0] in [0, 1]:
                    if order_line[2].get('product_id', False):
                        product_id = self.env['product.product'].browse(order_line[2].get('product_id'))
                    else:
                        product_id = self.ofm_purchase_order_line_ids.browse(order_line[1]).product_id
                elif order_line[0] == 4:
                    product_id = self.ofm_purchase_order_line_ids.browse(order_line[1]).product_id

                if product_id:
                    if product_id.default_code in product:
                        if product_id.default_code not in product_duplicate:
                            product_duplicate.update({product_id.default_code: product_id.name})
                    else:
                        product.append(product_id.default_code)

            product_duplicate_show = ''

            for product in product_duplicate:
                product_duplicate_show += "[" + product + "] " + product_duplicate[product] + "\n"

            if product_duplicate:
                raise except_orm(_('Error!'), 'List of Product Duplicate: \n' + product_duplicate_show)

    def check_qty_with_qty_available(self, order_line):
        is_danger = False
        for line in order_line:
            line.onchange_check_qty_with_qty_available()
            if line.is_danger:
                is_danger = True
                break

        return is_danger

    def check_split_pr(self):
        amount_product_per_so = int(
            self.env['ir.config_parameter'].search([
                ('key', '=', 'prs_amount_product_per_so')
            ]).value
        )

        order_line_by_product_status = self.get_order_line_by_product_status(
            self.ofm_purchase_order_line_ids,
            amount_product_per_so
        )

        return order_line_by_product_status

    def check_quantity_order_line(self):
        is_quantity_pass = True
        if self.type_purchase_ofm:
            for order_line_id in self.ofm_purchase_order_line_ids:
                if order_line_id.product_qty == 0:
                    is_quantity_pass = False
                    break
        else:
            for order_line_id in self.order_line:
                if order_line_id.product_qty == 0:
                    is_quantity_pass = False
                    break

        if not is_quantity_pass:
            raise except_orm(_('Error!'), 'Product no quantity.')

    def get_cn_from_staging(self):
        ofm_sync_data = self.env['ofm.sync.data']
        cn_result = ofm_sync_data.get_invoice_from_staging(self, 'Return')

        return cn_result

    def call_api_check_qty_from_ofm(self):
        tr_call_api = self.env['tr.call.api']
        tr_call_api.call_api_check_qty_from_ofm(self)
        self.onchange_is_hide_product_incorrect()
        for line in self.ofm_purchase_order_line_ids:
            line.show_notify_product_status_incorrect()

    def call_action_send_pr_header(self):
        ctx = dict(self._context)

        if self.ofm_purchase_order_header_id:
            ofm_purchase_order_header_id = self.ofm_purchase_order_header_id
            ctx.update({
                'is_new_pr_header': False,
            })
        else:
            ofm_purchase_order_header_id = self.create_pr_header()
            ctx.update({
                'is_new_pr_header': True,
            })

        ctx.update({
            'order_id': self
        })
        ofm_purchase_order_header_id.with_context(ctx).action_send()

        return ofm_purchase_order_header_id

    @api.depends('order_line.date_planned', 'ofm_purchase_order_line_ids.date_planned')
    def _compute_date_planned(self):
        for order in self:
            super(PurchaseOrder, self)._compute_date_planned()
            min_date = False
            if order.type_purchase_ofm:
                for line in order.ofm_purchase_order_line_ids:
                    if not min_date or line.date_planned < min_date:
                        min_date = line.date_planned
                if min_date:
                    order.date_planned = min_date
                else:
                    order.date_planned = datetime.now()

    @api.multi
    @api.depends('picking_count')
    def _compute_picking_all(self):
        for order in self:
            if order.group_id:
                picking_cancel_ids = order.env['stock.picking'].search([
                    ('group_id', '=', order.group_id.id),
                ]).read('id')

                order.picking_count_all = len(picking_cancel_ids)
            else:
                order.picking_count_all = 0

    @api.multi
    def button_product_incorrect(self):
        for rec in self:
            rec.call_api_check_qty_from_ofm()

            if not rec.is_hide_product_incorrect:
                res_id = rec.env['purchase.order.product.incorrect.wizard'].create({
                    'order_id': rec.id
                })

                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Product Incorrect Management',
                    'res_model': 'purchase.order.product.incorrect.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': rec.env.ref('ofm_purchase_request.purchase_order_check_product_incorrect_wizard', False).id,
                    'res_id': res_id.id,
                    'target': 'new',
                }

    @api.multi
    def button_sent_ofm(self):
        for rec in self:
            rec.check_quantity_order_line()
            rec.call_api_check_qty_from_ofm()
            qty_not_available = rec.check_qty_with_qty_available(rec.ofm_purchase_order_line_ids)

            if not qty_not_available:
                order_id_split = rec.check_split_pr()

                is_split = False
                if len(order_id_split.get('non_stock')) > 0 \
                        and len(order_id_split.get('stock')) > 0:
                    is_split = True
                else:
                    if len(order_id_split.get('non_stock')) > 1:
                        is_split = True
                    elif len(order_id_split.get('stock')) > 1:
                        is_split = True

                if is_split:
                    res_id = self.env['purchase.order.wizard'].create({
                        'message_alert': 'This PR will be split.'
                    })
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Confirm Send Purchase Request',
                        'res_model': 'purchase.order.wizard',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'view_id': self.env.ref('ofm_purchase_request.purchase_request_wizard', False).id,
                        'res_id': res_id.id,
                        'target': 'new',
                    }
                else:
                    rec.call_action_send_pr_header()

    @api.multi
    def button_sent(self):
        for rec in self:
            is_check_state = rec.check_state_before_update_status('sent')
            if is_check_state:
                if not rec.type_purchase_ofm:
                    rec.name = rec.get_pr_no()
                else:
                    rec.update({'is_sent_ofm': True})

                rec.write({
                    'state': 'sent'
                })

            return is_check_state

    @api.multi
    def button_confirm(self):
        for order in self:
            if order.type_purchase_ofm:
                is_check_state = order.check_state_before_update_status('completed')

                if is_check_state:
                    order.write({'state': 'completed'})
            else:
                order.check_quantity_order_line()
                is_check_state = order.check_state_before_update_status('purchase')

                if is_check_state:
                    order.get_po_no()
                    super(PurchaseOrder, order).button_confirm()

            order.date_purchase_request = order.date_order

            return is_check_state

    @api.multi
    def button_pending(self):
        for rec in self:
            is_check_state = rec.check_state_before_update_status('pending')
            if is_check_state:
                rec.write({'state': 'pending'})

            return is_check_state

    @api.multi
    def button_draft(self):
        for rec in self:
            is_check_state = rec.check_state_before_update_status('draft')
            rec.ofm_purchase_order_header_id.action_waiting()

            if is_check_state:
                super(PurchaseOrder, rec).button_draft()
            return is_check_state

    @api.multi
    def button_cancel(self):
        ctx = dict(self._context)
        for rec in self:
            is_check_state = rec.check_state_before_update_status('cancel')
            if is_check_state:
                #go to the sale order and get the list of other PO
                rec_sale_order = rec.sale_order_id
                if rec_sale_order:
                    other_po = rec_sale_order.purchase_order_ids - rec
                    #get all the po names and their states
                    po_names = other_po.mapped('name')
                    po_states = other_po.mapped('state')
                    prefixes = map(lambda name: name[0:2].lower(), po_names)
                    #check if there is PO in the list of prefixes. 
                    # If there is, we should go to default behavior. 
                    # Else, we should check if all of them are cancelled. 
                    # If they are all cancelled, then we should cancel the SO.
                    if ('po' not in prefixes) and ('from_api' in ctx.keys()):
                        all_cancelled = all([state == 'cancel' for state in po_states])
                        if all_cancelled:
                            #cancel sale order
                            rec_sale_order.with_context(ctx).action_cancel_so()

                #continue to default behavior
                rec.action_reordering_rule('cancel')
                super(PurchaseOrder, rec).button_cancel()

            return is_check_state

    def print_pr(self, data):
        return self.env['report'].get_action(self, 'Requests_for_Quotation.jasper')

    def print_po(self, data):
        return self.env['report'].get_action(self, 'purchase_order.jasper')

    def prepare_vender_bill(self):
        if not self.invoice_ids:
            journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
            ]
            journal = self.env['account.journal'].search(journal_domain, limit=1)
        else:
            # Use the same account journal than a previous invoice
            journal = self.invoice_ids[0].journal_id

        if self.type_purchase_ofm:
            reference = self.vendor_invoice_no
            vendor_invoice_date = self.vendor_invoice_date

            if self._context.get('is_add_rd_after_vendor_reference', False):
                reference += '_'
                reference += self._context.get('picking_name_current', '')
        else:
            reference = self.partner_ref
            vendor_invoice_date = ''

        return {
            'purchase_id': self.id,
            'origin': self.name,
            'type': 'in_invoice',
            'journal_id': journal[0].id,
            'account_id': journal[0].default_debit_account_id.id,
            'reference': reference,
            'vendor_invoice_date': vendor_invoice_date,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'branch_id': self.branch_id.id,
            'user_id': self.env.uid,
            'fiscal_position_id': self.fiscal_position_id.id,
            'comment': self.comment_po,
            'note': self.notes,
            'picking_id': self._context.get('picking_id_current', False),
            'type_purchase_ofm': self.type_purchase_ofm,
        }

    def prepare_vender_bill_line(self, invoice):
        # account.invoice > purchase_order_change
        new_lines = self.env['account.invoice.line']
        account_invoice = self.env['account.invoice']
        purchase_invoice_line = account_invoice.invoice_line_ids.mapped('purchase_line_id')
        for line in invoice.purchase_id.order_line - purchase_invoice_line:
            data = invoice._prepare_invoice_line_from_po_line(line)
            new_line = new_lines.new(data)
            new_line._set_additional_fields(invoice)
            new_lines += new_line
        return new_lines

    def create_vender_bill(self):
        Invoice = self.env['account.invoice']
        vender_bill_val = self.prepare_vender_bill()

        invoice = Invoice.new(vender_bill_val)
        invoice._onchange_partner_id()

        invoice.invoice_line_ids += self.prepare_vender_bill_line(invoice)

        invoice.purchase_id = False

        inv = invoice._convert_to_write({name: invoice[name] for name in invoice._cache})

        inv_purchase_id = inv.get('purchase_id', False)

        if not inv_purchase_id:
            inv.update({
                'purchase_id': self.id
            })

        new_invoice = Invoice.create(inv)
        if all([
            self.type_purchase_ofm,
            self.vendor_invoice_no,
            len(self.picking_ids) == 1,
        ]):
            new_invoice.action_invoice_open()

    def create_pr_header(self):
        purchase_order_header_dict = {}
        for purchase_order_field in self._fields:
            if purchase_order_field in self.ofm_purchase_order_header_id._fields:
                if self._fields.get(purchase_order_field).type == 'many2one':
                    purchase_order_header_dict.update({
                        purchase_order_field: self[purchase_order_field].id
                    })
                elif self._fields.get(purchase_order_field).type not in ['one2many', 'many2many']:
                    purchase_order_header_dict.update({
                        purchase_order_field: self[purchase_order_field]
                    })

        ofm_purchase_order_header_id = self.env['ofm.purchase.order.header'].create(purchase_order_header_dict)
        ofm_purchase_order_line_ids = self.env['ofm.purchase.order.line'].search([('order_id', '=', self.id)])

        self.update({
            'ofm_purchase_order_header_id': ofm_purchase_order_header_id.id
        })

        ofm_purchase_order_line_ids.update({
            'order_id': False,
            'ofm_purchase_order_header_id': ofm_purchase_order_header_id.id
        })

        return ofm_purchase_order_header_id

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = 'Draft'

        res = super(PurchaseOrder, self).create(vals)

        if all([
            res,
            not self._context.get('is_suggest', False)
        ]):
            res._amount_all_ofm()

        return res

    @api.multi
    def write(self, vals):
        for rec in self:

            if all([
                rec.type_purchase_ofm,
                rec.state == 'draft',
                rec.name.find('PR') == 0,
            ]):
                ofm_purchase_order_line_ids = vals.get('ofm_purchase_order_line_ids', False)

                if ofm_purchase_order_line_ids:
                    is_error = False
                    for ofm_purchase_order_line_id in ofm_purchase_order_line_ids:
                        if ofm_purchase_order_line_id[0] == 0:
                            is_error = True
                            break
                        elif ofm_purchase_order_line_id[0] == 1:
                            data_edit = ofm_purchase_order_line_id[2]
                            if data_edit.get('product_id', False):
                                is_error = True
                                break

                    if is_error:
                        raise except_orm(_('Error!'), _("Cannot be edited because this PR has been confirmed."))

            res = super(PurchaseOrder, rec).write(vals)

            if all([
                res,
                not rec._context.get('is_write', False)
            ]):
                context = dict(rec._context)
                context.update({
                    'is_write': True
                })

                rec.with_context(context)._amount_all_ofm()

            return res

    @api.multi
    def unlink(self):
        for rec in self:
            rec.action_reordering_rule('unlink')
            return super(PurchaseOrder, rec).unlink()

    @api.model
    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res.update({
            'branch_id': self.branch_id.id,
        })
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_status_odoo = fields.Char(
        string='Product Status Odoo',
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

    is_sent_ofm = fields.Boolean(
        string='Flag Sent to OFM',
        realated='order_id.is_sent_ofm',
        store=True,
    )

    move_ids = fields.One2many(
        'stock.move',
        compute='_compute_move_line_id',
        string='Reservation',
        readonly=True,
        store=True,
    )

    invoice_lines = fields.One2many(
        'account.invoice.line',
        compute='_compute_invoice_line_id',
        string="Bill Lines",
        readonly=True,
        store=True,
    )

    @api.onchange('product_id')
    def onchange_product_status_name_abb(self):
        for rec in self:
            product_status_odoo = rec.product_id.prod_status
            rec.product_status_odoo = product_status_odoo

            if product_status_odoo == u'NonStock':
                rec.product_status = 'Non Stock'
            else:
                rec.product_status = 'Stock'

    @api.multi
    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        index = 0
        for value in res:
            value['branch_id'] = self.order_id.branch_id.id
            res[index] = value
            index += 1
        return res

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(
                line.price_unit,
                line.order_id.currency_id,
                line.product_qty,
                product=line.product_id,
                partner=line.order_id.partner_id
            )

            total_included = taxes['total_included']
            total_excluded = taxes['total_excluded']

            line.update({
                'price_tax': total_included - total_excluded,
                'price_total': total_included,
                'price_subtotal': total_excluded,
            })

    @api.depends('order_id.state', 'move_ids.state')
    def _compute_qty_received(self):
        for line in self:
            if line.order_id.state not in ['purchase', 'done']:
                line.qty_received = 0.0
                continue
            if line.product_id.type not in ['consu', 'product']:
                line.qty_received = line.product_qty
                continue
            total = 0.0
            if line.order_id.group_id:
                params = (
                    line.order_id.group_id.id,
                    line.product_id.id,
                )
                str_query = """
                    select sm.id as move_id
                    from stock_picking sp
                    inner join stock_move sm on sm.picking_id = sp.id
                    where sp.group_id = %s and sm.product_id = %s
                """ % params
                self.env.cr.execute(str_query)
                result = self.env.cr.dictfetchall()
                move_ids = [item['move_id'] for item in result] if result else []
                move_ids = move_ids and self.env['stock.move'].search([
                    ('id', 'in', move_ids)
                ]) or []
                for move in move_ids:
                    if move.state == 'done':
                        if move.product_uom != line.product_uom:
                            qty_convert = move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                        else:
                            qty_convert = move.product_uom_qty

                        if move.picking_id.picking_type_id.code == 'incoming':
                            total += qty_convert
                        else:
                            total -= qty_convert
            line.qty_received = total

    def get_readonly_filed_save(self, vals):

        return vals

    @api.depends('order_id.state', 'order_id.picking_ids')
    def _compute_move_line_id(self):
        for record in self:
            if record.order_id and isinstance(record.order_id.id, int):
                params = (
                    record.order_id.id,
                    record.product_id.id,
                )
                sql_str = """
                    with tb_po_line as (
                        select id
                        from purchase_order_line pol
                        where order_id = %s
                    ),
                    invoice_line as (
                        select id, product_id
                        from stock_move
                        where purchase_line_id in (
                            select id from tb_po_line
                            )
                        )
                    select id from invoice_line where product_id = %s
                    """ % params

                self.env.cr.execute(sql_str)
                results = self.env.cr.dictfetchall()

                if results:
                    move_ids = []
                    for item in results:
                        move_ids.append(item['id'])
                    if move_ids:
                        record.move_ids = move_ids

    @api.depends('order_id.state', 'order_id.invoice_ids')
    def _compute_invoice_line_id(self):
        for record in self:
            if record.order_id and isinstance(record.order_id.id, int):
                params = (
                    record.order_id.id,
                    record.product_id.id,
                )
                sql_str = """
                    with tb_po_line as (
                        select id
                        from purchase_order_line pol
                        where order_id = %s
                    ),
                    move_line as (
                        select id, product_id
                        from account_invoice_line
                        where purchase_line_id in (
                            select id from tb_po_line
                            )
                        )
                    select id from move_line where product_id = %s
                    """ % params

                self.env.cr.execute(sql_str)
                results = self.env.cr.dictfetchall()

                if results:
                    invoice_lines = []
                    for item in results:
                        invoice_lines.append(item['id'])
                    if invoice_lines:
                        record.invoice_lines = invoice_lines

    @api.model
    def create(self, vals):
        vals = self.get_readonly_filed_save(vals)

        res = super(PurchaseOrderLine, self).create(vals)

        return res

    @api.multi
    def write(self, vals):
        for rec in self:
            vals = rec.get_readonly_filed_save(vals)

            res = super(PurchaseOrderLine, rec).write(vals)

            return res


class PurchaseRequestOrderLineOFM(models.Model):
    _inherit = 'purchase.order.line'
    _name = 'ofm.purchase.order.line'
    _description = 'Purchase Order Line'
    _order = 'sequence, id'

    def _get_default_is_header_can_create_order_line(self):
        # if not self._context.get('order_line_can_create', False):
        #     raise except_orm(_('Error!'), _("Cannot add product because pr/po was created."))

        return self._context.get('is_header_can_create_order_line', False)

    def _get_can_create_order_line(self):
        if self._context.get('is_sent_ofm', False):
            raise except_orm(_('Error!'), _("Cannot add product because PR has been sent."))

    procurement_ids = fields.One2many(
        comodel_name='procurement.order',
        inverse_name='ofm_purchase_line_id',
        string='Associated Procurements',
        copy=False
    )

    is_header_can_create_order_line = fields.Boolean(
        string='Order Line Can Create',
        default=_get_default_is_header_can_create_order_line,
        store=False,
        readonly=True,
    )

    state = fields.Selection(
        default='draft',
        related='order_id.state',
        store=True,
    )

    product_qty_available = fields.Integer(
        string='Quantity Available',
        readonly=True
    )

    order_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Order Reference',
        index=True,
        required=False,
        ondelete='cascade'
    )

    ofm_purchase_order_header_id = fields.Many2one(
        comodel_name='ofm.purchase.order.header',
        string='OFM Purchase Order Header',
        index=True,
        ondelete='cascade'
    )

    is_danger = fields.Boolean(
        string='Highlight Red Row',
        default=True,
        readonly=True,
    )

    is_sent_ofm = fields.Boolean(
        string='Flag Sent to OFM',
        realated='order_id.is_sent_ofm',
        default=_get_can_create_order_line
    )

    product_uom_show = fields.Char(
        string='Product Unit of Measure',
        readonly=True,
    )

    price_unit_show = fields.Float(
        string='Unit Price',
        readonly=True,
    )

    name_show = fields.Char(
        string='Description',
        readonly=True,
    )

    date_planned_show = fields.Datetime(
        string='Scheduled Date',
        readonly=True,
    )

    taxes_id_show = fields.Many2many(
        comodel_name='account.tax',
        string='Taxes',
        readonly=True,
        related='taxes_id'
    )

    product_status_correct = fields.Boolean(
        string='Product Status Correct',
        readonly=True
    )

    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='',
        store=True,
        readonly=False,
    )

    price_subtotal_show = fields.Monetary(
        string='Subtotal',
        readonly=True,
    )

    price_total = fields.Monetary(
        string='Total',
        compute='',
        store=True,
        readonly=False,
    )

    price_total_show = fields.Monetary(
        string='Total',
        readonly=True,
    )

    price_tax = fields.Monetary(
        string='Tax',
        compute='',
        store=True,
        readonly=False,
    )

    price_tax_show = fields.Monetary(
        string='Tax',
        readonly=True,
    )

    delivery_fee_ofm = fields.Float(
        string='DeliveryFee',
    )

    discount = fields.Float(
        string='Discount (%)',
        digits=dp.get_precision('Discount'),
        default=0.0
    )

    is_best_deal_promotion = fields.Boolean(
        string="Best Deal Promotion",
    )

    product_status_ofm = fields.Char(
        string='Product Status OFM',
        translate=True
    )

    qty_invoiced = fields.Float(
        compute='',
        string="Billed Qty",
        digits=dp.get_precision('Product Unit of Measure'),
        store=False
    )
    qty_received = fields.Float(
        compute='',
        string="Received Qty",
        digits=dp.get_precision('Product Unit of Measure'),
        store=False
    )

    move_ids = fields.One2many(
        'stock.move',
        compute='',
        string='Reservation',
        readonly=True,
        store=False,
    )

    invoice_lines = fields.One2many(
        'account.invoice.line',
        compute='',
        string="Bill Lines",
        readonly=True,
        store=False,
    )

    @api.onchange('product_uom')
    def onchange_product_uom_show(self):
        self.product_uom_show = self.product_uom.name

    @api.onchange('price_unit')
    def onchange_price_unit_show(self):
        self.price_unit_show = self.price_unit

    @api.onchange('date_planned')
    def onchange_date_planned_show(self):
        self.date_planned_show = self.date_planned

    @api.onchange('product_qty', 'product_status')
    def onchange_check_qty_with_qty_available(self):
        is_danger = False

        if any([
            all([
                self.product_qty > self.product_qty_available,
                self.product_id.prod_status != u'NonStock'
            ]),
            not self.product_status_correct
        ]):
            is_danger = True

        self.is_danger = is_danger

    @api.onchange('product_id')
    def onchange_set_order_line(self):
        self.update({
            'product_qty_available': 0
        })

    @api.onchange('product_qty', 'price_unit', 'taxes_id')
    def onchange_calculate_amount(self):
        taxes = self.taxes_id.compute_all(
            self.price_unit,
            self.order_id.currency_id,
            self.product_qty,
            product=self.product_id,
            partner=self.order_id.partner_id
        )

        total_included = taxes['total_included']
        total_excluded = taxes['total_excluded']
        price_tax = total_included - total_excluded
        price_total = total_included
        price_subtotal = total_excluded

        self.price_tax = price_tax
        self.price_tax_show = price_tax
        self.price_total = price_total
        self.price_total_show = price_total
        self.price_subtotal = price_subtotal
        self.price_subtotal_show = price_subtotal

    @api.onchange('product_qty')
    def onchange_product_qty_from_manage_product_incorrect(self):
        product_incorrect_id = self._context.get('product_incorrect_id', False)
        ofm_order_line_id = self._context.get('ofm_order_line_id', False)
        if all([
            product_incorrect_id,
            ofm_order_line_id
        ]):
            product_incorrect_edit_qty_id = self.env['purchase.order.product.incorrect.edit.qty.wizard']
            product_incorrect_edit_qty_id = product_incorrect_edit_qty_id.search([
                ('product_incorrect_id', '=', product_incorrect_id),
                ('ofm_order_line_id', '=', ofm_order_line_id)
            ])

            if product_incorrect_edit_qty_id:
                product_incorrect_edit_qty_id.write({
                    'product_qty': self.product_qty,
                })
            else:
                product_incorrect_edit_qty_id.create({
                    'product_incorrect_id': product_incorrect_id,
                    'ofm_order_line_id': ofm_order_line_id,
                    'product_qty': self.product_qty,
                })

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        return False

    def show_notify_product_status_incorrect(self):
        if self.product_id and not self.product_status_correct:
            default_code = self.product_id.default_code if self.product_id.default_code else ''
            message_warning = default_code + ': Product Status Incorrect'

            self.env.user.notify_warning(
                "Warning",
                message_warning,
                False
            )

    def get_readonly_filed_save(self, vals):
        vals = super(PurchaseRequestOrderLineOFM, self).get_readonly_filed_save(vals)

        product_uom = vals.get('product_uom', False)

        if product_uom:
            product_uom = self.env['product.uom'].browse(product_uom).name
            vals.update({
                'product_uom_show': product_uom,
            })

        price_unit = vals.get('price_unit', False)

        if price_unit:
            vals.update({
                'price_unit_show': price_unit,
            })

        date_planned = vals.get('date_planned', False)

        if date_planned:
            vals.update({
                'date_planned_show': date_planned,
            })

        price_subtotal = vals.get('price_subtotal', False)

        if price_subtotal:
            vals.update({
                'price_subtotal_show': price_subtotal,
            })

        price_total = vals.get('price_total', False)

        if price_total:
            vals.update({
                'price_total_show': price_total,
            })

        price_tax = vals.get('price_tax', False)

        if price_tax:
            vals.update({
                'price_tax_show': price_tax,
            })

        return vals
