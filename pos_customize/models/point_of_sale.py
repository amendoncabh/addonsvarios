# -*- coding: utf-8 -*-

import logging
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from itertools import chain

from odoo import api
from odoo import fields
from odoo import models
from odoo.exceptions import except_orm, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import float_is_zero
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'
    _order = 'sequence'

    @api.multi
    @api.depends('branch_id', 'branch_id.sequence')
    def _sequence_pos_branch(self):
        for pos_config in self:
            pos_config.update({'sequence': pos_config.branch_id.sequence})

    multi_line = fields.Boolean(
        string="POS Multi-line",
        default=True,
    )

    promotion_discount_product_id = fields.Many2one(
        'product.product',
        string='Promotion Product',
        required=True,
    )

    address = fields.Text(
        'Address'
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string="Branch",
        index=True,
        required=True,
        default=lambda self: self.env.user.branch_id.id,
    )

    cash_limit = fields.Float(
        related='branch_id.cash_limit',
        string='Cash Limit',
        readonly=True,
    )

    pos_company_id = fields.Many2one(
        'res.company',
        string="Company",
        compute='_get_company_to_pos'
    )

    pos_no = fields.Char(
        string="POS ID"
    )

    terminal_no = fields.Char(
        string="Terminal No.",
        required=True,
    )

    product_ids = fields.Many2many(
        'product.product',
        domain=[('available_in_pos', '=', True)]
    )

    is_not_print_invoice = fields.Boolean(
        string="Can't Be Invoice",
        default=False,
        track_visibility='onchange',
    )
    sequence = fields.Integer(
        string="Sequence",
        readonly=True,
        store=True,
        compute='_sequence_pos_branch',
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Picking Type',
        required=True,
    )

    rcpt_no_abb_latest = fields.Integer(
        string='Rcpt ABB No.(Latest)',
        readonly=True
    )

    rcpt_no_abb_round = fields.Integer(
        string='Rcpt ABB No. Round',
        readonly=True,
        default=0,
    )

    @api.model
    def update_rcpt_no_abb(self):
        dict_rcpt_no_abb = {}
        rcpt_no_abb_round = self._context.get('rcpt_no_abb_round', False)
        rcpt_no_abb_latest = self._context.get('rcpt_no_abb_latest', False)
        if rcpt_no_abb_round:
            dict_rcpt_no_abb.update({
                'rcpt_no_abb_round': rcpt_no_abb_round
            })
        if rcpt_no_abb_latest:
            dict_rcpt_no_abb.update({
                'rcpt_no_abb_latest': rcpt_no_abb_latest
            })
        self.env['pos.config'].browse(self._context.get('id')).write(dict_rcpt_no_abb)

    @api.multi
    def _get_company_to_pos(self):
        for item in self:
            item.pos_company_id = item.company_id

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        for pos_order in self:
            if pos_order.branch_id.pos_config_product_template_id:
                template_id = pos_order.branch_id.pos_config_product_template_id.id
                pos_order.update({
                    'pos_product_template_id': template_id,
                })

    @api.multi
    def open_ui(self):

        record = self

        record.current_session_id.write({
            'resume_date': datetime.now()
        })

        return super(PosConfig, self).open_ui()

    @api.model
    def create(self, vals):
        res_id = super(PosConfig, self).create(vals)

        prefix = res_id.sequence_id.prefix

        res_id.sequence_id.write({
            'prefix': prefix + '%(y)s%(month)s',
            'padding': 5,
        })
        return res_id

    @api.multi
    def wizard_open_existing_session_cb_close(self, created_id):
        view = self.env.ref('pos_customize.view_confirm_session_close')
        return {
            'name': 'Confirm Close Session',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'res_model': 'pos.config.confirm.close',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def open_existing_session_cb_close(self):
        assert len(self.ids) == 1, "you can open only one session at a time"
        return self.open_session_cb()

    @api.multi
    def copy(self, default=None):
        raise UserError(_('Duplicating is not supported.'))


class PosOrder(models.Model):
    _name = "pos.order"
    _inherit = ['mail.thread', 'pos.order']

    def satang_rounding(self):
        # self.amount_total = self.calculate_rounding(self.amount_total)[0]
        self.amount_total = self.amount_total - self.change_rounding
    def _monkey_pad_filter_order_line(self, order_lines):
        return order_lines

    def _monkey_pad_filter_order_line(self, order_lines):
        return order_lines

    def calculate_rounding(self, total_amount):
        total_amount_int = int(total_amount)
        diff = total_amount - total_amount_int
        if diff > 0.75:
            amount_total_rounding = total_amount_int + 0.75
        elif 0.75 > diff > 0.50:
            amount_total_rounding = total_amount_int + 0.50
        elif 0.50 > diff > 0.25:
            amount_total_rounding = total_amount_int + 0.25
        elif 0.25 > diff > 0.00: 
            amount_total_rounding = total_amount_int
        else:
            amount_total_rounding = total_amount
        rounding = abs(amount_total_rounding - total_amount)
        return amount_total_rounding, rounding

    @api.depends('amount_tax', 'amount_total', 'amount_paid',
                 'amount_return', 'lines', 'statement_ids', 'lines.discount')
    def _amount_all(self):
        for order in self:
            order_lines = self._monkey_pad_filter_order_line(order.lines)

            order.amount_paid = order.amount_return = order.amount_tax = 0.0
            currency = order.pricelist_id.currency_id
            order.amount_paid = sum(payment.amount for payment in order.statement_ids)
            order.amount_return = sum(payment.amount < 0 and payment.amount or 0 for payment in order.statement_ids)

            order.amount_tax = currency.round(
                sum(
                    self._amount_line_tax(
                        line, order.fiscal_position_id) for line in order_lines
                )
            )
            amount_untaxed = currency.round(sum(line.price_subtotal for line in order_lines))
            order.amount_total = round((order.amount_tax + amount_untaxed), 2)
            order.satang_rounding()

    @api.multi
    def recalculate(self):
        for record in self:
            record._amount_all()
        return True
    
    def _monkey_pad_order_compute_price_with_prorate(self, price, qty, prorate_amount=None):
        return price

    @api.model
    def _amount_line_tax(self, line, fiscal_position_id):
        taxes = line.tax_ids.filtered(lambda t: t.company_id.id == line.order_id.company_id.id)
        if fiscal_position_id:
            taxes = fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)
        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

        price = self._monkey_pad_order_compute_price_with_prorate(price, line.qty, line.prorate_amount)

        taxes = taxes.compute_all(price, line.order_id.pricelist_id.currency_id, line.qty, product=line.product_id,
                                  partner=line.order_id.partner_id or False)['taxes']
        return sum(tax.get('amount', 0.0) for tax in taxes)

    def _compute_branch_id(self):
        self.branch_id = self.session_id.config_id.branch_id

    @api.multi
    def _compute_picking_ids(self):
        for record in self:
            group_id = record.picking_id.group_id
            record.picking_ids = self.env['stock.picking'].search([
                ('group_id', '=', group_id.id)
            ])

    @api.multi
    def _compute_refund(self):
        for record in self:
            record['refund_ids'] = self.env['account.invoice'].search([
                ('pos_id', '=', record.id), ('type', '=', 'out_refund')
            ])

    @api.multi
    def _compute_invoices(self):
        for record in self:
            record['invoice_ids'] = self.env['account.invoice'].search([
                ('pos_id', '=', record.id), ('type', '=', 'out_invoice')
            ])

    @api.multi
    def _compute_show_return(self):
        for record in self:
            if record.session_id.state == 'closed' and not record.check_reverse_all:
                record.require_return = True
            else:
                record.require_return = False

    refund_user_id = fields.Many2one(
        'res.users',
        'Refund User',
        change_default=True,
        readonly=True,
        track_visibility='onchange',
    )

    amount_tax = fields.Float(
        compute="_amount_all",
        string='Taxes',
        track_visibility='onchange',
        digits=0,
        store=True
    )
    amount_total = fields.Float(
        compute="_amount_all",
        string='Total',
        digits=0,
        track_visibility='onchange',
        store=True
    )
    amount_paid = fields.Float(
        compute="_amount_all",
        string='Paid',
        states={
            'draft': [('readonly', False)]
        },
        readonly=True,
        digits=0,
        track_visibility='onchange',
        store=True
    )
    amount_return = fields.Float(
        compute="_amount_all",
        string='Returned',
        digits=0,
        track_visibility='onchange',
        store=True
    )

    check_amount = fields.Boolean(
        string="Check Amount",
        default=False,
        readonly=True,
        track_visibility='onchange',
    )
    is_not_print_invoice = fields.Boolean(
        related='session_id.config_id.is_not_print_invoice',
        string='Phone',
        readonly=True,
        ondelete='restrict'
    )

    is_return_order = fields.Boolean(
        string="Return Order",
        default=False,
        readonly=True,
        track_visibility='onchange',
    )
    tax_invoice = fields.Char(
        string='Tax Invoice',
        readonly=True,
        track_visibility='onchange',
    )

    invoice_id = fields.Many2one(
        comodel_name="account.invoice",
        string="Tax Invoice",
        copy=False,
        required=False,
        readonly=True,
        track_visibility="onchange",
    )

    inv_no = fields.Char(
        string='Receipt no.',
        readonly=True,
        track_visibility='onchange',
    )
    pos_order_log = fields.One2many(
        'customer.change.log',
        'pos_order_id',
        'Pos Log Change',
        track_visibility='onchange',
    )

    date_order = fields.Datetime(
        'Order Date',
        readonly=False,
        select=True,
        track_visibility='onchange',
    )

    shop_no = fields.Char(
        related='partner_id.shop_id',
        readonly=True,
        string="Branch ID",
        track_visibility='onchange',
    )
    company_type = fields.Selection(
        related='partner_id.company_type',
        selection=[
            ('person', 'Individual'),
            ('company', 'Company')
        ],
        readonly=True,
        string='Company Type',
    )
    street = fields.Char(
        string='Address',
        related='partner_id.street',
    )
    street2 = fields.Char(
        string='Road',
        related='partner_id.street2',
    )
    zip = fields.Char(
        related='partner_id.zip',
        string='Zip',
        size=24,
        change_default=True
    )
    city = fields.Char(
        related='partner_id.city',
        string='City'
    )
    state_id = fields.Many2one(
        "res.country.state",
        related='partner_id.state_id',
        string='State',
        ondelete='restrict'
    )
    country_id = fields.Many2one(
        'res.country',
        related='partner_id.country_id',
        string='Country',
        ondelete='restrict'
    )
    vat = fields.Char(
        related='partner_id.vat',
        string='Tax ID',
        ondelete='restrict'
    )
    phone = fields.Char(
        related='partner_id.phone',
        string='Phone',
        ondelete='restrict'
    )
    printed_first = fields.Boolean(
        string='Print First',
        default=False,
        copy=False,
        track_visibility='onchange',
    )
    printed = fields.Boolean(
        string='Have been printed',
        default=False,
        copy=False,
        track_visibility='onchange',
    )

    printed_receipt_first = fields.Boolean(
        string='Print Reciept First',
        default=True,
        copy=False,
        track_visibility='onchange',
    )
    printed_receipt = fields.Boolean(
        string='Have been printed Receipt',
        default=True,
        copy=False,
        track_visibility='onchange',
    )

    state = fields.Selection(
        [
            ('draft', 'New'),
            ('cancel', 'Cancelled'),
            ('paid', 'Paid'),
            ('done', 'Posted'),
            ('invoiced', 'Invoiced')
        ],
        'Status',
        readonly=True,
        copy=False,
        track_visibility='onchange',
    )
    partner_id = fields.Many2one(
        'res.partner',
        'Customer',
        change_default=True,
        select=1,
        states={
            'draft': [('readonly', False)],
            'paid': [('readonly', False)]
        },
        track_visibility='onchange',
    )
    date_order = fields.Datetime(
        'Order Date',
        readonly=True,
        select=True,
        track_visibility='onchange',
    )
    lines = fields.One2many(
        'pos.order.line',
        'order_id',
        'Order Lines',
        states={
            'draft': [('readonly', False)]
        },
        readonly=True,
        copy=True,
        track_visibility='onchange',
    )
    session_id = fields.Many2one(
        index=True
    )
    comment_order = fields.Text(
        string='Comment'
    )
    iface_tax_included = fields.Boolean(
        string='Include Taxes in Prices',
    )
    change_rounding = fields.Float(
        string='Rounding',
        digits=0,
        track_visibility='onchange',
        store=True,
        readonly=True,
    )
    amount_discount = fields.Float(
        # compute="_amount_all",
        string='Discount',
        digits=0,
        track_visibility='onchange',
        store=True
    )
    branch_id = fields.Many2one(
        'pos.branch',
        string="Branch",
        compute='_compute_branch_id',
        store=True,
    )

    picking_ids = fields.One2many(
        'stock.picking',
        string="Stock Picking",
        required=False,
        readonly=True,
        copy=False,
        compute=_compute_picking_ids,
    )

    refund_ids = fields.One2many(
        'account.invoice',
        'pos_id',
        string="Refund Invoices",
        required=False,
        readonly=True,
        copy=False,
        compute=_compute_refund,
    )

    invoice_ids = fields.One2many(
        'account.invoice',
        'pos_id',
        string='Tax Invoices',
        required=False,
        readonly=True,
        copy=False,
        compute=_compute_invoices,
    )

    check_reverse_all = fields.Boolean(
        'Check Reverse All',
        default=False,
        compute='_compute_qty_reverse',
    )

    approve_return = fields.Boolean(
        string="Approve Return",
        default=False,
    )

    session_state = fields.Selection(
        string="Session State",
        selection=[
            ('opening_control', 'Opening Control'),  # method action_pos_session_open
            ('opened', 'In Progress'),               # method action_pos_session_closing_control
            ('closing_control', 'Closing Control'),  # method action_pos_session_close
            ('closed', 'Closed & Posted'),
        ],
        required=False,
        related='session_id.state',
        readonly=True,
    )

    invoice_state = fields.Selection(
        string="Invoice Status",
        required=False,
        related='invoice_id.state',
    )

    before_rounding = fields.Float(
        string='Before Rounding',
        readonly=True,
    )

    total_products_nonvat = fields.Float(
        string='Total Products NonVat',
        readonly=True,
    )

    total_products_vat_included = fields.Float(
        string='Total Products Vat Included',
        readonly=True,
    )

    total_products_vat_excluded = fields.Float(
        string='Total Products Vat Excluded',
        readonly=True,
    )

    total_products_vat_amount = fields.Float(
        string='Total Products Vat Amount',
        readonly=True,
    )

    @api.multi
    def name_get(self):
        return [(r.id, r.inv_no) for r in self]

    @api.model
    def create(self, values):

        if values.get('partner_id'):
            partner_id = self.env['res.partner'].browse(values.get('partner_id'))
            values.update({'pricelist_id': partner_id.property_product_pricelist.id})

        if 'session_id' in values and values.get('session_id'):
            pos_session = self.env['pos.session'].browse(values.get('session_id'))

            if pos_session.past_session:
                date_at_start = datetime.strptime(pos_session.start_at, '%Y-%m-%d %H:%M:%S')
                date_now = datetime.now()
                time_at_now = date_now.strftime('%H:%M:%S')
                time_at_now_time = datetime.strptime(time_at_now, '%H:%M:%S').time()

                time_start_minus = datetime.strptime('17:00:00', '%H:%M:%S').time()
                time_stop_minus = datetime.strptime('23:59:59', '%H:%M:%S').time()

                if time_start_minus <= time_at_now_time <= time_stop_minus:
                    date_at_start = date_at_start - timedelta(hours=36)
                date_at_start = date_at_start.strftime('%Y-%m-%d')
                datetime_pass_session = datetime.strptime(date_at_start + " " + time_at_now, '%Y-%m-%d %H:%M:%S')

                values['date_order'] = datetime_pass_session

        if 'lines' in values and values.get('lines') and 'is_return_order' not in values:
            pos_order_ids = []
            lines_promotion = []
            for line in values.get('lines'):

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
                        line_promotion[2]['qty'],
                        pos_promotion_sum[key]['qty']
                    ])
                    id = pos_promotion_sum[key]['id']
                else:
                    qty = line_promotion[2]['qty']
                    id = line_promotion[2]['id']

                pos_promotion_sum[key] = {
                    u'discount': line_promotion[2]['discount'],
                    u'discount_amount': line_promotion[2]['discount_amount'],
                    u'promotion_condition_id': line_promotion[2].get('promotion_condition_id', False),
                    u'promotion_id': line_promotion[2].get('promotion_id, False'),
                    u'promotion_type': line_promotion[2].get('promotion_type', False),
                    u'reward_type': line_promotion[2].get('reward_type', False),
                    u'prorate_amount': line_promotion[2].get('prorate_amount', False),
                    u'prorate_amount_exclude': line_promotion[2].get('prorate_amount_exclude', False),
                    u'prorate_vat': line_promotion[2].get('prorate_vat', False),
                    u'prorate_amount_2': line_promotion[2].get('prorate_amount_2', 0),
                    u'prorate_amount_exclude_2': line_promotion[2].get('prorate_amount_exclude_2', 0),
                    u'prorate_vat_2': line_promotion[2].get('prorate_vat_2', 0),
                    u'promotion': line_promotion[2].get('promotion', False),
                    u'promotion_name': line_promotion[2].get('promotion_name', False),
                    u'free_product_id': line_promotion[2].get('free_product_id', False),
                    u'id': id,
                    u'price_unit': line_promotion[2].get('price_unit', False),
                    u'product_id': line_promotion[2].get('product_id', False),
                    u'qty': qty,
                    u'iface_line_tax_included': line_promotion[2]['iface_line_tax_included'],
                }
                if line_promotion[2].get('tax_ids', None):
                    pos_promotion_sum[key].update({u'tax_ids': line_promotion[2]['tax_ids'], })

            for pos_promotion_one in pos_promotion_sum:
                pos_order_ids.append([0, 0, pos_promotion_sum[pos_promotion_one]])

            values['lines'] = pos_order_ids

        res_id = super(PosOrder, self).create(values)
        number_next_actual = res_id.session_id.config_id.sequence_id.number_next_actual

        if number_next_actual == 9999:
            res_id.session_id.config_id.sequence_id.write({
                'number_next_actual': 1
            })

        sequence_id = res_id.session_id.config_id.sequence_id

        pos_order_name = sequence_id.with_context({
            'date': res_id.date_order
        })._next()

        res_id.write({
            'name': pos_order_name
        })

        return res_id

    @api.multi
    def write(self, values):
        if not values:
            values = {}

        if 'partner_id' in values:

            user = self.env.user
            group_admin_id = self.env.ref('base.group_system').id
            group_pos_admin_id = self.env.ref('point_of_sale.group_pos_admin').id

            if not values.get('partner_id') \
                    and (group_admin_id not in user.groups_id.ids and group_pos_admin_id not in user.groups_id.ids):
                raise except_orm(_('Error!'), _('Can not remove partner from PoS Order'))

        return super(PosOrder, self).write(values)

    @api.multi
    def action_cancel(self):
        self.ensure_one()
        self.update({
            'state': 'cancel'
        })

    @api.onchange('printed_first', 'printed')
    def onchange_printed_first(self):
        for order in self:
            if order.printed_first:
                order.update({'printed': True})
            else:
                order.update({'printed': False})

    @api.onchange('printed_receipt_first')
    def onchange_printed(self):
        for order in self:
            if order.printed_receipt_first:
                order.update({'printed_receipt': True})
            else:
                order.update({'printed_receipt': False})

    @api.onchange('pricelist_id')
    def onchange_product_id(self):
        for order in self:
            order.lines._onchange_product_id()

    @api.multi
    def action_pos_order_invoice(self):
        for order in self:
            if not order.partner_id:
                raise UserError(_('Please provide a customer.'))

            return super(PosOrder, order).action_pos_order_invoice()

    @api.multi
    def action_warning_create_invoice(self):
        if not self.partner_id:
            raise UserError(_('Please provide a customer.'))
        return {
            'name': _('Are you sure?'),
            'type': 'ir.actions.act_window',
            'res_model': 'confirm.create.invoice.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }

    def _prepare_invoice(self):
        res = super(PosOrder, self)._prepare_invoice()
        res.update({
            'branch_id': self.session_id.config_id.branch_id.id,
            'pos_id': self.id,
            'change_rounding': self.change_rounding,
        })
        return res

    # def customer_refund_create(self):
    #     if not self.partner_id:
    #         raise UserError(
    #             _("Please select customer"))
    #
    #     inv_obj = self.env['account.invoice']
    #     inv_tax_obj = self.env['account.invoice.tax']
    #     inv_line_obj = self.env['account.invoice.line']
    #
    #     for void in self:
    #         ###### Create Account Invoice ######
    #         inv_obj.create({
    #             'state': 'draft',
    #             'partner_id': void.partner_id,
    #             'journal_id': void.sale_journal.id,
    #             'date_invoice': datetime.now,
    #             'parent_invoice_id': void.name,
    #             'team_id': void.env['crm.team']._get_default_team_id(),
    #         })
    #
    #         for product in void.lines:
    #             inv_line_obj.create({
    #                 'product_id': product.product_id,
    #                 'quantity': '',
    #                 'price_unit': '',
    #                 'account_id': '',
    #                 'invoice_line_tax_ids': '',
    #                 'company_id': '',
    #                 'name': '',
    #             })

    def _monkey_pad_pos_invoice_line_dict(self, line=False, inv_line=False):
        return inv_line

    def _action_create_invoice_line(self, line=False, invoice_id=False):
        InvoiceLine = self.env['account.invoice.line']
        inv_name = line.product_id.name_get()[0][1]
        inv_line = {
            'invoice_id': invoice_id,
            'product_id': line.product_id.id,
            'quantity': line.qty,
            'account_analytic_id': self._prepare_analytic_account(line),
            'name': inv_name,
        }
        # Oldlin trick
        invoice_line = InvoiceLine.sudo().new(inv_line)
        invoice_line._onchange_product_id()

        # replace taxes, what order lines have into invoice line,
        if line and line.tax_ids and len(line.tax_ids):
            invoice_line.invoice_line_tax_ids = line.tax_ids

        invoice_line.invoice_line_tax_ids = invoice_line.invoice_line_tax_ids.filtered(lambda t: t.company_id.id == line.order_id.company_id.id).ids
        fiscal_position_id = line.order_id.fiscal_position_id
        if fiscal_position_id:
            invoice_line.invoice_line_tax_ids = fiscal_position_id.map_tax(invoice_line.invoice_line_tax_ids, line.product_id, line.order_id.partner_id)
        invoice_line.invoice_line_tax_ids = invoice_line.invoice_line_tax_ids.ids
        # We convert a new id object back to a dictionary to write to
        # bridge between old and new api
        inv_line = invoice_line._convert_to_write({name: invoice_line[name] for name in invoice_line._cache})
        inv_line.update(price_unit=line.price_unit, discount=line.discount)

        inv_line = self._monkey_pad_pos_invoice_line_dict(line, inv_line)

        return InvoiceLine.sudo().create(inv_line)

    @api.multi
    def refund(self):
        """Create a copy of order  for refund order"""
        clone_list = []
        line_obj = self.env['pos.order.line']
        pos_payment_obj = self.env['pos.make.payment']
        account_payment_obj = self.env['account.bank.statement']
        account_payment_line_obj = self.env['account.bank.statement.line']
        stock_return_picking_obj = self.env['stock.return.picking']
        main_order_state = False

        for order in self:
            # order.customer_refund_create()

            if order.state == 'done':
                main_order_state = order.state
                main_order_move = order.account_move.id

            if order.tax_invoice:
                raise UserError(_('!!! The order have Tax Invoice No already. !!!'))
            if order.is_return_order:
                raise UserError(_('The order is already refunded'))
            order.is_return_order = True
            order.refund_user_id = self.env.user.id

            if order.session_id.state == 'closed':
                raise UserError(_('!!! This session %s is closed !!!' % order.session_id.name))

            clone_id = order.copy({
                'name': order.name + ' REFUND',  # not used, name forced by create
                'picking_id': order.picking_id.id,
            })

            for order_line in clone_id.lines:
                order_line.write({
                    'qty': -order_line.qty
                })

            clone_id._amount_all()

            ctx = self._context.copy()
            ctx.update({
                'active_id': clone_id.id
            })

            order_obj = self.env['pos.order']
            active_id = ctx and ctx.get('active_id', False)
            if active_id:
                order_id = order_obj.browse(active_id)

            account_statement = None
            for statement_id in order.statement_ids:
                account_statement = statement_id.statement_id.id
                statement_id.copy({
                    'amount': statement_id.amount * -1,
                    'pos_statement_id': order_id.id,
                    'statement_id': account_statement,
                    'journal_id': statement_id.journal_id.id
                })

            if order_id.test_paid():
                order_id.write({'state': 'paid'})

            order_id.create_picking()

            clone = clone_id

            for statement_id in clone.statement_ids:
                amount_old = statement_id.amount
                amount = amount_old * -1
                statement_old_ids = account_payment_line_obj.search(([
                    ('pos_statement_id', '=', order.id),
                    ('amount', '=', amount)
                ]))
                if statement_old_ids:
                    for statement_old_id in statement_old_ids:
                        # account_payment_line = account_payment_line_obj.browse(statement_old_ids[0])
                        statement_id.write({
                            'journal_id': statement_old_id.journal_id.id
                        })

            clone.write({
                'check_amount': True,
            })

            if main_order_state:
                ctx = self._context.copy()
                company_id = clone.session_id.config_id.company_id.id
                ctx.update(
                    {'force_company': company_id, 'company_id': company_id}
                )
                self._create_account_move_line(
                    [clone.id],
                    clone.session_id,
                    main_order_move,
                )
            abs = {
                'name': _('Return Products'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'pos.order',
                'res_id': clone.id,
                'view_id': False,
                'context': self._context,
                'type': 'ir.actions.act_window',
                'target': 'current',
            }
            return abs

    @api.multi
    def action_paid(self):
        # if not self.session_id.past_session:
        #     self.write({'date_order': datetime.now()})
        super(PosOrder, self).action_paid()
        return True

    @api.multi
    def action_pos_order_paid(self):
        if not self.test_paid():
            raise UserError(_("Order is not paid."))
        self.write({'state': 'paid'})
        return self.create_picking()

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)

        pos_session_id = self.env['pos.session'].search([
            ('id', '=', ui_order['pos_session_id'])
        ])
        res.update({
            'inv_no': ui_order['inv_no'],
            'iface_tax_included': ui_order['iface_tax_included'],
            'change_rounding': ui_order['change_rounding'],
            'before_rounding': ui_order['before_rounding'],
            'amount_discount': ui_order['amount_discount'],
            'branch_id': pos_session_id.config_id.branch_id.id,
            'amount_total': ui_order['amount_total_rounding'],
            'total_products_nonvat': ui_order['total_products_nonvat'],
            'total_products_vat_included': ui_order['total_products_vat_included'],
            'total_products_vat_excluded': ui_order['total_products_vat_excluded'],
            'total_products_vat_amount': ui_order['total_products_vat_amount'],
        })
        return res

    def test_paid(self):
        """A Point of Sale is paid when the sum
        @return: True
        """
        for order in self:
            if order.lines and not order.amount_total:
                continue
            if (not order.lines) or (not order.statement_ids) or (abs(order.amount_total - order.amount_paid) > 0.01):
                return False
        return True

    def create_picking(self):
        """Create a picking for each order and validate it."""
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        StockWarehouse = self.env['stock.warehouse']
        for order in self:
            if not order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu']):
                continue
            address = order.partner_id.address_get(['delivery']) or {}
            picking_type = order.picking_type_id
            return_pick_type = order.picking_type_id.return_picking_type_id or order.picking_type_id
            order_picking = Picking
            return_picking = Picking
            moves = Move
            location_id = order.location_id.id
            if order.partner_id:
                destination_id = order.partner_id.property_stock_customer.id
            else:
                if (not picking_type) or (not picking_type.default_location_dest_id):
                    customerloc, supplierloc = StockWarehouse._get_partner_locations()
                    destination_id = customerloc.id
                else:
                    destination_id = picking_type.default_location_dest_id.id

            if picking_type:
                group_id = self.env["procurement.group"].create({
                    'name': self.name,
                })
                message = _(
                    "This transfer has been created from the point of sale session: <a href=# data-oe-model=pos.order data-oe-id=%d>%s</a>") % (
                              order.id, order.name)
                picking_vals = {
                    'origin': order.name,
                    'partner_id': address.get('delivery', False),
                    'date_done': order.date_order,
                    'picking_type_id': picking_type.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'note': order.note or "",
                    'branch_id': order.session_id.config_id.branch_id.id,
                    'location_id': location_id,
                    'location_dest_id': destination_id,
                }
                pos_qty = any([x.qty > 0 for x in order.lines if x.product_id.type in ['product', 'consu']])
                if pos_qty:
                    order_picking = Picking.create(picking_vals.copy())
                    order_picking.message_post(body=message)
                neg_qty = any([x.qty < 0 for x in order.lines if x.product_id.type in ['product', 'consu']])
                if neg_qty:
                    return_vals = picking_vals.copy()
                    return_vals.update({
                        'location_id': destination_id,
                        'location_dest_id': return_pick_type != picking_type and return_pick_type.default_location_dest_id.id or location_id,
                        'picking_type_id': return_pick_type.id
                    })
                    return_picking = Picking.create(return_vals)
                    return_picking.message_post(body=message)

            for line in order.lines.filtered(
                    lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty,
                                                                                              precision_rounding=l.product_id.uom_id.rounding)):
                moves |= Move.create({
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': order_picking.id if line.qty >= 0 else return_picking.id,
                    'picking_type_id': picking_type.id if line.qty >= 0 else return_pick_type.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': abs(line.qty),
                    'state': 'draft',
                    'location_id': location_id if line.qty >= 0 else destination_id,
                    'location_dest_id': destination_id if line.qty >= 0 else return_pick_type != picking_type and return_pick_type.default_location_dest_id.id or location_id,
                    'group_id': group_id.id,
                })

            # prefer associating the regular order picking, not the return
            order.write({'picking_id': order_picking.id or return_picking.id})

            if return_picking:
                order._force_picking_done(return_picking)
            if order_picking:
                order._force_picking_done(order_picking)

            # when the pos.config has no picking_type_id set only the moves will be created
            if moves and not return_picking and not order_picking:
                tracked_moves = moves.filtered(lambda move: move.product_id.tracking != 'none')
                untracked_moves = moves - tracked_moves
                tracked_moves.action_confirm()
                untracked_moves.action_assign()
                moves.filtered(lambda m: m.state in ['confirmed', 'waiting']).force_assign()
                moves.filtered(lambda m: m.product_id.tracking == 'none').action_done()

        return True

    def _match_payment_to_invoice(self, order):
        res = super(PosOrder, self)._match_payment_to_invoice(order)
        return res

    @api.multi
    @api.depends('refund_ids', 'picking_ids')
    def _compute_qty_reverse(self):
        for record in self:
            check_reverse_all = False
            product_list = {}
            for picking_id in record.picking_ids:
                if picking_id.origin == record.name:
                    continue

                for pack_operation_product_id in picking_id.pack_operation_product_ids:
                    key = pack_operation_product_id.product_id.id
                    if product_list.get(key, False):
                        product_list[key] += pack_operation_product_id.qty_done
                    else:
                        product_list[key] = pack_operation_product_id.qty_done

            for line in record.lines:
                key = line.product_id.id
                if product_list.get(key, False):
                    product_list[key] -= line.qty
                else:
                    print key

            for key, value in product_list.items():
                print key, value
                if value > 0:
                    check_reverse_all = True

            record.check_reverse_all = check_reverse_all

    @api.multi
    def action_approve_return(self):
        for record in self:
            record.approve_return = True

    @api.model
    def flag_print(self, id):
        pos_order_name = self.env['pos.order'].search([('id', '=', id)])

        pos_order_name.invoice_id.print_time += 1

        if pos_order_name.invoice_id.print_time == 1:
            pos_order_name.invoice_id.is_first_print = False

    @api.multi
    def print_full_tax_invoice_and_cn(self):

        for record in self:
            if record.is_return_order:
                result = record.invoice_id.print_credit_note()
            else:
                result = record.invoice_id.print_full_tax_invoice()

            return result


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    discount_amount = fields.Float(
        'Discount',
        digits=0,
        default=lambda *a: 0.0
    )
    price_subtotal = fields.Float(
        compute="_compute_amount_line_all",
        digits=0,
        string='Subtotal w/o Tax'
    )
    price_subtotal_incl = fields.Float(
        compute="_compute_amount_line_all",
        digits=0,
        string='Subtotal'
    )
    price_subtotal_wo_discount = fields.Float(
        compute="_compute_amount_line_all",
        digits=0,
        string='Subtotal w/o Tax'
    )
    price_subtotal_wo_discount_incl = fields.Float(
        compute="_compute_amount_line_all",
        digits=0,
        string='Subtotal'
    )
    order_id = fields.Many2one(
        'pos.order',
        'Order Ref',
        ondelete='cascade',
        index=True
    )
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        index=True,
    )
    product_id = fields.Many2one(
        index=True,
    )
    iface_line_tax_included = fields.Boolean(
        string='Include Taxes in Order Line',
    )

    @api.model
    def create(self, values):
        print values
        return super(PosOrderLine, self).create(values)

    def _monkey_pad_orderline_compute_price_with_prorate(self, price, qty, prorate_amount=None):
        return price

    @api.depends('price_unit', 'tax_ids', 'qty', 'discount', 'product_id')
    def _compute_amount_line_all(self):
        for line in self:
            fpos = line.order_id.fiscal_position_id
            tax_ids_after_fiscal_position = fpos.map_tax(line.tax_ids, line.product_id,
                                                         line.order_id.partner_id) if fpos else line.tax_ids
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            price = self._monkey_pad_orderline_compute_price_with_prorate(price, line.qty, line.prorate_amount)
            taxes = tax_ids_after_fiscal_position.compute_all(
                price,
                line.order_id.pricelist_id.currency_id,
                line.qty,
                product=line.product_id,
                partner=line.order_id.partner_id
            )
            
            taxes_wo_discount = tax_ids_after_fiscal_position.compute_all(
                line.price_unit,
                line.order_id.pricelist_id.currency_id,
                line.qty,
                product=line.product_id,
                partner=line.order_id.partner_id
            )
            line.update({
                'price_subtotal_incl': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'price_subtotal_wo_discount_incl': taxes_wo_discount['total_included'],
                'price_subtotal_wo_discount': taxes_wo_discount['total_excluded'],
            })

    # @api.onchange('product_id')
    # def onchange_product_id(self):
    #     # print('===== onchange_product_id ====')
    #     if self.order_id:
    #
    #         partner_id = pos_order.partner_id.id or False
    #
    #         qty = self.qty
    #         if pos_order.pricelist_id and self.product_id:
    #
    #             pricelist = pos_order.pricelist_id.id
    #             product_id = self.product_id.id
    #
    #             price_unit = self.env['product.pricelist'].price_get(product_id, qty or 1.0, partner_id)[pricelist]
    #             self.price_unit = price_unit
    #
    #             prod = self.env['product.product'].browse([product_id])
    #             # self.tax_ids = prod.taxes_id.ids
    #             self.tax_ids = [[6, 0, prod.taxes_id.ids]]
    #
    #             self.onchange_qty()

    # @api.onchange('qty', 'price_unit', 'discount', 'discount_amount')
    # def onchange_qty(self):
    #     # print('===== onchange_qty ====')
    #     pos_order = self.order_id
    #
    #     partner_id = pos_order.partner_id.id or False
    #
    #     qty = self.qty
    #
    #     if not pos_order.pricelist_id:
    #         return
    #     pricelist = pos_order.pricelist_id.id
    #
    #     if not self.product_id:
    #         return
    #
    #     product_id = self.product_id.id
    #
    #     # price_unit = self.env['product.pricelist'].price_get(product_id, qty or 1.0, partner_id)[pricelist]
    #     # self.price_unit = price_unit
    #
    #     price_unit = self.price_unit
    #
    #     account_tax_obj = self.env['account.tax']
    #
    #     prod = self.product_id
    #
    #     discount = self.discount
    #     discount_amount = self.discount_amount
    #
    #     price = (price_unit * (1 - (discount or 0.0) / 100.0)) - discount_amount or 0.0
    #     self.price_subtotal = self.price_subtotal_incl = price * qty
    #     cur = self.env['product.pricelist'].browse([pricelist]).currency_id
    #     if (prod.taxes_id):
    #         taxes = prod.taxes_id.compute_all(price, cur, qty, product=prod, partner=False)
    #         self.price_subtotal = taxes['total_excluded']
    #         self.price_subtotal_incl = taxes['total_included']
    #     return

    # @api.depends()
    # @api.multi
    # def _amount_line_all(self):
    #     account_tax_obj = self.env['account.tax']
    #     for line in self:
    #         cur = self.env.ref('pos_customize.trinity_currency')
    #         taxes = [tax for tax in line.tax_ids if tax.company_id.id == line.order_id.company_id.id]
    #         fiscal_position_id = line.order_id.fiscal_position_id
    #         if fiscal_position_id:
    #             taxes = fiscal_position_id.map_tax(taxes)
    #         taxes_ids = [tax.id for tax in taxes]
    #         price = (line.price_unit * (1 - (line.discount or 0.0) / 100.0)) - (line.discount_amount or 0.0)
    #         line.price_subtotal = line.price_subtotal_incl = price * line.qty
    #         if taxes_ids:
    #             taxes = account_tax_obj.browse(taxes_ids).compute_all(price, cur, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
    #             line.price_subtotal = taxes['total_excluded']
    #             line.price_subtotal_incl = taxes['total_included']
    #         line.price_subtotal = cur.round(line.price_subtotal)
    #         line.price_subtotal_incl = cur.round(line.price_subtotal_incl)
    #
    #     return


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.depends()
    @api.multi
    def _product_pricelist(self):

        plobj = self.env['product.pricelist']
        context = self._context
        res = {}
        pricelist_str = ''
        if context is None:
            context = {}
        quantity = context.get('quantity') or 1.0
        pricelist = context.get('pricelist', False)

        partner = context.get('partner', False)
        if pricelist:
            # Support context pricelists specified as display_name or ID for compatibility
            if isinstance(pricelist, basestring):
                pricelist_ids = plobj.name_search(
                    pricelist,
                    operator='=',
                    context=context,
                    limit=1
                )
                pricelist = pricelist_ids[0][0] if pricelist_ids else pricelist

            if isinstance(pricelist, (int, long)):

                products = self

                pl = plobj.browse([pricelist])
                cr = self.env.cr

                date = context.get('date') and context['date'][0:10] or time.strftime(DEFAULT_SERVER_DATE_FORMAT)

                product_uom_obj = self.env['product.uom']

                if not products:
                    return {}

                categ_ids = {}
                for p in products:
                    categ = p.categ_id
                    while categ:
                        categ_ids[categ.id] = True
                        categ = categ.parent_id
                categ_ids = categ_ids.keys()

                is_product_template = products[0]._name == "product.template"
                if is_product_template:
                    prod_tmpl_ids = [tmpl.id for tmpl in products]
                    # all variants of all products
                    prod_ids = [p.id for p in
                                list(chain.from_iterable([t.product_variant_ids for t in products]))]
                else:
                    prod_ids = [product.id for product in products]
                    prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

                cr.execute(
                    'SELECT i.id '
                    'FROM product_pricelist_item AS i '
                    'LEFT JOIN product_category AS c '
                    'ON i.categ_id = c.id '
                    'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = any(%s))'
                    'AND (product_id IS NULL OR product_id = any(%s))'
                    'AND (categ_id IS NULL OR categ_id = any(%s)) '
                    'AND (pricelist_id = %s) '
                    'AND ((i.date_start IS NULL OR i.date_start<=%s) AND (i.date_end IS NULL OR i.date_end>=%s))'
                    'ORDER BY applied_on, min_quantity desc, c.parent_left desc',
                    (prod_tmpl_ids, prod_ids, categ_ids, pricelist, date, date))

                item_ids = [x[0] for x in cr.fetchall()]
                items = self.env['product.pricelist.item'].browse(item_ids)

                if items:
                    items[0].compute_price
                for product in products:
                    for rule in items:

                        if is_product_template:
                            if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                                continue
                            if rule.product_id and not (
                                    product.product_variant_count == 1 and product.product_variant_ids[
                                0].id == rule.product_id.id):
                                # product rule acceptable on template if has only one variant
                                continue
                        else:
                            if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                                continue
                            if rule.product_id and product.id != rule.product_id.id:
                                continue

                        if rule.categ_id:
                            cat = product.categ_id
                            while cat:
                                if cat.id == rule.categ_id.id:
                                    break
                                cat = cat.parent_id
                            if not cat:
                                continue

                        product.pricelist_type = rule.compute_price
                        product.pricelist_percent_price = rule.percent_price
                        break
            return

    # pricelist = fields.Float(_product_pricelist, fnct_inv=_set_product_lst_price, type='float', string='Price', digits_compute=dp.get_precision('Product Price')),
    pricelist_type = fields.Char(compute="_product_pricelist", string='Pricelist Type')
    pricelist_percent_price = fields.Float(compute="_product_pricelist", string='Percentage Price')
    product_tmpl_id = fields.Many2one(
        index=True,
    )


