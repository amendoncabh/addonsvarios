from datetime import datetime

from odoo import models, api, _, fields
from odoo.tools.misc import formatLang


class account_journal(models.Model):
    _inherit = "account.journal"

    @api.model
    def _default_sequence(self):
        self.env.cr.execute('select sequence from account_journal where sequence is not null order by sequence desc limit 1')
        sequence_returned = self.env.cr.fetchone()[0]
        if sequence_returned:
            sequence_returned += 1
        else:
            sequence_returned = 0
        return sequence_returned

    sequence = fields.Integer(
        help='Used to order Journals in the dashboard view',
        default=_default_sequence,
        readonly=False
    )

    is_credit_card = fields.Boolean(
        string="Credit Card",
    )

    @api.multi
    def get_journal_dashboard_datas(self):
        currency = self.currency_id or self.company_id.currency_id
        number_to_reconcile = last_balance = account_sum = 0
        ac_bnk_stmt = []
        title = ''
        number_draft = number_waiting = number_late = sum_draft = sum_waiting = sum_late = 0
        if self.type in ['bank', 'cash']:
            last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)], order="date desc, id desc", limit=1)
            last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0
            ac_bnk_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids),('state', '=', 'open')])
            for ac_bnk in ac_bnk_stmt:
                for line in ac_bnk.line_ids:
                    if not line.journal_entry_ids:
                        number_to_reconcile += 1
            # optimization to read sum of balance from account_move_line
            account_ids = tuple(filter(None, [self.default_debit_account_id.id, self.default_credit_account_id.id]))
            if account_ids:
                amount_field = 'balance' if not self.currency_id else 'amount_currency'
                query = """SELECT sum(%s) FROM account_move_line WHERE account_id in %%s;""" % (amount_field,)
                self.env.cr.execute(query, (account_ids,))
                query_results = self.env.cr.dictfetchall()
                if query_results and query_results[0].get('sum') != None:
                    account_sum = query_results[0].get('sum')
        #TODO need to check if all invoices are in the same currency than the journal!!!!
        elif self.type in ['sale', 'purchase']:
            title = _('Bills to pay') if self.type == 'purchase' else _('Invoices owed to you')
            # optimization to find total and sum of invoice that are in draft, open state
            query = """SELECT state, amount_total, currency_id AS currency FROM account_invoice WHERE journal_id = %s AND state NOT IN ('paid', 'cancel');"""
            self.env.cr.execute(query, (self.id,))
            query_results = self.env.cr.dictfetchall()
            today = datetime.today()
            query = """SELECT amount_total, currency_id AS currency FROM account_invoice WHERE journal_id = %s AND date < %s AND state = 'open';"""
            self.env.cr.execute(query, (self.id, today))
            late_query_results = self.env.cr.dictfetchall()
            sum_draft = 0.0
            number_draft = 0
            number_waiting = 0
            for result in query_results:
                cur = self.env['res.currency'].browse(result.get('currency'))
                amount_total = result.get('amount_total') or 0
                if result.get('state') in ['draft', 'proforma', 'proforma2']:
                    number_draft += 1
                    sum_draft += cur.compute(amount_total, currency)
                elif result.get('state') == 'open':
                    number_waiting += 1
                    sum_waiting += cur.compute(amount_total, currency)
            sum_late = 0.0
            number_late = 0
            for result in late_query_results:
                cur = self.env['res.currency'].browse(result.get('currency'))
                number_late += 1
                sum_late += cur.compute(amount_total, currency)

        return {
            'number_to_reconcile': number_to_reconcile,
            'account_balance': formatLang(self.env, account_sum, currency_obj=self.currency_id or self.company_id.currency_id),
            'last_balance': formatLang(self.env, last_balance, currency_obj=self.currency_id or self.company_id.currency_id),
            'number_draft': number_draft,
            'number_waiting': number_waiting,
            'number_late': number_late,
            'sum_draft': formatLang(self.env, sum_draft or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'sum_waiting': formatLang(self.env, sum_waiting or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'sum_late': formatLang(self.env, sum_late or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'currency_id': self.currency_id and self.currency_id.id or self.company_id.currency_id.id,
            'bank_statements_source': self.bank_statements_source,
            'title': title,
        }

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        context = self._context or {}
        company_id = context.get('company_id', False)
        if company_id:
            if name:
                account_journal_ids = self.search(
                    [
                        ('company_id', '=', company_id),
                        ('name', 'ilike', name),
                    ] + args,
                    limit=limit
                )
            else:
                account_journal_ids = self.search(
                    [
                        ('company_id', '=', company_id),
                    ] + args,
                    limit=limit
                )

            return account_journal_ids.sudo().name_get()

        return super(account_journal, self).name_search(name, args, operator, limit)
