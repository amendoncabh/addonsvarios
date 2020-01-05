# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import except_orm


class SOPayments(models.TransientModel):
    _name = "so.payments.wizard"

    def default_customer_type(self):
        return self._context.get('customer_type', False)

    def default_payment_type(self):
        customer_type = self._context.get('customer_type', False)
        active_id = self._context.get('active_id', 0)
        so_id = self.env['sale.order'].browse(active_id)

        type_sale_ofm = False
        if so_id and so_id.type_sale_ofm:
            type_sale_ofm = so_id.type_sale_ofm
            payment_name = 'Deposit'
        else:
            payment_name = 'Cash/ Credit Card'

        domain = [
            ('customer_type', '=', customer_type),
            ('type_sale_ofm', '=', type_sale_ofm),
            ('name', '=', payment_name),
        ]
        payment_type_id = self.env['so.payment.type'].search(domain, order='name DESC', limit=1)

        return payment_type_id.id

    @api.depends('total_amount')
    @api.multi
    def _compute_total_amount(self):
        for record in self:
            record.save_total_amount = record.total_amount

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

    def domain_invoice_credit_note(self):
        domain = [('id', '=', False)]
        if self.env.context.get('active_id', False):
            active_id = self.env.context.get('active_id')
            sale_order_id = self.env['sale.order'].browse(active_id)
            partner_id = sale_order_id.partner_id
            if partner_id.customer_payment_type == 'credit':
                partner_ids = [partner_id.id]
                if partner_id.child_ids:
                    partner_ids += partner_id.child_ids.ids
                domain_invoice = [
                    ('type', '=', 'out_refund'),
                    ('partner_id', 'in', partner_ids),
                    ('state', '=', 'open'),
                    ('so_id.sale_payment_type', '=', 'credit')
                ]
                credit_note_ids = self.env['account.invoice'].search(domain_invoice)
                if credit_note_ids:
                    domain = [('id', 'in', credit_note_ids.ids)]
        return domain

    def default_customer_credit_term_tender_id(self):
        default_id = 0
        if self._context.get('credit_term_tender_id'):
            default_id = self._context.get('credit_term_tender_id')
        return default_id

    @api.model
    def domain_customer_credit_term_tender_id(self):
        domain = [('id', '=', False)]
        if self._context.get('credit_term_tender_id'):
            domain = [
                ('id', '=', self._context.get('credit_term_tender_id')),
            ]
        return domain

    payment_type_id = fields.Many2one(
        comodel_name="so.payment.type",
        string="Payment Type",
        required=True,
        default=default_payment_type,
        index=True,
    )

    advance_amount = fields.Float(
        string="Advance Amount",
        default=0,
    )

    total_amount = fields.Float(
        string="Total Amount",
        default=0,
        readonly=True,
    )

    save_total_amount = fields.Float(
        string="Total Amount",
        default=0,
        compute="_compute_total_amount",
        store=True,
        readonly=False,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
    )

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Payment Methods",
        index=True,
        domain=[('option', '=', False)],
    )

    journal_type = fields.Selection(
        string="Journal type",
        related='journal_id.type',
        selection=[
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('general', 'Miscellaneous'),
        ],
        readonly=True,
        required=False,
    )

    approve_code = fields.Char(
        string='Approve Code',
        size=6,
    )

    tender = fields.Selection(
        string="Tender",
        selection=[
            ('VISA', 'VISA'),
            ('MAST', 'MAST'),
            ('TPNC', 'TPNC'),
            ('JCB', 'JCB'),
            ('KBANK', 'KBANK'),
            ('CUPC', 'CUPC'),
            ('QKBN', 'QKBN'),
        ],
        default='VISA',
    )

    credit_card_no = fields.Char(
        string='Credit Card No.',
        size=16,
    )

    credit_term_card_no = fields.Char(
        string='Cheque/Bank No.',
        size=16,
    )

    credit_term_tender = fields.Many2one(
        comodel_name="account.payment.method.multi",
        string="Payment Methods",
        domain=domain_customer_credit_term_tender_id,
        default=default_customer_credit_term_tender_id,
    )

    is_hide_credit_term_card_no = fields.Boolean(
        string="Hide Credit Term Card no",
        readonly=True,
    )

    is_credit_card = fields.Boolean(
        string="",
        related='journal_id.is_credit_card'
    )

    customer_type = fields.Char(
        string="Customer Type",
        required=False,
        store=False,
        default=default_customer_type,
    )

    is_hide_field_credit_term = fields.Boolean(
        string="Hide Field for Credit Term",
        readonly=True,
        compute='compute_is_hide_field_credit_term'
    )

    type_sale_ofm = fields.Boolean(
        string='Type Sale OFM',
        readonly=True,
    )

    change_rounding = fields.Float(
        string="Rounding",
        required=False,
        default=0.0,
        readonly=True,
    )

    credit_note_ids = fields.Many2many(
        comodel_name='account.invoice',
        string='Deposit',
        domain=domain_invoice_credit_note
    )

    credit_note_amount = fields.Float(
        string='Cn Amount',
        default=0.0,
        compute="_compute_credit_note_amount",
    )

    @api.onchange('credit_note_ids')
    def onchange_credit_note_ids(self):
        if self.type_sale_ofm:
            payment_name = 'Deposit'
        else:
            payment_name = 'Cash/ Credit Card'

        customer_type = self._context.get('customer_type', False)
        active_id = self._context.get('active_id', 0)
        so_id = self.env['sale.order'].browse(active_id)
        aging_balance = so_id.partner_id.aging_balance
        amount_total = 0

        for credit_note_id in self.credit_note_ids:
            amount_total += credit_note_id.amount_total

        remain_amount = self.total_amount - amount_total

        domain = [
            ('customer_type', '=', customer_type),
            ('type_sale_ofm', '=', self.type_sale_ofm),
        ]

        if remain_amount <= aging_balance:
            is_no_credit_balance = False
        else:
            is_no_credit_balance = True

        if any([
            is_no_credit_balance,
            so_id and so_id.sale_payment_type == 'deposit',
        ]):
            domain.append(('name', '=', payment_name))

        return {
            'domain': {
                'payment_type_id': domain
            }
        }

    @api.multi
    @api.depends('credit_note_ids')
    def _compute_credit_note_amount(self):
        for record in self:
            amount_total = 0
            for credit_note_id in record.credit_note_ids:
                amount_total += credit_note_id.amount_total

            if amount_total > record.total_amount:
                msg_error = """
                Don't get Credit Note More Than Sale Total
                """
                raise except_orm(_('Error!'), _(msg_error))

            record.credit_note_amount = amount_total

    @api.onchange('type_sale_ofm')
    def onchange_type_sale_ofm(self):
        customer_type = self._context.get('customer_type', False)
        is_no_credit_balance = self._context.get('is_no_credit_balance', False)
        active_id = self._context.get('active_id', 0)
        so_id = self.env['sale.order'].browse(active_id)

        if self.type_sale_ofm:
            payment_name = 'Deposit'
        else:
            payment_name = 'Cash/ Credit Card'

        domain = [
            ('customer_type', '=', customer_type),
            ('type_sale_ofm', '=', self.type_sale_ofm),
        ]

        if any([
            is_no_credit_balance,
            so_id and so_id.sale_payment_type == 'deposit',
        ]):
            domain.append(('name', '=', payment_name))

        return {
            'domain': {
                'payment_type_id': domain
            }
        }

    @api.multi
    @api.onchange('credit_term_tender')
    def onchange_is_hide_credit_term_card_no(self):
        if self.credit_term_tender.type == 'bank':
            self.is_hide_credit_term_card_no = False
        else:
            self.is_hide_credit_term_card_no = True
        self.credit_term_card_no = False

    @api.onchange('payment_type_id')
    def onchange_payment_type(self):
        self.journal_id = False

    @api.multi
    @api.depends('payment_type_id')
    def compute_is_hide_field_credit_term(self):
        for rec in self:
            if rec.payment_type_id and rec.payment_type_id.name == 'Credit Term':
                rec.is_hide_field_credit_term = True
            else:
                rec.is_hide_field_credit_term = False
                self.credit_term_card_no = None
                self.credit_term_tender = None

    @api.onchange('company_id')
    def onchange_company(self):
        return {
            'domain': {
                'journal_id': [
                    ('journal_user', '=', True),
                    ('type', 'in', ['bank', 'cash']),
                    ('company_id', '=', self.company_id.id),
                    ('option', '=', False),
                ]
            }
        }

    @api.onchange('payment_type_id', 'journal_id', 'advance_amount')
    def onchange_adjust_change_rounding(self):
        if not self.payment_type_id or not self.journal_id or not self.advance_amount:
            self.change_rounding = 0
        elif self.journal_id.type == 'cash':
            amount_total_rounding, rounding = self.calculate_rounding(self.total_amount)
            if any([
                self.advance_amount == 0,
                self.advance_amount >= amount_total_rounding
            ]):
                self.advance_amount = amount_total_rounding
                self.change_rounding = rounding
            else:
                self.change_rounding = 0
        else:
            self.change_rounding = 0

    def get_account_payment_method_multi_id(self):
        account_payment_method_multi_id = self.env['account.payment.method.multi'].search([
            ('journal_id', '=', self.journal_id.id),
        ], limit=1)

        if not account_payment_method_multi_id:
            msg_error = u"Don't Have Payment Method For This Journal"
            raise except_orm(_('Error!'), _(msg_error))

        account_payment_method_multi_id = {
            'payment_method_id': account_payment_method_multi_id.id,
            'paid_total': self.advance_amount,
            'journal_id': self.journal_id.id,
            'approve_code': self.approve_code,
            'tender': self.tender,
            'credit_card_no': self.credit_card_no,
            'is_credit_card': self.is_credit_card,
        }

        return account_payment_method_multi_id

    @api.onchange('is_credit_card')
    def onchange_is_credit_card(self):
        if self.is_credit_card is False:
            self.credit_card_no = None
            self.approve_code = None
            self.tender = None


    def prepare_deposit_line(self, sale_id):
        deposit_line = []
        product_product_obj = self.env['product.product']

        total_amount_product_tax = 0
        total_amount_product_untax = 0

        for order_id in sale_id.order_line:
            if order_id.tax_id:
                total_amount_product_tax += order_id.price_total
            else:
                total_amount_product_untax += order_id.price_total

        if total_amount_product_tax != 0:
            if self.type_sale_ofm:
                product_deposit_name = 'Deposit From Sale'
                msg_error = u"Cash/ Credit no tax line."
            else:
                product_deposit_name = 'Cash/ Credit From Sale'
                msg_error = u"Deposit no tax line."

            product_deposit_id = product_product_obj.search([
                ('name', '=', product_deposit_name)
            ])

            if not product_deposit_id:
                product_deposit_id = product_product_obj.create(
                    product_product_obj.prepare_product_deposit_for_create(product_deposit_name)
                )

            tax_id = product_deposit_id.taxes_id.filtered(
                lambda tax_rec: tax_rec.company_id.id == sale_id.company_id.id
            )

            if not tax_id:
                raise except_orm(_('Error!'), _(msg_error))

            deposit_line.append(
                (
                    0,
                    False,
                    {
                        'name': product_deposit_id.name,
                        'product_id': product_deposit_id.id,
                        'total': total_amount_product_tax,
                        'deposit_line_tax_id': [
                            (6, 0, [tax_id.id])
                        ]
                    }
                )
            )

        if total_amount_product_untax != 0:
            if self.type_sale_ofm:
                product_deposit_name = 'Deposit From Sale Without Tax'
            else:
                product_deposit_name = 'Cash/ Credit From Sale Without Tax'

            product_deposit_without_tax_id = product_product_obj.search([
                ('name', '=', product_deposit_name)
            ])

            if not product_deposit_without_tax_id:
                product_deposit_without_tax_id = product_product_obj.create(
                    product_product_obj.prepare_product_deposit_for_create(product_deposit_name)
                )

            deposit_line.append(
                (
                    0,
                    False,
                    {
                        'name': product_deposit_without_tax_id.name,
                        'product_id': product_deposit_without_tax_id.id,
                        'total': total_amount_product_untax,
                        'deposit_line_tax_id': False
                    }
                )
            )

        return deposit_line

    @api.multi
    def create_deposit(self):
        for rec in self:
            active_id = rec._context.get('active_id', False)

            if active_id:
                sale_id = rec.env['sale.order'].browse(active_id)
                deposit_id = sale_id.deposit_ids.filtered(
                    lambda deposit_id_rec: deposit_id_rec.state == 'draft'
                )

                if not deposit_id:
                    if rec.journal_id:
                        if hasattr(rec.journal_id, 'default_credit_deposit_account_id'):
                            if rec.journal_id.default_credit_deposit_account_id:
                                default_credit_deposit_account_id = rec.journal_id.default_credit_deposit_account_id.id
                            else:
                                raise except_orm(_('Error!'), _(u"No Account Deposit."))
                        else:
                            raise except_orm(_('Error!'), _(u"No Field Account Deposit."))
                    else:
                        raise except_orm(_('Error!'), _(u"No Account Journal."))

                    currency_id = sale_id.currency_id
                    account_deposit_line = rec.prepare_deposit_line(sale_id)
                    account_deposit_obj = rec.env['account.deposit']
                    account_payment_method_multi_id = rec.get_account_payment_method_multi_id()

                    rec.journal_id.id

                    journal_domain = [
                        ('type', '=', 'sale'),
                        ('company_id', '=', sale_id.company_id.id),
                        ('code', 'like', 'SI')
                    ]

                    default_journal_id = self.env[
                        'account.journal'
                    ].search(
                        journal_domain,
                        limit=1
                    )

                    if not default_journal_id:
                        journal_domain = [
                            ('type', '=', 'sale'),
                            ('company_id', '=', self.company_id.id),
                        ]
                        default_journal_id = self.env[
                            'account.journal'
                        ].search(
                            journal_domain,
                            limit=1
                        )

                    deposit_id = account_deposit_obj.create({
                        'sale_id': active_id,
                        'journal_id': default_journal_id.id,
                        'account_id': default_credit_deposit_account_id,
                        'date': fields.Date.today(),
                        'partner_id': sale_id.partner_id.id,
                        'currency_id': currency_id.id,
                        'company_id': sale_id.company_id.id,
                        'branch_id': sale_id.branch_id.id,
                        'type': 'out_deposit',
                        'type_sale_ofm': sale_id.type_sale_ofm,
                        'deposit_line': account_deposit_line,
                        'payment_line': [(0, False, account_payment_method_multi_id)]
                    })

                    for deposit_line_id in deposit_id.deposit_line:
                        deposit_line_id.onchange_product_id_change()
                        deposit_line_id._compute_price()
                else:
                    account_payment_method_multi_id = rec.get_account_payment_method_multi_id()

                    deposit_id.update({
                        'payment_line': [
                            (0, False, account_payment_method_multi_id)
                        ]
                    })

                if self.change_rounding:
                    deposit_id.update({
                        'change_rounding': self.change_rounding,
                    })

                deposit_id.button_compute()
                deposit_id._compute_amount()

                return deposit_id

    @api.multi
    def action_confirm_payment(self):
        ctx = dict(self._context)
        ctx.update({
            'from_action_confirm_payment' : True,
        })
        for rec in self:
            if any([
                rec.advance_amount > rec.total_amount,
                rec.advance_amount < 0
            ]):
                raise except_orm(_('Error!'), _(u"Advance Amount Invalid."))

            is_deposit = False

            if rec.payment_type_id:
                if rec.payment_type_id.name == 'Deposit':
                    is_deposit = True
                    sale_payment_type = 'deposit'
                elif rec.payment_type_id.name == 'Cash/ Credit Card':
                    is_deposit = True
                    sale_payment_type = 'cash'
                elif rec.payment_type_id.name == 'Credit Term':
                    sale_payment_type = 'credit'

            if rec.credit_term_card_no or rec.credit_term_tender:
                sale_credit_term_no = rec.credit_term_card_no
                sale_credit_term_tender = rec.credit_term_tender.id
            else:
                sale_credit_term_no = None
                sale_credit_term_tender = None

            so_id = rec.env['sale.order'].browse(rec._context.get('active_id', 0))

            check_status_product = False
            if so_id:

                if not so_id.sale_payment_type:
                    so_id.update({
                        'sale_payment_type': sale_payment_type,
                        'credit_term_card_no': sale_credit_term_no,
                        'credit_term_tender': sale_credit_term_tender,

                    })

                if so_id.sale_payment_type == 'credit' and rec.credit_note_ids and len(rec.credit_note_ids):
                    so_id.update({
                        'credit_note_ids': [(6, 0, rec.credit_note_ids.ids)]
                    })

                check_status_product = so_id.with_context(ctx).action_confirm_so()
                if check_status_product and so_id.type_sale_ofm:
                    so_id.picking_ids.do_unreserve()

            if all([
                check_status_product,
                is_deposit
            ]):
                deposit_id = rec.create_deposit()

                if rec.advance_amount == rec.total_amount:
                    if self.type_sale_ofm:
                        action = rec.env.ref('tr_account_deposit.tr_action_account_deposit_out').read()[0]
                        action['view_mode'] = 'form'
                        action['views'].pop(0)
                        action['res_id'] = deposit_id.id
                    else:
                        action = rec.env.ref('tr_account_deposit.tr_action_account_cash_credit_out').read()[0]
                        action['view_mode'] = 'form'
                        action['views'].pop(0)
                        action['res_id'] = deposit_id.id

                    return action
                else:
                    return True
            else:
                return True

    @api.model
    def create(self, vals):
        save_total_amount = vals.get('save_total_amount', False)
        advance_amount = vals.get('advance_amount', False)
        if save_total_amount and advance_amount:
            amount_total_rounding, rounding = self.calculate_rounding(save_total_amount)
            if advance_amount == amount_total_rounding:
                vals.update({
                    'change_rounding': rounding,
                })
        return super(SOPayments, self).create(vals)
