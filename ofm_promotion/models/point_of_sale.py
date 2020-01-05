# -*- coding: utf-8 -*-

import logging

from odoo import api
from odoo import fields
from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    before_discount = fields.Float(
        string='Before Discount',
        readonly=True,
    )

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)

        res.update({
            'before_discount': ui_order['before_discount'],
        })

        return res

    def _monkey_pad_pos_invoice_line_dict(self, line=False, inv_line=False):
        res = super(PosOrder, self)._monkey_pad_pos_invoice_line_dict(line, inv_line)
        res.update({
            'promotion_id': line.promotion_id.id,
            'promotion_condition_id': line.promotion_condition_id.id,
            'promotion_name': line.promotion_name,
            'promotion': line.promotion,
            'free_product_id': line.free_product_id.id,
            'prorate_amount': line.prorate_amount,
            'reward_type': line.reward_type,
        })
        return res

    def _monkey_pad_filter_order_line(self, order_lines):
        order_lines = super(PosOrder, self)._monkey_pad_filter_order_line(order_lines)
        return [line for line in order_lines if not line.promotion]

    def _monkey_pad_order_compute_price_with_prorate(self, price, qty, prorate_amount=None):
        price = super(PosOrder, self)._monkey_pad_order_compute_price_with_prorate(price, qty, prorate_amount)
        if not prorate_amount:
            return price
        if price * qty < 0:
            prorate_amount = prorate_amount * -1
        price = price - (prorate_amount/qty)
        return price

    def _create_account_move_line(self, session=None, move=None):
        def _flatten_tax_and_children(taxes, group_done=None):
            children = self.env['account.tax']
            if group_done is None:
                group_done = set()
            for tax in taxes.filtered(lambda t: t.amount_type == 'group'):
                if tax.id not in group_done:
                    group_done.add(tax.id)
                    children |= _flatten_tax_and_children(tax.children_tax_ids, group_done)
            return taxes + children

        # Tricky, via the workflow, we only have one id in the ids variable
        """Create a account move line of order grouped by products or not."""
        IrProperty = self.env['ir.property']
        ResPartner = self.env['res.partner']

        if session and not all(session.id == order.session_id.id for order in self):
            raise UserError(_('Selected orders do not have the same session!'))

        grouped_data = {}
        have_to_group_by = session and session.config_id.group_by or False
        rounding_method = session and session.config_id.company_id.tax_calculation_rounding_method

        def add_anglosaxon_lines(grouped_data):
            Product = self.env['product.product']
            Analytic = self.env['account.analytic.account']
            for product_key in list(grouped_data.keys()):
                if product_key[0] == "product":
                    line = grouped_data[product_key][0]
                    product = Product.browse(line['product_id'])
                    # In the SO part, the entries will be inverted by function compute_invoice_totals
                    price_unit = - product._get_anglo_saxon_price_unit()
                    account_analytic = Analytic.browse(line.get('analytic_account_id'))
                    res = Product._anglo_saxon_sale_move_lines(
                        line['name'], product, product.uom_id, line['quantity'], price_unit,
                        fiscal_position=order.fiscal_position_id,
                        account_analytic=account_analytic)
                    if res:
                        line1, line2 = res
                        line1 = Product._convert_prepared_anglosaxon_line(line1, order.partner_id)
                        insert_data('counter_part', {
                            'name': line1['name'],
                            'account_id': line1['account_id'],
                            'credit': line1['credit'] or 0.0,
                            'debit': line1['debit'] or 0.0,
                            'partner_id': line1['partner_id']

                        })

                        line2 = Product._convert_prepared_anglosaxon_line(line2, order.partner_id)
                        insert_data('counter_part', {
                            'name': line2['name'],
                            'account_id': line2['account_id'],
                            'credit': line2['credit'] or 0.0,
                            'debit': line2['debit'] or 0.0,
                            'partner_id': line2['partner_id']
                        })

        for order in self.filtered(lambda o: not o.account_move or o.state == 'paid'):
            current_company = order.sale_journal.company_id
            account_def = IrProperty.get(
                'property_account_receivable_id', 'res.partner')
            order_account = order.partner_id.property_account_receivable_id.id or account_def and account_def.id
            partner_id = ResPartner._find_accounting_partner(order.partner_id).id or False
            if move is None:
                # Create an entry for the sale
                journal_id = self.env['ir.config_parameter'].sudo().get_param(
                    'pos.closing.journal_id_%s' % current_company.id, default=order.sale_journal.id)
                move = self.with_context(branch_id=order.branch_id.id)._create_account_move(
                    order.session_id.start_at, order.name, int(journal_id), order.company_id.id)

            def insert_data(data_type, values):
                # if have_to_group_by:
                values.update({
                    'partner_id': partner_id,
                    'move_id': move.id,
                })

                if data_type == 'product':
                    key = ('product', values['partner_id'],
                           (values['product_id'], tuple(values['tax_ids'][0][2]), values['name']),
                           values['analytic_account_id'], values['debit'] > 0)
                elif data_type == 'tax':
                    key = ('tax', values['partner_id'], values['tax_line_id'], values['debit'] > 0)
                elif data_type == 'counter_part':
                    key = ('counter_part', values['partner_id'], values['account_id'], values['debit'] > 0)
                else:
                    return

                grouped_data.setdefault(key, [])

                if have_to_group_by:
                    if not grouped_data[key]:
                        grouped_data[key].append(values)
                    else:
                        current_value = grouped_data[key][0]
                        current_value['quantity'] = current_value.get('quantity', 0.0) + values.get('quantity', 0.0)
                        current_value['credit'] = current_value.get('credit', 0.0) + values.get('credit', 0.0)
                        current_value['debit'] = current_value.get('debit', 0.0) + values.get('debit', 0.0)
                else:
                    grouped_data[key].append(values)

            # because of the weird way the pos order is written, we need to make sure there is at least one line,
            # because just after the 'for' loop there are references to 'line' and 'income_account' variables (that
            # are set inside the for loop)
            # TOFIX: a deep refactoring of this method (and class!) is needed
            # in order to get rid of this stupid hack
            assert order.lines, _('The POS order must have lines when calling this method')
            # Create an move for each order line
            cur = order.pricelist_id.currency_id

            order_lines = order._monkey_pad_filter_order_line(order.lines)

            for line in order_lines:
                if line.promotion and line.reward_type:
                    continue

                amount = line.price_subtotal

                # Search for the income account
                if line.product_id.property_account_income_id.id:
                    income_account = line.product_id.property_account_income_id.id
                elif line.product_id.categ_id.property_account_income_categ_id.id:
                    income_account = line.product_id.categ_id.property_account_income_categ_id.id
                else:
                    raise UserError(_('Please define income '
                                      'account for this product: "%s" (id:%d).')
                                    % (line.product_id.name, line.product_id.id))

                name = line.product_id.name
                if line.notice:
                    # add discount reason in move
                    name = name + ' (' + line.notice + ')'

                # Create a move for the line for the order line
                # Just like for invoices, a group of taxes must be present on this base line
                # As well as its children
                base_line_tax_ids = _flatten_tax_and_children(line.tax_ids_after_fiscal_position).filtered(lambda tax: tax.type_tax_use in ['sale', 'none'])
                insert_data('product', {
                    'name': name,
                    'quantity': line.qty,
                    'product_id': line.product_id.id,
                    'account_id': income_account,
                    'analytic_account_id': self._prepare_analytic_account(line),
                    'credit': ((amount > 0) and amount) or 0.0,
                    'debit': ((amount < 0) and -amount) or 0.0,
                    'tax_ids': [(6, 0, base_line_tax_ids.ids)],
                    'partner_id': partner_id
                })

                # Create the tax lines
                taxes = line.tax_ids_after_fiscal_position.filtered(lambda t: t.company_id.id == current_company.id)
                if not taxes:
                    continue
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

                if line.prorate_amount:
                    prorate_amount = line.prorate_amount
                    if price * line.qty < 0:
                        prorate_amount = prorate_amount * -1
                    price = price - (prorate_amount/line.qty)

                for tax in taxes.compute_all(price, cur, line.qty)['taxes']:
                    insert_data('tax', {
                        'name': _('Tax') + ' ' + tax['name'],
                        'product_id': line.product_id.id,
                        'quantity': line.qty,
                        'account_id': tax['account_id'] or income_account,
                        'credit': ((tax['amount'] > 0) and tax['amount']) or 0.0,
                        'debit': ((tax['amount'] < 0) and -tax['amount']) or 0.0,
                        'tax_line_id': tax['id'],
                        'partner_id': partner_id
                    })

            # round tax lines per order
            if rounding_method == 'round_globally':
                for group_key, group_value in grouped_data.iteritems():
                    if group_key[0] == 'tax':
                        for line in group_value:
                            line['credit'] = cur.round(line['credit'])
                            line['debit'] = cur.round(line['debit'])

            # counterpart
            insert_data('counter_part', {
                'name': _("Trade Receivables"),  # order.name,
                'account_id': order_account,
                'credit': ((order.amount_total < 0) and -order.amount_total) or 0.0,
                'debit': ((order.amount_total > 0) and order.amount_total) or 0.0,
                'partner_id': partner_id
            })

            if order.change_rounding:
                pos_journal_id = order.session_id.config_id.journal_id

                credit_rounding_account_id = pos_journal_id.default_credit_rounding_account_id or False
                debit_rounding_account_id = pos_journal_id.default_debit_rounding_account_id or False

                if credit_rounding_account_id is False or debit_rounding_account_id is False:
                    raise UserError(_(
                        'Please set Rounding Account of POS Journal')
                    )

                insert_data('counter_part', {
                    'name': _("Trade Rounding"),  # order.name,
                    'account_id': order.session_id.config_id.journal_id.default_credit_rounding_account_id.id,
                    'credit': ((order.change_rounding < 0) and -order.change_rounding) or 0.0,
                    'debit': ((order.change_rounding > 0) and order.change_rounding) or 0.0,
                    'partner_id': partner_id
                })

            order.write({'state': 'done', 'account_move': move.id})

        if self and order.company_id.anglo_saxon_accounting:
            add_anglosaxon_lines(grouped_data)

        all_lines = []
        for group_key, group_data in grouped_data.iteritems():
            for value in group_data:
                all_lines.append((0, 0, value),)
        if move:  # In case no order was changed
            move.sudo().write({'line_ids': all_lines})
            move.sudo().post()
        return True


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

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
        default='discount',
        selection=[
            ('discount', 'Discount'),
            ('product', 'Product'),
            ('coupon', 'Coupon'),
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

    is_type_discount_f_see = fields.Boolean(
        string="Type Discount F'See",
        default=False,
    )

    prorate_ids = fields.One2many(
        comodel_name="pos.promotion.prorate",
        inverse_name="line_id",
        string="Prorate Detail",
        readonly=True,
    )

    def _monkey_pad_orderline_compute_price_with_prorate(self, price, qty, prorate_amount=None):
        price = super(PosOrderLine, self)._monkey_pad_orderline_compute_price_with_prorate(price, qty, prorate_amount)
        if not prorate_amount:
            return price
        if price * qty < 0:
            prorate_amount = prorate_amount * -1
        price = price - (prorate_amount/qty)
        return price