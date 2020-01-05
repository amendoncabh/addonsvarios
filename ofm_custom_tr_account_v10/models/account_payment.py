# coding: utf-8

from datetime import datetime
from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError, UserError

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}

MAP_TYPE_PAYMENT_SIGN = {
    'inbound': -1,
    'outbound': 1,
}


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def print_form_receive_payment_report(self):
        report_name = 'receive.payment.jasper'
        return self.env['report'].get_action(self, report_name)

    @api.multi
    @api.depends('branch_id')
    def _get_company_id(self):
        for record in self:
            record.company_id = record.branch_id.pos_company_id

    def _default_branch(self):
        branch_id = self._context.get('branch_id', False)
        if branch_id:
            return branch_id
        return self.env.user.branch_id.id

    def _default_journal_id(self):
        payment_type = self._context.get('default_payment_type', False)
        default_domain = [
            ('company_id', '=', self.env.user.company_id.id),
            ('type', 'in', ['cash', 'bank'])
        ]

        if payment_type == 'inbound':
            type_payment_to_customer = self._context.get(
                'default_type_payment_to_customer'
                , False
            )

            if type_payment_to_customer:
                if type_payment_to_customer == 'inbound':
                    default_domain += [
                        ('code', '=', 'RV'),
                        ('option', '=', 'sale'),
                    ]

                elif type_payment_to_customer == 'outbound':
                    default_domain += [
                        ('code', '=', 'PV'),
                        ('option', '=', 'purchase'),
                    ]

                else:
                    default_domain += [('option', '=', 'sale')]

        else:
            default_domain += [('option', '=', 'purchase')]

        journal_ids = self.env['account.journal'].search(
            default_domain,
            limit=1
        )

        if journal_ids:
            return journal_ids.id
        return None

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        require=True,
        readonly=True,
        default=_default_branch,
    )

    company_id = fields.Many2one(
        'res.company',
        related='',
        string='Company',
        compute='_get_company_id',
        store=True,
    )

    name = fields.Char(
        readonly=True,
        copy=False,
        default="Payment Draft"
    )

    journal_id = fields.Many2one(
        default=_default_journal_id,
        domain=[
            ('type', 'in', ['cash', 'bank']),
            ('option', '!=', False)
        ],
    )

    type_payment_to_customer = fields.Selection(
        selection=[
            ('outbound', 'Send Money'),
            ('inbound', 'Receive Money')
        ],
        string='Payment Type'
    )

    invoice_total = fields.Monetary(
        string='Amount Invoice',
        track_visibility='always',
        store=True,
    )

    wht_total = fields.Monetary(
        string='WHT Total',
        store=True,
    )

    write_off = fields.Monetary(
        string='Write Off',
        track_visibility='always',
        default=0.0,
    )

    write_off_show = fields.Monetary(
        related='write_off',
        readonly=True,
    )

    amount_show = fields.Monetary(
        string="Total Payment",
    )

    total_payment = fields.Monetary(
        string='Payment Amount',
        readonly=False,
        default=0.0,
    )

    total_payment_show = fields.Monetary(
        string='Payment Amount',
        related='total_payment',
        readonly=True,
        default=0.0,
    )

    @api.onchange('invoice_line', 'payment_line', 'invoice_line.paid_amount', 'payment_line.paid_total', 'write_off')
    def onchange_compute_invoice(self):
        for record in self:
            write_off = 0
            total_payment = 0
            for payment in record.payment_line:
                if payment.payment_method_id.type == 'writeoff':
                    write_off += payment.paid_total
                else:
                    total_payment += payment.paid_total

            amount = total_payment + write_off

            invoice_line = record.invoice_line.filtered(
                lambda invoice_rec: invoice_rec.is_check_full
            )

            invoice_total = sum(line.paid_amount for line in invoice_line)
            wht_total = sum(line.paid_total for line in record.payment_line if line.wht_id)

            record.update({
                'write_off': write_off,
                'total_payment': total_payment,
                'amount': amount,
                'invoice_total': invoice_total,
                'wht_total': wht_total
            })


    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        # Set partner_id domain
        if self.partner_type:
            return {'domain': {'partner_id': [('parent_id', '=', False), (self.partner_type, '=', True),
                                              ('customer_payment_type', '=', 'credit')]}}

    @api.onchange('partner_id', 'branch_id')
    def _onchange_partner_id(self):
        res = {}
        if self.partner_id:
            partners = self.partner_id | self.partner_id.commercial_partner_id | self.partner_id.commercial_partner_id.child_ids
            partner_ids = partners.ids
            for partner in partners:
                if len(partner.child_ids):
                    partner_ids = partner_ids + partner.child_ids.ids

            res['domain'] = {'payment_token_id': [
                ('partner_id', 'in', partner_ids),
                ('acquirer_id.auto_confirm', '!=', 'authorize')
            ]}

        return res

    @api.onchange('partner_id', 'payment_type', 'currency_id', 'branch_id')
    def _onchange_partner(self):
        update_value = super(AccountPayment, self)._onchange_partner()

        invoice_of_sale_refund = [
            'out_refund'
        ]

        invoice_of_sale_receive = [
            'out_invoice'
        ]

        invoice_of_purchase = [
            'in_invoice',
            'in_refund'
        ]

        if self.payment_type == 'inbound':
            if self.type_payment_to_customer == 'inbound':
                type_invoice = invoice_of_sale_receive
            else:
                type_invoice = invoice_of_sale_refund
        else:
            type_invoice = invoice_of_purchase

        account_invoice = self.env['account.invoice']
        if self.partner_id:
            partners = self.partner_id | self.partner_id.commercial_partner_id | self.partner_id.commercial_partner_id.child_ids
            partner_ids = partners.ids
            for partner in partners:
                if len(partner.child_ids):
                    partner_ids = partner_ids + partner.child_ids.ids

            invoice_line = account_invoice.search([
                ('partner_id', 'in', partner_ids),
                ('state', 'in', ['open']),
                ('type', 'in', type_invoice),
                ('branch_id', '=', self.branch_id.id)
            ])
            val = self.get_payment_line(invoice_line)

            update_value.update({
                'value': {
                    'invoice_line': val
                }
            })

            return update_value

    def get_payment_line(self, invoice_line):
        val = []
        for invoice in invoice_line:
            # if self.currency_id != invoice.currency_id:
            currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(self))
            currency_residual = currency.compute(invoice.residual, self.company_id.currency_id)
            balance = self.currency_id == invoice.currency_id and invoice.residual or currency_residual
            balance -= invoice.credit_amt

            if 'refund' in invoice.type:
                balance *= -1

            if self.currency_id == invoice.currency_id:
                val.append({
                    'invoice_id': invoice.id,
                    'dute_date': invoice.date_due,
                    'amount': invoice.amount_total,
                    'wht_total': invoice.amount_wht,
                    'balance': balance,
                    'currency_id': invoice.currency_id,
                })
            elif self.currency_id == self.company_id.currency_id:
                val.append({
                    'invoice_id': invoice.id,
                    'dute_date': invoice.date_due,
                    'amount': invoice.amount_total,
                    'wht_total': invoice.amount_wht,
                    'balance': balance,
                    'currency_id': invoice.currency_id,
                })

        return val

    def generate_payment_no(self, branch_id, date_order):
        ctx = dict(self._context)

        if self.payment_type == 'outbound':
            prefix = 'PV-'
        else:
            prefix = 'RV-'

        ctx.update({'res_model': self._name})

        prefix = prefix + branch_id.branch_code + '%(y)s%(month)s'
        so_no = branch_id.with_context(ctx).next_sequence(date_order, prefix, 5) or '/'

        return so_no

    def check_suspend_tax_ref(self):
        super(AccountPayment, self).check_suspend_tax_ref()
        if self.name == "Payment Draft":
            name = self.generate_payment_no(
                self.branch_id,
                self.payment_date
            )
        return name

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        res = super(AccountPayment, self)._onchange_payment_type()
        res['domain']['journal_id'].append(('option', '!=', False))
        return res

    @api.multi
    def prepost(self):
        for record in self:
            branch_id = record.branch_id.id
            if record.type_payment_to_customer == 'inbound':
                if record.amount_show < record.invoice_total:
                    raise ValidationError(_('Error!\nThe paid amount over balance.'))
            else:
                if record.amount_show > record.invoice_total:
                    raise ValidationError(_('Error!\nThe paid amount over balance.'))

            if record.invoice_total < 0:
                view = self.env.ref('ofm_custom_tr_account_v10.view_receive_payment_approval_form')
                return {
                    'name': 'Validate Refund',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'views': [(view.id, 'form')],
                    'res_model': 'receive.payment.approval',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }
            if record.invoice_total > 0:
                record.with_context(branch_id=branch_id).post()

    def check_amount_invoice_total(self):
        is_over_balance = False

        if self.type_payment_to_customer == 'outbound' and self.invoice_total >= 0:
            is_over_balance = True
        elif self.type_payment_to_customer == 'inbound' and self.invoice_total <= 0:
            is_over_balance = True

        if is_over_balance:
            raise ValidationError(_('Error!\nThe paid amount over balance.'))

    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        self.check_amount_invoice_total()

        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = False
        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            # if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = self.invoice_ids[0].currency_id
        debit, credit, amount_currency, currency_id = aml_obj.with_context(
            date=self.payment_date
        ).compute_amount_fields(
            amount,
            self.currency_id,
            self.company_id.currency_id,
            invoice_currency
        )
        move_vals = self._get_move_vals()
        move = self.env['account.move'].create(move_vals)

        # if self.amount != self.invoice_total :
        #     raise ValidationError(_('Error!\nPlease Check payment line Payment Amount is not  equat Amount Invoice.'))
        # search invoice is not paid amount = 0
        invoice_ids = self.env['account.invoice.payment.line'].search(
            [('payment_id', '=', self.id), ('paid_amount', '=', 0)])
        for inv in invoice_ids:
            inv.unlink()
        # Write line corresponding to invoice payment
        for invoice in self.invoice_line:
            if (invoice.paid_amount - invoice.balance) > 0.01:
                raise ValidationError(_('Error!\nThe paid amount over balance.'))

            if invoice.credit_amt > 0:
                self.reconcile_credit_note(invoice.invoice_id)

            paid_amt = (invoice.paid_amount * MAP_TYPE_PAYMENT_SIGN[self.payment_type])
            debit, credit, amount_currency, currency_id = aml_obj.with_context(
                date=self.payment_date
            ).compute_amount_fields(
                paid_amt,
                self.currency_id,
                self.company_id.currency_id,
                invoice_currency
            )
            counterpart_aml_dict = self._get_shared_move_line_vals(
                tools.float_round(debit, precision_rounding=0.01),
                tools.float_round(credit, precision_rounding=0.01),
                amount_currency,
                move.id,
                invoice.invoice_id
            )
            counterpart_aml_dict.update(self._get_counterpart_move_line_vals(invoice.invoice_id))
            counterpart_aml_dict.update({'currency_id': currency_id})
            counterpart_aml = aml_obj.create(counterpart_aml_dict)
            # check_invoice_suspend = self.get_invoice_suspend(invoice_id=invoice.invoice_id.id)

        # Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(
                date=self.payment_date).compute_amount_fields(self.payment_difference, self.currency_id,
                                                              self.company_id.currency_id, invoice_currency)
            writeoff_line['name'] = _('Counterpart')
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit']:
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit']:
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo
        self.invoice_ids.register_payment(counterpart_aml)

        # Write counterpart lines
        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        for payment in self.payment_line:
            payment_total = (payment.paid_total * MAP_TYPE_PAYMENT_SIGN[self.payment_type])
            debit, credit, amount_currency, currency_id = aml_obj.with_context(
                date=self.payment_date
            ).compute_amount_fields(
                payment_total,
                self.currency_id,
                self.company_id.currency_id,
                invoice_currency
            )
            liquidity_aml_dict = self._get_shared_move_line_vals(
                credit,
                debit,
                -amount_currency,
                move.id,
                False
            )

            # account_id = payment.payment_method_id.account_id.id
            # if payment.payment_method_id.account_id.id
            liquidity_aml_dict.update(
                self._get_liquidity_move_line_vals_multi(
                    payment,
                    payment_total
                )
            )
            aml_obj.create(liquidity_aml_dict)

        self.check_suspend_vat(move_id=move)
        self.move_id = move
        # Reconclie by line in payment
        for line in move.line_ids:
            if line.invoice_id:
                line.invoice_id.register_payment(line)

        ctx = dict(self._context)
        if self.type_payment_to_customer:
            ctx.update({
                'type_payment_to_customer': self.type_payment_to_customer
            })


        move.with_context(ctx).post()
        return move

    def check_suspend_tax_ref(self):
        super(AccountPayment, self).check_suspend_tax_ref()
        name = 'Draft'
        return name

    @api.multi
    def write(self, vals):
        res = super(AccountPayment, self).write(vals)
        print res
        return res

    def create_payment_from_account_invoice(self, inv):
        invoice_type = inv.type
        journal_domain = [('company_id', '=', inv.company_id.id)]
        type_payment_to_customer = ''

        if invoice_type in ('out_invoice', 'out_refund'):
            # sale invoice, sale refund
            if invoice_type == 'out_invoice':
                type_payment_to_customer = 'inbound'
                journal_domain.append(('option', '=', 'sale'))
                journal_domain.append(('code', '=', 'RV'))
            elif invoice_type == 'out_refund':
                type_payment_to_customer = 'outbound'
                journal_domain.append(('option', '=', 'purchase'))
                journal_domain.append(('code', '=', 'PV'))
            payment_type = 'inbound'
            partner_type = 'customer'
        elif invoice_type in ('in_invoice', 'in_refund'):
            # purchase invoice, purchase refund
            journal_domain.append(('option', '=', 'purchase'))
            journal_domain.append(('code', '=', 'PV'))

            payment_type = 'outbound'
            partner_type = 'supplier'
        else:
            return False

        journal_id = self.env['account.journal'].search(journal_domain)

        residual = inv.residual if invoice_type in ('out_invoice', 'in_invoice') else inv.residual * -1

        prepare_payment_invoice_line = [
            (
                0, 0,
                {
                    'invoice_id': inv.id,
                    'amount': residual,
                    'is_check_full': True,
                    'balance': residual,
                    'paid_amount': residual,
                    'paid_amount_show': residual,
                }
            )
        ]

        account_payment_method_id = self.env['account.payment.method'].search(
            [
                ('payment_type', '=', payment_type),
                ('code', '=', 'manual'),
            ]
        )

        account_payment_id = self.with_context(
            force_company=inv.company_id.id
        ).create({
            'name': 'Payment Draft',
            'partner_type': partner_type,
            'payment_type': payment_type,
            'type_payment_to_customer': type_payment_to_customer,
            'payment_date': datetime.now().strftime("%Y-%m-%d"),
            'company_id': inv.company_id.id,
            'journal_id': journal_id.id,
            'branch_id': inv.branch_id.id,
            'amount': 0,
            'invoice_total': residual,
            'payment_method_id': account_payment_method_id.id,
        })

        account_payment_id.write({
            'partner_id': inv.partner_id.id,
            'invoice_line': prepare_payment_invoice_line,
        })

        return account_payment_id

    # def _create_payment_entry(self, amount):
    #     """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
    #         Return the journal entry.
    #     """
    #
    #     aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
    #     invoice_currency = False
    #     if self.invoice_ids and all(
    #             [
    #                 x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids
    #             ]
    #     ):
    #         # if all the invoices selected share the same currency, record the paiement in that currency too
    #         invoice_currency = self.invoice_ids[0].currency_id
    #     debit, credit, amount_currency, currency_id = aml_obj.with_context(
    #         date=self.payment_date
    #     ).compute_amount_fields(
    #         amount,
    #         self.currency_id,
    #         self.company_id.currency_id,
    #         invoice_currency
    #     )
    #     move_vals = self._get_move_vals()
    #     move = self.env['account.move'].with_context(
    #         branch_id=self.branch_id
    #     ).create(
    #         move_vals
    #     )
    #
    #     # Write line corresponding to invoice payment
    #     for invoice in self.invoice_line:
    #         if (invoice.paid_amount - invoice.balance) > 0.01:
    #             raise ValidationError(_('Error!\nThe paid amount over balance.'))
    #
    #         if invoice.credit_amt > 0:
    #             self.reconcile_credit_note(invoice.invoice_id)
    #
    #         paid_amt = (invoice.paid_amount * MAP_TYPE_PAYMENT_SIGN[self.payment_type])
    #         debit, credit, amount_currency, currency_id = aml_obj.with_context(
    #             date=self.payment_date
    #         ).compute_amount_fields(
    #             paid_amt,
    #             self.currency_id,
    #             self.company_id.currency_id,
    #             invoice_currency
    #         )
    #         counterpart_aml_dict = self._get_shared_move_line_vals(
    #             debit,
    #             credit,
    #             amount_currency,
    #             move.id,
    #             invoice.invoice_id
    #         )
    #         counterpart_aml_dict.update(
    #             self._get_counterpart_move_line_vals(
    #                 invoice.invoice_id
    #             )
    #         )
    #         counterpart_aml_dict.update({
    #             'currency_id': currency_id
    #         })
    #         counterpart_aml = aml_obj.create(
    #             counterpart_aml_dict
    #         )
    #         # check_invoice_suspend = self.get_invoice_suspend(invoice_id=invoice.invoice_id.id)
    #     for invoice in self.invoice_line:
    #         for child_id in invoice.invoice_id.child_ids:
    #             child_paid_amt = (
    #                     child_id.amount_total * MAP_TYPE_PAYMENT_SIGN[self.payment_type]
    #             )
    #             debit, credit, amount_currency, currency_id = aml_obj.with_context(
    #                 date=self.payment_date
    #             ).compute_amount_fields(
    #                 child_paid_amt,
    #                 self.currency_id,
    #                 self.company_id.currency_id,
    #                 invoice_currency
    #             )
    #             child_counterpart_aml_dict = self._get_shared_move_line_vals(
    #                 credit,
    #                 debit,
    #                 -amount_currency,
    #                 move.id,
    #                 child_id
    #             )
    #             child_counterpart_aml_dict.update(
    #                 self._get_counterpart_move_line_vals(
    #                     child_id
    #                 )
    #             )
    #             child_counterpart_aml_dict.update({
    #                 'currency_id': currency_id
    #             })
    #             child_counterpart_aml = aml_obj.create(
    #                 counterpart_aml_dict
    #             )
    #
    #     # Reconcile with the invoices
    #     if self.payment_difference_handling == 'reconcile' and self.payment_difference:
    #         writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
    #         debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(
    #             date=self.payment_date
    #         ).compute_amount_fields(
    #             self.payment_difference,
    #             self.currency_id,
    #             self.company_id.currency_id,
    #             invoice_currency
    #         )
    #         writeoff_line['name'] = _('Counterpart')
    #         writeoff_line['account_id'] = self.writeoff_account_id.id
    #         writeoff_line['debit'] = debit_wo
    #         writeoff_line['credit'] = credit_wo
    #         writeoff_line['amount_currency'] = amount_currency_wo
    #         writeoff_line['currency_id'] = currency_id
    #         writeoff_line = aml_obj.create(writeoff_line)
    #         if counterpart_aml['debit']:
    #             counterpart_aml['debit'] += credit_wo - debit_wo
    #         if counterpart_aml['credit']:
    #             counterpart_aml['credit'] += debit_wo - credit_wo
    #         counterpart_aml['amount_currency'] -= amount_currency_wo
    #
    #     if counterpart_aml.reconciled is False:
    #         self.invoice_ids.register_payment(counterpart_aml)
    #
    #     # Write counterpart lines
    #     if not self.currency_id != self.company_id.currency_id:
    #         amount_currency = 0
    #     for payment in self.payment_line:
    #         payment_total = (payment.paid_total * MAP_TYPE_PAYMENT_SIGN[self.payment_type])
    #         debit, credit, amount_currency, currency_id = aml_obj.with_context(
    #             date=self.payment_date
    #         ).compute_amount_fields(
    #             payment_total,
    #             self.currency_id,
    #             self.company_id.currency_id,
    #             invoice_currency
    #         )
    #         liquidity_aml_dict = self._get_shared_move_line_vals(
    #             credit,
    #             debit,
    #             -amount_currency,
    #             move.id,
    #             False
    #         )
    #
    #         # account_id = payment.payment_method_id.account_id.id
    #         # if payment.payment_method_id.account_id.id
    #         liquidity_aml_dict.update(
    #             self._get_liquidity_move_line_vals_multi(
    #                 payment,
    #                 -amount
    #             )
    #         )
    #         aml_obj.create(liquidity_aml_dict)
    #
    #     self.check_suspend_vat(move_id=move)
    #     move.post()
    #     self.move_id = move
    #     # Reconclie by line in payment
    #     for line in move.line_ids:
    #         if line.invoice_id:
    #             line.invoice_id.register_payment(line)
    #     return move


class AccountPaymentLine(models.Model):
    _inherit = 'account.payment.line'

    is_domain_payment_method = fields.Boolean(
        string='is Domain Payment Method',
        default=False,
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
        default=lambda self: self._context.get('tender', ''),
    )
    cheque_number = fields.Char(
        string='Number',
    )

    @api.onchange('is_domain_payment_method')
    def onchange_get_domain_payment_method(self):
        domain = [
            ('company_id', '=', self.env.user.company_id.id),
            ('type', 'in', ['cash', 'bank', 'writeoff', 'creditcard']),
        ]

        return {
            'domain': {
                'payment_method_id': domain
            }
        }
