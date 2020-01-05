# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import except_orm
from odoo.tools import float_utils


class SaleOrder(models.Model):
    _inherit = "sale.order"

    deposit_ids = fields.One2many(
        comodel_name='account.deposit',
        inverse_name='sale_id',
        string='Deposit',
        readonly=False,
        index=True,
        copy=False,
    )

    count_deposit_amount = fields.Integer(
        string='Quantity Deposit',
        compute='compute_amount_of_deposit',
        readonly=True
    )

    is_hide_confirm_so = fields.Boolean(
        string='Hide Confirm SO',
        readonly=True,
        default=True,
        compute='compute_hide_confirm_so'
    )

    is_hide_deposit = fields.Boolean(
        string='Hide Deposit',
        readonly=True,
        default=True,
        compute='compute_hide_deposit'
    )

    is_hide_payment = fields.Boolean(
        string='Hide Payment',
        readonly=True,
        default=True,
        compute='compute_hide_payment'
    )

    is_hide_delivery = fields.Boolean(
        string='Hide Delivery',
        readonly=True,
        default=True,
        compute='compute_hide_delivery'
    )

    sale_payment_type = fields.Selection(
        selection=[
            ('cash', 'Cash/ Credit Card'),
            ('deposit', 'Deposit'),
            ('credit', 'Credit Term'),
        ],
        string='Payment Type',
    )

    credit_term_card_no = fields.Char(
        string='Credit Card No.',
        size=16,
    )

    credit_term_tender = fields.Many2one(
        comodel_name="account.payment.method.multi",
        string="Payment Methods",
    )

    deposit_payment_line_ids = fields.One2many(
        comodel_name='account.deposit.payment.line',
        compute='compute_deposit_payment_line',
    )

    is_hide_credit_term_tender = fields.Boolean(
        string='Hide Credit Term Tender',
        readonly=True,
        compute='compute_is_hide_credit_term_tender'
    )

    is_hide_action_cancel_payment_type = fields.Boolean(
        string='Hide Action Cancel Payment Type',
        readonly=True,
        compute='compute_is_hide_action_cancel_payment_type'
    )

    credit_note_ids = fields.Many2many(
        'account.invoice',
        'sale_order_credit_note_rel',
        'sale_id',
        'invoice_id',
        string='Credit Note Line',
    )

    @api.multi
    def _prepare_invoice(self):
        for rec in self:
            res = super(SaleOrder, rec)._prepare_invoice()

            deposit_ids = rec.deposit_ids.filtered(
                lambda rec_depo: rec_depo.state in ['open', 'paid']
            )

            inv_deposit_ids = [
                (
                    6,
                    0,
                    deposit_ids.ids
                )
            ]

            res.update({
                'deposit_ids': inv_deposit_ids,
            })

            return res

    def open_confirm_so_without_deposit(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirm SO without Deposit',
            'res_model': 'confirm.without.deposit.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('tr_account_deposit.confirm_without_deposit_form_wizard', False).id,
            'target': 'new',
        }

    def get_deposit_state_show_confirm_so(self):
        return [
            'open',
        ]

    def get_customer_credit_balance(self):
        customer_balance = (self.partner_id.aging_balance - self.amount_total)

        return customer_balance

    def check_deposit_for_customer_payment_credit(self):
        deposit_draft = self.deposit_ids.filtered(
            lambda deposit_rec: deposit_rec.state == 'draft'
        )

        if deposit_draft:
            raise except_orm(_('Error!'), _(u"There is a deposit remaining, please complete it."))
        else:
            deposit_on_hands = self.deposit_ids.filtered(
                lambda deposit_rec: deposit_rec.state in ['open', 'paid']
            )

            if deposit_on_hands:
                return self.action_confirm_so()
            else:
                return self.open_confirm_so_without_deposit()

    def check_customer_credit_balance(self):
        customer_balance = self.get_customer_credit_balance()

        if self.state == 'sent' \
                and self.partner_id.customer_payment_type == 'credit' \
                and customer_balance < 0\
                and self.sale_payment_type not in ['deposit', 'cash']:
            raise except_orm(_('Error!'), _(u"This customer have Credit Balance less then 0. Please, Payment Deposit."))

    @api.multi
    @api.depends('state', 'deposit_ids')
    def compute_hide_confirm_so(self):
        for rec in self:
            if rec.state == 'sent':
                rec.is_hide_confirm_so = False
            else:
                rec.is_hide_confirm_so = True

    @api.multi
    @api.depends('state', 'deposit_ids')
    def compute_amount_of_deposit(self):
        for rec in self:
            if rec.deposit_ids:
                rec.count_deposit_amount = len(rec.deposit_ids)
            else:
                rec.count_deposit_amount = 0

    @api.multi
    @api.depends('deposit_ids')
    def compute_hide_payment(self):
        for rec in self:
            deposit_without_cancel = rec.deposit_ids.filtered(
                lambda deposit_rec: deposit_rec.state != 'cancel'
            )
            customer_balance = rec.get_customer_credit_balance()
            total_deposit = sum([deposit.paid_total for deposit in deposit_without_cancel])

            if any([
                float_utils.float_compare(rec.amount_total, total_deposit, 0, 0) == 0,
                rec.state not in ['sent', 'sale'],
                rec.sale_payment_type == 'credit',
            ]):
                if customer_balance < 0 and rec.sale_payment_type not in ['deposit', 'cash', 'credit']:
                    rec.is_hide_payment = False
                else:
                    rec.is_hide_payment = True
            else:
                rec.is_hide_payment = False

    @api.multi
    @api.depends('deposit_ids')
    def compute_hide_deposit(self):
        for rec in self:
            deposit_without_cancel = rec.deposit_ids.filtered(
                lambda deposit_rec: deposit_rec.state != 'cancel'
            )

            if all([
                deposit_without_cancel,
                rec.sale_payment_type in ['deposit', 'cash'],
            ]):
                rec.is_hide_deposit = False
            else:
                rec.is_hide_deposit = True

    @api.multi
    @api.depends('delivery_count', 'is_hide_deposit', 'is_hide_payment')
    def compute_hide_delivery(self):
        for rec in self:
            deposit_draft_id = rec.deposit_ids.filtered(
                lambda deposit_rec: deposit_rec.state == 'draft'
            )

            if all([
                rec.state in ['sale', 'done'],
                rec.is_hide_payment,
                not deposit_draft_id,
            ]):
                rec.is_hide_delivery = False
            else:
                rec.is_hide_delivery = True

    @api.multi
    @api.depends('is_hide_payment')
    def compute_is_hide_credit_term_tender(self):
        if self.sale_payment_type == 'credit':
            self.is_hide_credit_term_tender = False
        else:
            self.is_hide_credit_term_tender = True

    @api.multi
    @api.depends('is_hide_payment')
    def compute_is_hide_action_cancel_payment_type(self):
        for rec in self:
            picking_ids = rec.picking_ids.filtered(
                lambda picking_rec: picking_rec.state == 'done'
            )

            if not rec.sale_payment_type or picking_ids:
                rec.is_hide_action_cancel_payment_type = True
            else:
                rec.is_hide_action_cancel_payment_type = False

    @api.multi
    @api.depends('deposit_ids')
    def compute_deposit_payment_line(self):
        for rec in self:
            deposit_id = rec.deposit_ids.filtered(
                lambda deposit_rec: deposit_rec.state != 'cancel'
            )

            rec.deposit_payment_line_ids = rec.env['account.deposit.payment.line'].search([
                ('payment_id', '=', deposit_id.id),
            ])

    @api.multi
    def action_open_so_payments_form_wizard(self):
        for rec in self:
            if rec.customer_type:

                if rec.type_sale_ofm:
                    rec.call_api_check_qty_from_ofm()
                    is_danger = rec.check_qty_with_qty_available(rec.order_line)

                    if is_danger:
                        raise except_orm(_('Error!'), _(u"Please check product because some product invalid."))

                deposit_id = rec.deposit_ids.filtered(
                    lambda deposit_id_rec: deposit_id_rec.state == 'draft'
                )

                total_deposit = deposit_id.paid_total if deposit_id else 0
                total_balance = rec.amount_total - total_deposit
                customer_balance = rec.get_customer_credit_balance()

                ctx = dict(rec._context)
                ctx.update({
                    'default_advance_amount': total_balance,
                    'default_total_amount': total_balance,
                    'default_company_id': rec.company_id.id,
                    'is_no_credit_balance': True if customer_balance < 0 else False,
                    'default_type_sale_ofm': rec.type_sale_ofm,
                })
                if rec.partner_id['credit_term_tender_id']:
                    ctx.update({
                        'credit_term_tender_id': rec.partner_id.credit_term_tender_id.id,
                    })

                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Payments',
                    'res_model': 'so.payments.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': rec.env.ref('tr_account_deposit.so_payments_form_wizard', False).id,
                    'context': ctx,
                    'target': 'new',
                }
            else:
                raise except_orm(_('Error!'), _(u"No Customer Type."))

    @api.multi
    def action_open_deposit(self):
        for rec in self:
            deposit_ids = rec.deposit_ids

            if deposit_ids:
                deposit_id = deposit_ids.filtered(
                    lambda deposit_id_rec: deposit_id_rec.state != 'cancel'
                )

                if deposit_id:
                    action = rec.env.ref('tr_account_deposit.tr_action_account_deposit_out_no_create').read()[0]
                    action['views'].pop(0)
                    action['res_id'] = deposit_id.id

                    return action

            raise except_orm(_('Error!'), _(u"No Deposit."))

    @api.multi
    def action_confirm_so_with_customer_payment_type(self):
        for rec in self:
            return rec.action_confirm_so()

    @api.multi
    def action_cancel(self):
        for rec in self:
            res = super(SaleOrder, rec).action_cancel()

            for deposit_id in rec.deposit_ids:
                deposit_id.deposit_cancel()
        
            return res

    @api.multi
    def action_cancel_so(self):
        for rec in self:
            res = super(SaleOrder, self).action_cancel_so()

            #commented out because deposits will not be cancelled from SO
            # for deposit_id in rec.deposit_ids:
            #     deposit_id.deposit_cancel()
        
        return res

    @api.multi
    def action_cancel_payment_type(self):
        for rec in self:
            if rec.sale_payment_type:
                if rec.sale_payment_type == 'credit':
                    rec.update({
                        'sale_payment_type': False,
                        'payment_term_id': False,
                    })
                elif rec.sale_payment_type in ['deposit', 'cash']:
                    rec.update({
                        'payment_term_id': False,
                    })

                    deposit_id = rec.deposit_ids.filtered(
                        lambda deposit_rec: deposit_rec.state != 'cancel'
                    )
                    if deposit_id:
                        deposit_id.deposit_cancel()

        return True

    @api.multi
    def print_deposit_form(self):
        for record in self:
            result = super(SaleOrder, record).print_deposit_form()
            deposit_without_cancel = record.deposit_ids.filtered(
                lambda deposit_rec: deposit_rec.state != 'cancel'
            )
            if deposit_without_cancel:
                # deposit_without_cancel.print_time_dpo += 1
                # if deposit_without_cancel.print_time_dpo == 1:
                #     deposit_without_cancel.is_first_print_dpo = False

                if all({
                    record.state != 'draft',
                    record.deposit_ids,
                }):
                    record.is_delivery_print = True

                report_name = 'full.tax.invoice.deposit.jasper'

                params = {
                    'IDS': ','.join(map(str, self.ids)),
                }

                result = {
                    'type': 'ir.actions.report.xml',
                    'report_name': report_name,
                    'datas': {'records': [], 'parameters': params},
                }

                return result
            else:
                raise except_orm(_('No Deposit!'), _('Please Make Deposit'))

    @api.multi
    def write(self, vals):
        for rec in self:
            sale_payment_type = vals.get('sale_payment_type', False)

            if sale_payment_type:
                if sale_payment_type in ['deposit', 'cash']:
                    vals.update({
                        'payment_term_id': False,
                    })
                elif sale_payment_type == 'credit' or not sale_payment_type:
                    payment_term_id = rec.partner_id.property_payment_term_id

                    vals.update({
                        'payment_term_id': payment_term_id.id if payment_term_id else False,
                    })

            res = super(SaleOrder, self).write(vals)

            return res

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        ctx = dict(self.env.context)
        if 'cancel_from_deposit' in ctx.keys():
            if ctx['cancel_from_deposit']:
                del ctx['cancel_from_deposit']
                return []
            else:
                del ctx['cancel_from_deposit']
                res = super(SaleOrder, self).action_invoice_create(grouped, final)
        else:
            res = super(SaleOrder, self).action_invoice_create(grouped, final)
        return res


