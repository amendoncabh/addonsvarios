# -*- encoding: UTF-8 -*-

from datetime import datetime

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, UserError


class CashBoxIn(models.TransientModel):
    _inherit = 'cash.box.in'

    @api.model
    def _default_reason_id(self):
        if 'active_id' in self.env.context and self.env.context.get('active_id', False):
            active_id = self.env.context["active_id"]
            pos_order_id = self.env['pos.session'].browse([active_id])
            return pos_order_id.reason_id.id
        else:
            return self

    @api.one
    def _create_bank_statement_line(self, record):
        date_now = datetime.now()
        company_id = self.env.user.company_id.id
        user_id = self.env.user.id
        if record.state == 'confirm':
            raise UserError(_("You cannot put/take money in/out for a bank statement which is closed."))
        values = self._calculate_values_for_statement_line(record)
        # return record.write({'line_ids': [(0, False, values[0])]})
        vals = values[0]
        self.env.cr.execute("""
                INSERT INTO account_bank_statement_line
                  (name, sequence, amount, statement_id, journal_id, cash_box_type, date, ref, account_id, create_date, create_uid, company_id)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
            (vals['name'], 1, 0, vals['statement_id'], vals['journal_id'], vals['cash_box_type'], vals['date'], vals['ref'], vals['account_id'], date_now, user_id, company_id)
        )
        insert_id = self.env.cr.fetchone()[0]
        bank_statement_line_id = self.env['account.bank.statement.line'].browse(insert_id)
        bank_statement_line_id.write({
            'amount': vals['amount']
        })
        return record

    name = fields.Char(string='Reason', required=True)

    reason_id = fields.Many2one(
        'pos.cash.box.reason',
        string='Reason',
        required=True,
        default=_default_reason_id,
        ondelete='restrict',

    )
    amount_text = fields.Char(
        string='Amount',
        required=True,
        default='',
    )

    @api.onchange('reason_id')
    def _onchange_reason(self):
        self.update({
            'name': self.reason_id.name,
        })

    @api.onchange('amount_text')
    def _onchange_reason(self):

        def num(s):
            try:
                return float(s)
            except ValueError:
                raise except_orm(_('Error!'), _(" Input Only Digit "))

        if self.amount_text:

            self.update({
                'amount': num(self.amount_text),
                'name': self.reason_id.name,
            })
        else:
            self.update({
                'amount': 0.0,
                'name': self.reason_id.name,
            })


class CashBoxOut(models.TransientModel):
    _inherit = 'cash.box.out'

    @api.model
    def _default_reason_id(self):
        if 'active_id' in self.env.context and self.env.context.get('active_id', False):
            active_id = self.env.context["active_id"]
            pos_order_id = self.env['pos.session'].browse([active_id])
            return pos_order_id.reason_id.id
        else:
            return self

    @api.one
    def _create_bank_statement_line(self, record):
        date_now = datetime.now()
        company_id = self.env.user.company_id.id
        user_id = self.env.user.id
        if record.state == 'confirm':
            raise UserError(_("You cannot put/take money in/out for a bank statement which is closed."))
        values = self._calculate_values_for_statement_line(record)
        # return record.write({'line_ids': [(0, False, values[0])]})
        vals = values[0]
        self.env.cr.execute("""
                INSERT INTO account_bank_statement_line
                  (name, sequence, amount, statement_id, journal_id, cash_box_type, date, ref, account_id, create_date, create_uid, company_id)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
            (vals['name'], 1, 0, vals['statement_id'], vals['journal_id'], vals['cash_box_type'], vals['date'], vals['ref'], vals['account_id'], date_now, user_id, company_id)
        )
        insert_id = self.env.cr.fetchone()[0]
        bank_statement_line_id = self.env['account.bank.statement.line'].browse(insert_id)
        bank_statement_line_id.write({
            'amount': vals['amount']
        })
        return record

    name = fields.Char(string='Reason', required=True)

    reason_id = fields.Many2one(
        'pos.cash.box.reason',
        string='Reason',
        required=True,
        default=_default_reason_id,
        ondelete='restrict',
    )
    amount_text = fields.Char(
        string='Amount',
        required=True,
        default='',
    )

    @api.onchange('reason_id')
    def _onchange_reason(self):
        self.update({
            'name': self.reason_id.name,
        })

    @api.onchange('amount_text')
    def _onchange_reason(self):

        def num(s):
            try:
                return float(s)
            except ValueError:
                raise except_orm(_('Error!'), _(" Input Only Digit "))

        if self.amount_text:

            self.update({
                'amount': num(self.amount_text),
                'name': self.reason_id.name,
            })
        else:
            self.update({
                'amount': 0.0,
                'name': self.reason_id.name,
            })