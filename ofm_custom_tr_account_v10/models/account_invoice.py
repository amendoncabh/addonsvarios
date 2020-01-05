# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',  # Customer Invoice
    'in_invoice': 'in_refund',  # Vendor Bill
    'out_refund': 'out_invoice',  # Customer Refund
    'in_refund': 'in_invoice',  # Vendor Refund
}

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]

        return self.env['account.journal'].search(domain, order='sequence', limit=1)

    def _default_branch(self):
        return self.env.user.branch_id

    def _default_vendor_reference(self):
        if self._context.get('active_id', False):
            if self._context.get('active_model', False) \
                    and self._context.get('active_model') == 'purchase.order':
                po_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))

                return po_id.vendor_invoice_no

        return ''

    def _default_vendor_date_invoice(self):
        if self._context.get('active_id', False):
            if self._context.get('active_model', False) \
                    and self._context.get('active_model') == 'purchase.order':
                po_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
                if po_id.type_purchase_ofm:
                    return po_id.vendor_invoice_date
                else:
                    return fields.Date.context_today(self)
        else:
            return fields.Date.context_today(self)

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]"
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        default=_default_branch,
    )

    is_first_print = fields.Boolean(
        string="First Print",
        readonly=True,
        default=True,
    )

    print_time = fields.Integer(
        string="",
        required=False,
        default=0,
    )

    is_first_print_dpo = fields.Boolean(
        string="First Print",
        readonly=True,
        default=True,
    )

    print_time_dpo = fields.Integer(
        string="",
        required=False,
        default=0,
    )

    vendor_invoice_date = fields.Date(
        string='Vendor Bill Date',
        default=_default_vendor_date_invoice,
        readonly=True,
    )

    date_invoice = fields.Date(
        default=fields.Date.context_today
    )

    return_reason_id = fields.Many2one(
        comodel_name="return.reason",
        string="Reason",
        required=False,
        readonly=True,
    )
    amount_total = fields.Monetary(
        string='Total',
        store=True,
        readonly=True,
        compute='_compute_amount'
    )

    reference = fields.Char(
        default=_default_vendor_reference
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='stock picking',
        required=False,
        readonly=True,
    )

    type_purchase_ofm = fields.Boolean(
        string='Type Purchase OFM',
        readonly=True,
        default=False
    )

    cancel_from_state = fields.Char(
        string="Cancel from state",
        required=False,
    )

    is_super_user = fields.Boolean(
        string="Is Super User",
        compute="_compute_is_super_user",
        readonly=False,
    )

    hide_action_validate = fields.Boolean(
        string="Hide Action Validate",
        compute="_compute_hide_action_validate",
        readonly=True,
    )

    so_id = fields.Many2one(
        comodel_name="sale.order",
        string="",
        required=False,
    )

    is_delivery_print = fields.Boolean(
        string="Delivery Print",
        readonly=True,
        default=False,
    )

    @api.multi
    def make_first_print(self):
        self.write({
            'is_first_print': True,
            'print_time': 0,
        })

    @api.multi
    def _compute_hide_action_validate(self):
        for rec in self:
            hide_action_validate = True

            if rec.state in ['draft', 'proforma2']:
                hide_action_validate = False

                picking_id = rec.picking_id
                picking_return = False

                if picking_id:
                    picking_return = picking_id.get_picking_type_return()

                if all([
                    rec.type_purchase_ofm,
                    not rec.vendor_cn_reference,
                    picking_return,
                ]):
                    hide_action_validate = True

                if all([
                    rec.type_purchase_ofm,
                    rec.vendor_cn_reference,
                ]):
                    hide_action_validate = False

            rec.hide_action_validate = hide_action_validate

    @api.multi
    def button_dummy(self):
        for record in self:
            record._onchange_invoice_line_ids()
            record._compute_amount()
        return True

    @api.multi
    def print_full_tax_invoice(self):
        is_print_dpo = self._context.get('is_print_dpo', False)

        for record in self:
            if is_print_dpo:
                record.print_time_dpo += 1
                if record.print_time_dpo == 1:
                    record.is_first_print_dpo = False
            else:
                record.print_time += 1

                if all({
                    record.state == 'paid',
                    not record.deposit_ids,
                    not record.pos_id,
                    record.is_delivery_print == True,
                }):
                    record.print_time = 0
                    record.is_first_print = False
                    record.is_delivery_print = False

                if record.print_time == 1:
                    record.is_first_print = False

                if all({
                    record.state != 'paid',
                    not record.deposit_ids,
                    not record.pos_id,
                }):
                    record.is_delivery_print = True

        report_name = 'full.tax.invoice.jasper'

        params = {
            'IDS': ','.join(map(str, self.ids)),
            'is_print_dpo': is_print_dpo,
        }

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': {'records': [], 'parameters': params},
        }

    @api.multi
    def print_credit_note(self):
        for record in self:
            record.print_time += 1

            if record.print_time == 1:
                record.is_first_print = False

            pos_obj = record.env['pos.order'].search([
                ('invoice_id', '=', record.id)
            ])

            report_name = 'credit.note.jasper'
            current_obj = record

            return record.env['report'].get_action(current_obj, report_name)

    @api.model
    def invoice_line_move_line_get(self):

        for invoice_line_id in self.invoice_line_ids:
            if invoice_line_id.quantity == 0:
                raise UserError(_(" Can't Set Quantity 0 in invoice line "))

        def compute_excluded(amount, tax_ids=False):
            if tax_ids and len(tax_ids):
                taxes = tax_ids.with_context({'round': False}).compute_all(
                    amount,
                )
                total_excluded = taxes['total_excluded']
            else:
                total_excluded = amount
            return total_excluded

        res = super(AccountInvoice, self).invoice_line_move_line_get()

        for index, line in enumerate(self.invoice_line_ids):
            prorate_amount = compute_excluded(line.prorate_amount, line.invoice_line_tax_ids)
            amount_subtotal = compute_excluded(line.amount_subtotal, line.invoice_line_tax_ids)

            res[index]['product_cp_cid'] = line.product_id.cp_cid_ofm
            res[index]['promotion_id'] = line.promotion_id.id
            res[index]['promotion_condition_id'] = line.promotion_condition_id.id
            res[index]['promotion_name'] = line.promotion_name
            res[index]['promotion'] = line.promotion

            if line.prorate_amount:
                res[index]['prorate_amount_exclude'] = prorate_amount
                res[index]['prorate_amount_include'] = line.prorate_amount
                res[index]['price'] = amount_subtotal

        return res

    @api.model
    def line_get_convert(self, line, part):
        res = super(AccountInvoice, self).line_get_convert(line, part)
        res['product_cp_cid'] = line.get('product_cp_cid', False)
        return res

    def group_lines(self, iml, line):
        lines = super(AccountInvoice, self).group_lines(iml, line)
        for index, invoice_move in enumerate(iml):
            if 'prorate_amount_exclude' in invoice_move:
                if line[index][2]['debit']:
                    line[index][2]['debit'] -= invoice_move['prorate_amount_exclude']
                else:
                    line[index][2]['credit'] -= invoice_move['prorate_amount_exclude']

        return lines

    def rounding_move_line_get(self, inv):

        res = []

        if inv.type in ['out_refund', 'in_refund']:
            change_rounding = inv.change_rounding * -1
        else:
            change_rounding = inv.change_rounding

        move_line_dict = {
            'type': 'dest',
            'name': 'Rounding',
            'price': change_rounding,
            'account_id': inv.journal_id.default_debit_rounding_account_id.id,
            'date_maturity': inv.date_due,
            'invoice_id': inv.id,
        }

        res.append(move_line_dict)

        return res

    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        total, total_currency, invoice_move_lines = super(
            AccountInvoice, self
        ).compute_invoice_totals(
            company_currency, invoice_move_lines
        )
        total_prorate = 0.000000

        for line in invoice_move_lines:
            if 'prorate_amount_exclude' in line:
                total_prorate += line['prorate_amount_exclude']

        if self.change_rounding:
            if self.type in ['out_refund', 'in_refund']:
                total += self.change_rounding
            else:
                total -= self.change_rounding

        if total < 0:
            total_prorate *= -1
        total -= total_prorate

        if self.currency_id != company_currency:
            currency = self.currency_id.with_context(
                date=self._get_currency_rate_date() or fields.Date.context_today(self))
            total_currency = currency.round(total)
        else:
            total_currency = total

        return total, total_currency, invoice_move_lines

    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """

        def seperate_list_promotion(invoice_move_line):
            temp_list = []
            for index, invoice_move in enumerate(invoice_move_line):
                if invoice_move['promotion'] is True:
                    temp_list.append(invoice_move_line[index])
            for temp_one in temp_list:
                invoice_move_line.remove(temp_one)
            return invoice_move_line

        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()

            iml = seperate_list_promotion(iml)

            # ofm,grouping account move line by cpcid
            newiml = inv.invoice_line_move_line_get()
            newiml = seperate_list_promotion(newiml)
            cpcid_dict = dict()
            ofmimlnonkey = list()
            ofmiml = list()
            for l in newiml:
                key = l.get('product_cp_cid', False)
                if key is False:
                    ofmimlnonkey.append(l)
                    continue
                if key not in cpcid_dict:
                    cpcid_dict[key] = len(ofmiml)
                    if len(l['name'].split(':')) > 1:
                        l['name'] = l['name'].split(':')[0] + ': ' + key
                    else:
                        l['name'] = l['name'].split()[0] + ': ' + key
                    l.pop('price_unit', None)
                    l.pop('product_id', None)
                    l.pop('uom_id', None)
                    ofmiml.append(l)
                else:
                    ofmiml[cpcid_dict[key]]['price'] += l['price']
                    ofmiml[cpcid_dict[key]]['quantity'] += l['quantity']
                    if 'prorate_amount_exclude' in l:
                        if 'prorate_amount_exclude' not in ofmiml[cpcid_dict[key]]:
                            ofmiml[cpcid_dict[key]]['prorate_amount_exclude'] = l['prorate_amount_exclude']
                        else:
                            ofmiml[cpcid_dict[key]]['prorate_amount_exclude'] += l['prorate_amount_exclude']

            ofmiml = ofmimlnonkey + ofmiml
            ofmiml += inv.tax_line_move_line_get()

            # end ofm edited
            iml += inv.tax_line_move_line_get()

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = inv.number

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = \
                    inv.with_context(ctx).payment_term_id.with_context(
                        currency_id=company_currency.id
                    ).compute(
                        total,
                        inv.date_invoice
                    )[0]
                res_amount_currency = total_currency
                ctx['date'] = inv.date or inv.date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    # Check deposit total PS
                    check_deposit_total_ps = inv.monkey_pad_check_deposit_total_ps(
                        inv,
                        total,
                        iml
                    )
                    price = check_deposit_total_ps.get('price')
                    iml = check_deposit_total_ps.get('iml')

                    # get_deposit_adjust_dep_and_price
                    get_deposit_adjust_dep_and_price = inv.monkey_pad_get_deposit_adjust_dep_and_price(
                        inv,
                        price
                    )
                    price = get_deposit_adjust_dep_and_price.get('price')
                    adjust_price = get_deposit_adjust_dep_and_price.get('adjust_price')
                    adjusted_dep = get_deposit_adjust_dep_and_price.get('adjusted_dep')

                    iml.append({
                        'type': 'dest',
                        'name': self.get_move_name(),
                        'price': price,#t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id,
                        'ref': ref,
                    })

                    # add_deposit_decimal_adj_in_iml
                    add_deposit_decimal_adj_in_iml = inv.monkey_pad_add_deposit_decimal_adj_in_iml(
                        inv,
                        price,
                        adjusted_dep,
                        adjust_price,
                        iml
                    )
                    iml = add_deposit_decimal_adj_in_iml.get('iml')
            else:
                # Check deposit total PS
                check_deposit_total_ps = inv.monkey_pad_check_deposit_total_ps(
                    inv,
                    total,
                    iml
                )
                price = check_deposit_total_ps.get('price')
                iml = check_deposit_total_ps.get('iml')

                # get_deposit_adjust_dep_and_price
                get_deposit_adjust_dep_and_price = inv.monkey_pad_get_deposit_adjust_dep_and_price(
                    inv,
                    price
                )
                price = get_deposit_adjust_dep_and_price.get('price')
                adjust_price = get_deposit_adjust_dep_and_price.get('adjust_price')
                adjusted_dep = get_deposit_adjust_dep_and_price.get('adjusted_dep')

                iml.append({
                    'type': 'dest',
                    'name': self.get_move_name(),
                    'price': price,#total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id,
                    'ref': ref,
                })

                #add_deposit_decimal_adj_in_iml
                if self.deposit_ids:
                    add_deposit_decimal_adj_in_iml = inv.monkey_pad_add_deposit_decimal_adj_in_iml(
                        inv,
                        price,
                        adjusted_dep,
                        adjust_price,
                        iml
                    )
                    iml = add_deposit_decimal_adj_in_iml.get('iml')

            ofmtotal, ofmtotal_currency, ofmiml = inv.with_context(ctx).compute_invoice_totals(company_currency, ofmiml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = \
                    inv.with_context(ctx).payment_term_id.with_context(
                        currency_id=company_currency.id
                    ).compute(
                        ofmtotal,
                        inv.date_invoice
                    )[0]
                res_amount_currency = ofmtotal_currency
                ctx['date'] = inv.date or inv.date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(
                            t[1],
                            inv.currency_id
                        )
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    ofmiml.append({
                        'type': 'dest',
                        'name': self.get_move_name(),
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                ofmiml.append({
                    'type': 'dest',
                    'name': self.get_move_name(),
                    'price': ofmtotal,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and ofmtotal_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })

            if inv.change_rounding:
                credit_rounding_account_id = inv.journal_id.default_credit_rounding_account_id or False
                debit_rounding_account_id = inv.journal_id.default_debit_rounding_account_id or False

                if credit_rounding_account_id is False or debit_rounding_account_id is False:
                    raise UserError(_(
                        'Please set Rounding Account of Invoice Journal')
                    )
                iml += inv.rounding_move_line_get(inv)
                ofmiml += inv.rounding_move_line_get(inv)

            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            # self.get_move_desc_line(iml)
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            ofmline = [(0, 0, self.line_get_convert(l, part.id)) for l in ofmiml]
            ofmline = inv.group_lines(ofmiml, ofmline)

            ofmline = inv.finalize_invoice_move_lines(ofmline)

            date = inv.date or inv.date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'line_ofm_ids': ofmline,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
                'branch_id': inv.branch_id.id,
                'company_id': inv.branch_id.pos_company_id.id,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            ctx.update({'invoice_type': inv.type, 'invoice': inv})
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.with_context(ctx).post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
        return True

    @api.onchange('purchase_id')
    def purchase_order_change(self):
        self.branch_id = self.purchase_id.branch_id.id
        super(AccountInvoice, self).purchase_order_change()
        return {}

    @api.onchange('reference')
    def onchange_get_type_purchase_ofm(self):
        order_id = []

        if self.reference:
            order_id = self.env['purchase.order'].search([
                '|',
                '|',
                ('name', '=', self.reference),
                ('purchase_request_no', '=', self.reference),
                ('vendor_invoice_no', '=', self.reference),
            ], limit=1)

        if len(order_id) != 0:
            self.type_purchase_ofm = order_id.type_purchase_ofm
        else:
            self.type_purchase_ofm = False

    @api.model
    def _refund_cleanup_lines(self, lines):
        """ Convert records to dict of values suitable for one2many line creation

            :param recordset lines: records to convert
            :return: list of command tuple for one2many line creation [(0, 0, dict of valueis), ...]
        """
        result = []
        for line in lines:
            values = {}
            for name, field in line._fields.iteritems():
                if name in MAGIC_COLUMNS:
                    continue
                elif field.type == 'many2one':
                    values[name] = line[name].id
                elif field.type not in ['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'invoice_line_tax_ids':
                    values[name] = [(6, 0, line[name].ids)]
            values['origin_inv_line_id'] = line.id
            result.append((0, 0, values))
        return result

    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None, return_reason_id=None):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(invoice, date_invoice=date_invoice, date=date,
                                          description=description, journal_id=journal_id,
                                          return_reason_id=return_reason_id, )
            refund_invoice = self.create(values)
            invoice_type = {'out_invoice': ('customer invoices refund'),
                            'in_invoice': ('vendor bill refund')}
            message = _(
                "This %s has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>") % (
                          invoice_type[invoice.type], invoice.id, invoice.number)
            refund_invoice.message_post(body=message)
            new_invoices += refund_invoice
        return new_invoices

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None,
                        return_reason_id=None):
        """ Prepare the dict of values to create the new refund from the invoice.
            This method may be overridden to implement custom
            refund generation (making sure to call super() to establish
            a clean extension chain).

            :param record invoice: invoice to refund
            :param string date_invoice: refund creation date from the wizard
            :param integer date: force date from the wizard
            :param string description: description of the refund from the wizard
            :param integer journal_id: account.journal from the wizard
            :return: dict of value to create() the refund
        """
        values = {}
        for field in self._get_refund_copy_fields():
            if invoice._fields[field].type == 'many2one':
                values[field] = invoice[field].id
            else:
                values[field] = invoice[field] or False

        values['invoice_line_ids'] = self._refund_cleanup_lines(invoice.invoice_line_ids)

        tax_lines = invoice.tax_line_ids
        values['tax_line_ids'] = self._refund_cleanup_lines(tax_lines)

        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
        elif invoice['type'] == 'in_invoice':
            journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        else:
            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        values['journal_id'] = journal.id

        values['type'] = TYPE2REFUND[invoice['type']]
        values['date_invoice'] = date_invoice or fields.Date.context_today(invoice)
        values['state'] = 'draft'
        values['number'] = False
        values['origin'] = invoice.number
        values['payment_term_id'] = False
        values['refund_invoice_id'] = invoice.id
        values['return_reason_id'] = return_reason_id

        if date:
            values['date'] = date
        if description:
            values['name'] = description
        if invoice.pos_id.id:
            values['pos_id'] = invoice.pos_id.id

        return values

    @api.one
    @api.depends(
        'invoice_line_ids.price_subtotal',
        'tax_line_ids.amount',
        'currency_id',
        'company_id',
        'date_invoice',
        'type',
        'invoice_line_ids.price_subtotal_discount',
        'discount')
    def _compute_amount(self):
        super(AccountInvoice, self)._compute_amount()
        for record in self:
            tax_ids = record.invoice_line_ids.mapped("invoice_line_tax_ids")
            price_include = False
            for tax_id in tax_ids:
                if tax_id.price_include:
                    price_include = True
            if price_include:
                sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
                record.amount_total = sum(line.price_unit * line.quantity for line in record.invoice_line_ids)
                record.amount_untaxed = record.amount_total - record.amount_tax
                record.amount_total_signed = record.amount_total * sign
            if record.change_rounding:
                change_rounding = abs(record.change_rounding)
                if record.type in ['out_refund', 'in_refund']:
                    change_rounding = change_rounding * -1
                record.amount_total -= change_rounding

    @api.one
    @api.constrains('reference','partner_id')
    def _check_unique_reference_partner(self) :
        return True

    @api.multi
    def action_cancel(self):
        for record in self:
            record.cancel_from_state = record.state
        return super(AccountInvoice, self).action_cancel()

    def get_name_invoice(self):
        if self.tax_number and self.cancel_from_state and self.cancel_from_state not in ('draft'):
            return self.tax_number
        return super(AccountInvoice, self).get_name_invoice()

    @api.multi
    def _compute_is_super_user(self):
        for record in self:
            record.is_super_user = (self.env.uid == SUPERUSER_ID)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    branch_id = fields.Many2one(
        'por.branch',
        realated='invoice_id.branch_id',
        string='Branch',
    )

    origin_inv_line_id = fields.Integer(
        string="",
        required=False,
    )

    move_id = fields.Many2one(
        'stock.move',
        string='Stock Move id',
        required = False,
        readonly = True,
    )

    amount_subtotal_w_discount_incl = fields.Monetary(
        string="Amt Subtotal with Discount",
        store=True,
        readonly=True,
        compute='_compute_price'
    )

    amount_subtotal_w_discount = fields.Monetary(
        string="Amt Subtotal with Discount without vat",
        store=True,
        readonly=True,
        compute='_compute_price'
    )

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
        'invoice_id.date_invoice','discount2')
    def _compute_price(self):
        super(AccountInvoiceLine, self)._compute_price()
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = (self.price_unit * (1 - (self.discount or 0.0) / 100.0))
        if self.quantity:
            price = price - (self.discount2/self.quantity) - (self.prorate_amount/self.quantity)
        else:
            price = price

        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(
                price,
                currency,
                self.quantity,
                product=self.product_id,
                partner=self.invoice_id.partner_id
            )
        if taxes:
            self.amount_subtotal_w_discount = taxes['total_excluded']
        else:
            self.amount_subtotal_w_discount = (self.quantity * price) - self.discount2 - self.prorate_amount
        self.amount_subtotal_w_discount_incl = (self.quantity * price) - self.discount2 - self.prorate_amount


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.multi
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        """ Returns all information required to apply taxes (in self + their children in case of a tax goup).
            We consider the sequence of the parent for group of taxes.
                Eg. considering letters as taxes and alphabetic order as sequence :
                [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]

        RETURN: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'taxes': [{               # One dict for each tax in self and their children
                'id': int,
                'name': str,
                'amount': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': boolean,
            }]
        } """
        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id

        if isinstance(company_id, int):
            company_id = self.env['res.company'].browse(company_id)

        if not currency:
            currency = company_id.currency_id
        taxes = []
        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        # prec = currency.decimal_places
        prec = 9
        # In some cases, it is necessary to force/prevent the rounding of the tax and the total
        # amounts. For example, in SO/PO line, we don't want to round the price unit at the
        # precision of the currency.
        # The context key 'round' allows to force the standard behavior.
        round_tax = False if company_id.tax_calculation_rounding_method == 'round_globally' else True
        round_total = True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])
            round_total = bool(self.env.context['round'])

        if not round_tax:
            prec += 5

        base_values = self.env.context.get('base_values')
        if not base_values:
            total_excluded = total_included = base = round(price_unit * quantity, prec)
        else:
            total_excluded, total_included, base = base_values

        # Sorting key is mandatory in this case. When no key is provided, sorted() will perform a
        # search. However, the search method is overridden in account.tax in order to add a domain
        # depending on the context. This domain might filter out some taxes from self, e.g. in the
        # case of group taxes.
        for tax in self.sorted(key=lambda r: r.sequence):
            if tax.amount_type == 'group':
                children = tax.children_tax_ids.with_context(base_values=(total_excluded, total_included, base))
                ret = children.compute_all(price_unit, currency, quantity, product, partner)
                total_excluded = ret['total_excluded']
                base = ret['base'] if tax.include_base_amount else base
                total_included = ret['total_included']
                tax_amount = total_included - total_excluded
                taxes += ret['taxes']
                continue

            compute_tax_base = tax._compute_amount(base, price_unit, quantity, product, partner)
            tax_amount = currency.round(compute_tax_base)
            if not round_tax:
                tax_amount = round(tax_amount, prec)
            else:
                tax_amount = currency.round(tax_amount)
            if tax.price_include:
                total_excluded -= tax_amount
                base -= tax_amount
            else:
                total_included += tax_amount

            # Keep base amount used for the current tax
            tax_base = base

            if tax.include_base_amount:
                base += tax_amount

            taxes.append({
                'id': tax.id,
                'name': tax.with_context(**{'lang': partner.lang} if partner else {}).name,
                'amount': tax_amount,
                'base': tax_base,
                'sequence': tax.sequence,
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
                'analytic': tax.analytic,
            })

        return {
            'taxes': sorted(taxes, key=lambda k: k['sequence']),
            'total_excluded': currency.round(total_excluded) if round_total else total_excluded,
            'total_included': currency.round(total_included) if round_total else total_included,
            'base': base,
        }


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    @api.model
    def create(self, vals):
        company_id = False
        if all([
            'company_id' in vals,
            vals.get('company_id', False)
        ]):
            company_id = vals.get('company_id', False)

            if isinstance(company_id, int):
                company_id = self.env['res.company'].browse(company_id)

            if company_id.tax_calculation_rounding_method == 'round_globally':
                company_id.tax_calculation_rounding_method = 'round_per_line'
            else:
                company_id = False

        inv_tax = super(AccountInvoiceTax, self).create(vals)
        if company_id:
            inv_tax.company_id.tax_calculation_rounding_method = 'round_globally'

        return inv_tax
