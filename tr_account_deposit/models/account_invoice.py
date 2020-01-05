# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Trinity Roots co.,ltd. (<http://www.trinityroots.co.th>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, Warning, RedirectWarning, UserError

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Supplier Invoice
    'out_refund': 'out_invoice',        # Customer Refund
    'in_refund': 'in_invoice',          # Supplier Refund
}


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    deposit_ids = fields.Many2many(
        comodel_name='account.deposit',
        string='Deposit'
    )

    deposit_payment_line_ids = fields.One2many(
        comodel_name='account.deposit.payment.line',
        compute='compute_deposit_payment_line',
    )

    deposit_cash_credit_ids = fields.Many2many(
        comodel_name='account.deposit',
        string='Cash/ Credit',
        related='deposit_ids',
        store=False,
    )

    deposit_cash_credit_payment_line_ids = fields.One2many(
        comodel_name='account.deposit.payment.line',
        related='deposit_payment_line_ids',
        store=False,
    )

    amount_deposit = fields.Float(
        string='Deposit',
        digits=dp.get_precision('Account'),
        store=True,
        readonly=True,
        compute='_compute_amount',
        track_visibility='always'
    )
    amount_tax_deposit = fields.Float(
        string='Tax Deposit',
        digits=dp.get_precision('Account'),
        store=True,
        readonly=True,
        compute='_compute_amount',
        track_visibility='always'
    )
    parent_invoice_id = fields.Many2one(
        comodel_name='account.invoice',
        string='Parent Invoice',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        help='This is the main invoice that has generated this credit note'
    )
    child_ids = fields.One2many(
        comodel_name='account.invoice',
        inverse_name='parent_invoice_id',
        string='Debit and Credit Notes',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        help='These are all credit and debit to this invoice'
    )

    partner_parent_id = fields.Many2one(
        'res.partner',
        string="Partner Parent",
        related='partner_id.parent_id'
    )

    is_show_clear_deposit = fields.Boolean(
        string="Show Clear Deposit",
        compute="_compute_is_show_clear_deposit"
    )

    invisible_reconcile_refund_button = fields.Boolean(
        string="Is Invisible Reconcile Refund Button",
        compute="_compute_is_invisible_reconcile_refund_button"
    )

    @api.multi
    def _compute_is_show_clear_deposit(self):
        for record in self:
            if record.so_id and record.so_id.type_sale_ofm:
                if record.state == 'paid' and record.so_id.sale_payment_type == 'deposit':
                    record.is_show_clear_deposit = True
                else:
                    record.is_show_clear_deposit = False
            else:
                record.is_show_clear_deposit = False

    @api.multi
    def _compute_is_invisible_reconcile_refund_button(self):
        for record in self:
            so_id = record.mapped('so_id')
            is_invisible = False
            if any([
                record.type in ('in_invoice','out_invoice'),
                len(record.parent_invoice_id) == 0,
                record.state == 'paid'
            ]):
                is_invisible = True
            elif so_id and so_id.sale_payment_type != 'credit':
                is_invisible = True

            record.invisible_reconcile_refund_button = is_invisible

    @api.model
    def get_move_line(self, inv_id):
        res = {}

        if inv_id.type in ['in_invoice', 'in_refund']:
            amount = -inv_id.amount_untaxed
        else:
            amount = inv_id.amount_untaxed
        res.update({
            'type': 'src',
            'name': 'Invoice : ' + inv_id.name if inv_id.name else inv_id.name_customer,
            'price': amount,
            'account_id': inv_id.account_id.id,
            'date_maturity': inv_id.date,
            'amount_currency': False,
            'currency_id': False,
            'ref': inv_id.name,
            'deposit_id': inv_id.id,
        })
        # residual = deposit.residual - total
        # if residual <= 0:
        # inv_id.write({'state': 'paid'})

        return res

    def monkey_pad_check_deposit_total_ps(self, inv, total, iml):
        price = 0

        if total:
            if inv.amount_deposit != 0 and inv.type in ('in_invoice', 'in_refund'):
                price = total + (inv.amount_deposit + inv.amount_tax_deposit)
                iml += inv.deposit_ids.get_move_line()
                iml += inv.deposit_ids.tax_line_move_line_get()

            elif inv.amount_deposit != 0 and inv.type in ('out_invoice', 'out_refund'):
                price = (inv.amount_deposit + inv.amount_tax_deposit) - total
                iml += inv.deposit_ids.get_move_line()
                iml += inv.deposit_ids.tax_line_move_line_get()
            else:
                price = total + inv.amount_deposit
                iml += self._get_refund_move()

        return {
            'price': price,
            'iml': iml
        }

    def monkey_pad_add_deposit_decimal_adj_in_iml(self, inv, price, adjusted_dep, adjust_price, iml):
        if any([
            inv.amount_total - price >= -0.1,
            inv.amount_total - price <= 0.1 and adjusted_dep
        ]):
            decimal_adj = False
            dep = inv.deposit_ids.get_move_line()

            if dep:
                decimal_adj = dep[0]
                decimal_adj.update({
                    'name': 'Adjust decimal for balance',
                    'price': -1 * adjust_price,
                })
            if decimal_adj:
                iml += [decimal_adj]

        if inv.amount_deposit == 0 and adjust_price <> 0:
            inv_adjust = self.get_move_line(inv)

            if len(inv_adjust) > 0:
                inv_adjust.update({
                    'name': 'Adjust decimal for balance',
                    'price': adjust_price,
                })

                iml += [inv_adjust]
                
        return {
            'iml': iml,
            'decimal_adj': decimal_adj
        }

    def monkey_pad_get_deposit_adjust_dep_and_price(self, inv, price):
        adjusted_dep = False
        adjust_price = 0.0

        if self.type not in ['out_invoice', 'in_refund']:
            price *= -1

        temp_b1 = (inv.amount_total - price >= -0.1)
        temp_b2 = (inv.amount_total - price <= 0.1)

        if (temp_b1 or temp_b2) and not adjusted_dep:
            adjust_price = inv.amount_total - price
            price += inv.amount_total - price
            adjusted_dep = True

        if self.type not in ['out_invoice', 'in_refund']:
            price *= -1

        return {
            'price': price,
            'adjust_price': adjust_price,
            'adjusted_dep': adjusted_dep
        }

    @api.model
    def _get_refund_move(self):
        values = []
        for deposit in self.deposit_ids:

            if deposit.account_refund_id:
                account_id = deposit.account_refund_id.id
            else:
                account_id = deposit.account_id.id
            values.append({
                    'type': 'dest',
                    'name': 'Withdraw Deposit'+deposit.name,
                    'price': -deposit.amount_untaxed+-deposit.amount_tax,
                    'account_id': account_id,
                    'date_maturity': deposit.date,
                    'amount_currency': False,
                    'currency_id': False,
                    'ref': deposit.name,
                    })
            if deposit.account_refund_id == deposit.account_id:
                deposit.write({'state': 'open'})
        return values

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None,
                        return_reason_id=None):

        res = super(AccountInvoice, self)._prepare_refund(
            invoice,
            date_invoice,
            date,
            description,
            journal_id,
            return_reason_id
        )
        tax_lines = filter(lambda l: l.manual, invoice.tax_line_ids)
        tax_line = self._refund_cleanup_lines(tax_lines)

        res.update({
            'tax_line': tax_line
        })

        return res

    @api.multi
    @api.depends(
        'deposit_ids.amount_untaxed',
        'deposit_ids.amount_tax',
        'invoice_line_ids.price_subtotal',
        'tax_line_ids.amount',
        'currency_id',
        'company_id',
        'date_invoice',
        'type',
        'invoice_line_ids.price_subtotal_discount',
        'discount'
    )
    def _compute_amount(self):
        super(AccountInvoice, self)._compute_amount()
        for invoice_obj in self:

            # FOR DEPOSIT
            invoice_obj.amount_deposit = sum(line.amount_untaxed for line in invoice_obj.deposit_ids)
            invoice_obj.amount_tax_deposit = sum(line.amount_tax for line in invoice_obj.deposit_ids)

            invoice_obj.amount_total = invoice_obj.amount_total - (
                        invoice_obj.amount_deposit + invoice_obj.amount_tax_deposit)

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


class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"

    @api.model
    def move_line_get(self, invoice_id):
        res = []

        query_str = """
            SELECT id,
                account_id,
                invoice_id,
                manual,
                company_id,
                currency_id,
                amount as tax_amount,
                account_analytic_id,
                tax_id as tax_code_id,
                name,
                base_manual as amount,
                partner_id,
                invoice_ref,
                voucher_id,
                petty_tax_id,
                advance_tax_id,
                vat_date,
                payment_id 
            FROM account_invoice_tax 
            WHERE invoice_id = %s
        """

        self._cr.execute(query_str, (invoice_id,))

        inv = self.env['account.invoice'].browse(invoice_id)
        for row in self._cr.dictfetchall():
            if not (row['amount'] or row['tax_code_id'] or row['tax_amount']):
                continue
            res.append({
                'type': 'tax',
                'name': row['name'],
                'price_unit': row['amount'] - inv.amount_tax_deposit,
                'quantity': 1,
                'price': row['amount'] - inv.amount_tax_deposit or 0.0,
                'account_id': row['account_id'],
                'tax_code_id': row['tax_code_id'],
                'tax_amount': row['tax_amount'] - inv.amount_tax_deposit,
                'account_analytic_id': row['account_analytic_id'],
            })
        return res
