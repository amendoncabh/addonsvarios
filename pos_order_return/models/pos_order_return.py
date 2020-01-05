# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    not_returnable = fields.Boolean('Not Returnable')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_void_order = fields.Boolean(
        string='Void Order',
        copy=False,
    )
    return_order_id = fields.Many2one(
        'pos.order',
        'Return Order Of',
        readonly=True,
        copy=False,
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

    return_reason_id = fields.Many2one(
        'return.reason',
        string='Reason',
        required=False,
        readonly=True,
    )

    void_ids = fields.One2many(
        'pos.order',
        'return_order_id',
        string="Return/Void Orders",
        required=False,
        readonly=True,
        copy=False,
    )

    @api.model
    def _process_order(self, pos_order):
        prec_acc = self.env['decimal.precision'].precision_get('Account')
        pos_session = self.env['pos.session'].browse(pos_order['pos_session_id'])
        if pos_session.state == 'closing_control' or pos_session.state == 'closed':
            pos_order['pos_session_id'] = self._get_valid_session(pos_order).id
        if pos_order['is_void_order'] or pos_order['is_return_order']:
            if pos_order['return_status'] == 'Fully-Returned':
                original_order = self.env['pos.order'].browse(pos_order.get('return_order_id'))
                if original_order:
                    original_order.return_status = pos_order['return_status']

            pos_order['amount_paid'] = 0
            for line in pos_order['lines']:
                line_dict = line[2]
                if line_dict.get('original_line_id'):
                    original_line = self.env['pos.order.line'].browse(line_dict.get('original_line_id'))
                    if line_dict['promotion'] and line_dict['qty'] > 0:
                        original_line.line_qty_returned -= abs(line_dict['qty'])
                    else:
                        original_line.line_qty_returned += abs(line_dict['qty'])
            for statement in pos_order['statement_ids']:
                statement_dict = statement[2]
                if pos_order['amount_total'] < 0:
                    statement_dict['amount'] = statement_dict['amount'] * -1
                if statement_dict.get('original_line_id'):
                    original_statement_line = self.env['account.bank.statement.line'].browse(statement_dict.get('original_line_id'))
                    original_statement_line.line_amount_returned += abs(statement_dict['amount'])

            pos_order['amount_return'] = 0
            pos_order['amount_total'] = pos_order['amount_total_rounding']

        order = self.create(self._order_fields(pos_order))
        journal_ids = set()
        for payments in pos_order['statement_ids']:
            if not float_is_zero(payments[2]['amount'], precision_digits=prec_acc):
                order.add_payment(self._payment_fields(payments[2]))
            journal_ids.add(payments[2]['journal_id'])

        if pos_session.sequence_number <= pos_order['sequence_number']:
            pos_session.write({'sequence_number': pos_order['sequence_number'] + 1})
            pos_session.refresh()

        if not float_is_zero(pos_order['amount_return'], prec_acc):
            cash_journal_id = pos_session.cash_journal_id.id
            if not cash_journal_id:
                # Select for change one of the cash journals used in this
                # payment
                cash_journal = self.env['account.journal'].search([
                    ('type', '=', 'cash'),
                    ('id', 'in', list(journal_ids)),
                ], limit=1)
                if not cash_journal:
                    # If none, select for change one of the cash journals of the POS
                    # This is used for example when a customer pays by credit card
                    # an amount higher than total amount of the order and gets cash back
                    cash_journal = [statement.journal_id for statement in pos_session.statement_ids if
                                    statement.journal_id.type == 'cash']
                    if not cash_journal:
                        raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
                cash_journal_id = cash_journal[0].id
            order.add_payment({
                'amount': -pos_order['amount_return'],
                'payment_date': fields.Datetime.now(),
                'payment_name': _('Change CASH'),
                'journal': cash_journal_id,
            })
        return order

    @api.model
    def _order_fields(self, ui_order):
        fields_return = super(PosOrder, self)._order_fields(ui_order)
        # if ui_order.get('is_void_order') or ui_order.get('is_return_order'):
        #     return_order_id = self.browse(ui_order.get('return_order_id'))
        #     if return_order_id.invoice_id.state not in ['cancel']:
        #         return_order_id.invoice_id.action_invoice_cancel()
        fields_return.update({
            'approver_id': ui_order.get('approver_id') or False,
            'approve_datetime': ui_order.get('approve_datetime') or False,
            'is_void_order': ui_order.get('is_void_order') or False,
            'is_return_order': ui_order.get('is_return_order') or False,
            'return_order_id': ui_order.get('return_order_id') or False,
            'return_status': ui_order.get('return_status') or False,
            'return_reason_id': ui_order.get('return_reason_id') or False,
        })
        return fields_return

    @api.model
    def _payment_fields(self, ui_paymentline):
        res = super(PosOrder, self)._payment_fields(ui_paymentline)
        res.update({
            'line_amount_returned': ui_paymentline.get('line_amount_returned', False),
            'original_line_id': ui_paymentline.get('original_line_id', False),
        })
        return res

    @api.model
    def _prepare_bank_statement_line_payment_values(self, data):
        res = super(PosOrder, self)._prepare_bank_statement_line_payment_values(data)
        res.update({
            'line_amount_returned': data.get('line_amount_returned', False),
            'original_line_id': data.get('original_line_id', False),
        })
        return res

    def _prepare_invoice(self):
        res = super(PosOrder, self)._prepare_invoice()
        if self.is_void_order or self.is_return_order:
            res.update({
                'parent_invoice_id': self.return_order_id.invoice_id or False,
                'type': 'out_refund',
                'return_reason_id': self.return_reason_id,
            })
        return res

    def create_picking(self):
        super(PosOrder, self).create_picking()
        self.picking_id.update({
            'return_reason_id': self.return_reason_id.id,
            'branch_id': self.branch_id.id,
        })
        for move_line in self.picking_id.move_lines:
            move_line.update({
                'branch_id': self.picking_id.branch_id.id,
            })
        return True


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'
    line_qty_returned = fields.Integer('Line Returned', default=0)
    original_line_id = fields.Many2one('pos.order.line', "Original line")

    @api.model
    def _order_line_fields(self, line):
        fields_return = super(PosOrderLine, self)._order_line_fields(line)
        fields_return[2].update({'line_qty_returned': line[2].get('line_qty_returned', '')})
        fields_return[2].update({'original_line_id': line[2].get('original_line_id', '')})
        return fields_return
