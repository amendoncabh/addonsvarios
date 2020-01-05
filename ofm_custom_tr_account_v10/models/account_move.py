# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo import tools


class AccountMove(models.Model):
    _inherit = 'account.move'

    line_ofm_ids = fields.One2many(
        'account.move.line.ofm',
        'move_id',
        string='Journal Items OFM',
        states={'posted': [('readonly', True)]},
        copy=True
    )

    @api.multi
    def post(self):
        for record in self:
            if not record.branch_id:
                raise UserError(_(u"Don't Have Branch ID"))

            invoice_type = record._context.get('invoice_type', False)

            if 'out_invoice' == invoice_type:
                res_model = self._name + '.out_invoice.' + str(record.journal_id.id)
            elif 'in_invoice' == invoice_type:
                res_model = self._name + '.in_invoice.' + str(record.journal_id.id)
            elif 'out_refund' == invoice_type:
                res_model = self._name + '.out_refund.' + str(record.journal_id.id)
            elif 'in_refund' == invoice_type:
                res_model = self._name + '.in_refund.' + str(record.journal_id.id)
            else:
                res_model = self._context.get('active_model', self._name) + '.' + record.journal_id.type

            type_payment_to_customer = record._context.get('type_payment_to_customer', False)

            if type_payment_to_customer:
                res_model += '.' + type_payment_to_customer

            seq = self.env['pos.session.sequence'].search([
                ('branch_code', '=', record.branch_id.branch_code),
                ('res_model', '=', res_model),
            ], limit=1)

            sequence = record.journal_id.sequence_id

            if invoice_type in ['out_refund', 'in_refund'] and record.journal_id.refund_sequence:
                if not record.journal_id.refund_sequence_id:
                    raise UserError(_('Please define a sequence for the refunds'))
                sequence = record.journal_id.refund_sequence_id

            prefix = sequence.prefix

            if not seq:
                if record.branch_id.branch_code:
                    if prefix.find('/') != -1:
                        prefixs = sequence.prefix.split('/')
                    elif prefix.find('-') != -1:
                        prefixs = sequence.prefix.split('-')
                    else:
                        raise UserError(_(u"This %s Prefix Don't Have Special Character" % prefix))

                    if invoice_type in ['in_invoice']:
                        prefix = prefixs[0] + '-' + record.branch_id.branch_code + '%(y)s%(month)s'
                        padding = 6

                    else:
                        prefix = prefixs[0] + '-' + record.branch_id.branch_code + '%(y)s%(month)s'
                        padding = 5
                date_order = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ctx = dict(self._context)
                ctx.update({'res_model': res_model})

                sequence_id = record.branch_id.with_context(ctx).next_sequence(date_order, prefix, padding, False)

            else:

                sequence_id = seq.sequence_id

            if invoice_type in ['out_refund', 'in_refund'] and record.journal_id.refund_sequence:
                if not record.journal_id.refund_sequence_id:
                    raise UserError(_('Please define a sequence for the refunds'))
                record.journal_id.sudo().update({
                    'refund_sequence_id': sequence_id.id
                })
            else:
                record.journal_id.sudo().update({
                    'sequence_id': sequence_id.id
                })
        super(AccountMove, self).post()

    def _default_branch(self):
        branch_id = self._context.get('branch_id', False)
        if branch_id:
            return branch_id
        return self.env.user.branch_id

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        default=_default_branch,
    )

    @api.multi
    def group_line_ofm(self):
        self.ensure_one()
        self._cr.execute("""\
            SELECT      account_id,
                        product_cp_cid,
                        sum(debit),
                        sum(credit)
            FROM        account_move_line
            WHERE       move_id = %s
            GROUP BY    account_id,product_cp_cid
            """, (self.id,))

        for row in self._cr.fetchall():
            if not row[2] or not row[3]:
                self.line_ofm_ids.create({
                    'move_id': self.id,
                    'account_id': row[0],
                    'product_cp_cid': row[1] or None,
                    'debit': row[2],
                    'credit': row[3],
                    'name': row[1] or '',
                })
            if row[2] and row[3]:
                self.line_ofm_ids.create({
                    'move_id': self.id,
                    'account_id': row[0],
                    'product_cp_cid': row[1] or None,
                    'debit': row[2],
                    'credit': 0,
                    'name': row[1] or '',
                })
                self.line_ofm_ids.create({
                    'move_id': self.id,
                    'account_id': row[0],
                    'product_cp_cid': row[1] or None,
                    'debit': 0,
                    'credit': row[3],
                    'name': row[1] or '',
                })

    @api.multi
    def assert_balanced(self):
        if not self.ids:
            return True
        prec = self.env['decimal.precision'].precision_get('Account')

        self._cr.execute("""\
                        SELECT      sum(debit) - sum(credit)
                        FROM        account_move_line
                        WHERE       move_id in %s
                        GROUP BY    move_id
                        HAVING      abs(sum(debit) - sum(credit)) > %s
                        """, (tuple(self.ids), 10 ** (-2)))

        result = self._cr.fetchall()

        print result

        if len(result) != 0:
            raise UserError(_("Cannot create unbalanced journal entry."))
        return True


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_cp_cid = fields.Char(
        string="CPC ID",
        required=False,
    )

    @api.depends('debit', 'credit', 'amount_currency', 'currency_id', 'matched_debit_ids', 'matched_credit_ids',
                 'matched_debit_ids.amount', 'matched_credit_ids.amount', 'move_id.state')
    def _amount_residual(self):
        super(AccountMoveLine, self)._amount_residual()
        for line in self:

            line.amount_residual = tools.float_round(
                line.amount_residual,
                precision_rounding=0.0001
            )


class AccountMoveLineOFM(models.Model):
    _name = 'account.move.line.ofm'
    _inherit = 'account.move.line'