class PosSession(models.Model):
    _name = 'pos.session'
    _inherit = ['pos.session', 'mail.thread']

    POS_SESSION_STATE = [
        ('opening_control', 'Opening Control'),  # Signal open
        ('opened', 'In Progress'),  # Signal closing
        ('closing_control', 'Closing Control'),  # Signal close
        ('closed', 'Closed & Posted'),
    ]

    past_session = fields.Boolean(
        'Past Session',
        default=False,
        track_visibility='onchange'
    )
    start_at = fields.Datetime(
        'Opening Date',
        readonly=False,
        track_visibility='onchange'
    )
    stop_at = fields.Datetime(
        'Closing Date',
        readonly=False,
        track_visibility='onchange'
    )
    resume_date = fields.Datetime(
        'Resume Date',
        readonly=False,
        track_visibility='onchange'
    )
    name = fields.Char(
        'Session ID',
        required=True,
        readonly=True,
        track_visibility='onchange'
    )
    user_id = fields.Many2one(
        'res.users',
        'Responsible',
        required=True,
        select=1,
        readonly=True,
        track_visibility='onchange',
        states={
            'opening_control': [('readonly', False)],
            'opened': [('readonly', False)],
        }
    )
    start_at = fields.Datetime(
        'Opening Date',
        readonly=True,
        track_visibility='onchange'
    )
    stop_at = fields.Datetime(
        'Closing Date',
        readonly=True,
        copy=False,
        track_visibility='onchange'
    )

    state = fields.Selection(
        POS_SESSION_STATE,
        'Status',
        required=True,
        readonly=True,
        select=1,
        copy=False,
        track_visibility='onchange'
    )
    rescue = fields.Boolean(
        'Rescue session',
        readonly=True,
        help="Auto-generated session for orphan orders, ignored in constraints",
        track_visibility='onchange'
    )
    sequence_number = fields.Integer(
        'Order Sequence Number',
        help='A sequence number that is incremented with each order',
        track_visibility='onchange'
    )
    login_number = fields.Integer(
        'Login Sequence Number',
        help='A sequence number that is incremented each time a user resumes the pos session',
        track_visibility='onchange'
    )

    statement_ids = fields.One2many(
        'account.bank.statement',
        'pos_session_id',
        'Bank Statement',
        readonly=True,
        track_visibility='onchange',
    )
    config_id = fields.Many2one(
        index=True
    )
    flag_take_money_out = fields.Boolean(
        string='Flag Take Money Out',
        readonly=True,
        default=False,
    )

    pre_stop_date = fields.Datetime(
        string="",
        required=False,
    )

    @api.model
    def create(self, values):
        if values.get('past_session') == True:
            repeat_session = self.search([
                ('config_id', '=', values.get('config_id')),
                ('state', '!=', 'closed')
            ])
            if repeat_session:
                raise except_orm(_('Error!'), _('!! This session is already use !!'))

        POSSession = super(PosSession, self).create(values)
        if values.get('start_at', False) is False:
            start_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            start_at = values.get('start_at')
        pos_config = self.env['pos.config'].browse(values.get('config_id'))
        POSSession.write({'name': self.get_sequence(pos_config, start_at)})

        return POSSession

    def get_sequence(self, config_id, start_at):
        config_id.branch_id.check_branch_code()
        prefix = config_id.branch_id.branch_code + '%(y)s%(month)s'
        ctx = dict(self._context)
        ctx.update({'res_model': self._name})
        return config_id.branch_id.next_sequence(start_at, prefix, 5) or '/'

    @api.multi
    def action_pos_session_closing_control(self):
        for item in self:
            if item.flag_take_money_out:
                super(PosSession, self).action_pos_session_closing_control()
                item.write({'pre_stop_date': fields.datetime.today()})
            else:
                raise UserError(_('Set Closing Balance before End of Session.'))

    @api.multi
    def print_shift_close_jasper(self):

        for record in self:
            return record.env['report'].get_action(record, 'shift.close.jasper')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hide_in_pos_product_list = fields.Boolean('Hide in Product List',
                                              help='Check if you want to hide this product in the Point of Sale Product List')


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_statement_id = fields.Many2one(
        'pos.order',
        string="POS statement",
        ondelete='cascade',
        index=True,
    )


class AccountBankStmtCashWizard(models.Model):
    _inherit = 'account.bank.statement.cashbox'

    def _get_default_balance_session(self):
        return self._context.get('balance')

    balance_session = fields.Char(
        string='Balance',
        default=_get_default_balance_session,
        readonly=True,
    )

    @api.multi
    def validate(self):
        super(AccountBankStmtCashWizard, self).validate()

        for item in self:
            if item.env.context.get('balance', False) == 'end':
                if item._context.get('active_model') == 'pos.config':
                    active_id = item._context.get('active_id')
                    pos_session = item.env['pos.config'].browse(active_id).current_session_id
                    pos_session.flag_take_money_out = True
                elif item._context.get('active_model') == 'pos.session':
                    active_id = item._context.get('active_id')
                    pos_session = item.env['pos.session'].browse(active_id)
                    pos_session.flag_take_money_out = True

        return True
