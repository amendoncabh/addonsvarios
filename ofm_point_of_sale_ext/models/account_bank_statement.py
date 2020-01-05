# -*- coding: utf-8 -*-

from odoo import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        res = super(AccountBankStatementLine, self).process_reconciliation(counterpart_aml_dicts, payment_aml_rec, new_aml_dicts)
        self.ensure_one()
        self._cr.execute("""\
                    SELECT      aml.account_id,
                                coalesce(pt.cp_cid_ofm, aml.name),
                                sum(debit),
                                sum(credit)
                    FROM        account_move_line aml
                    LEFT JOIN   product_product pp on pp.id = aml.product_id
                    LEFT JOIN   product_template pt on pt.id = pp.product_tmpl_id
                    WHERE       aml.move_id = %s
                    GROUP BY    aml.account_id,coalesce(pt.cp_cid_ofm, aml.name)
                    """, (res.id,)
                         )

        for row in self._cr.fetchall():
            self.env['account.move.line.ofm'].create({
                'move_id': res.id,
                'account_id': row[0],
                'product_cp_cid': row[1] or None,
                'debit': row[2],
                'credit': row[3],
                'name': row[1] or None,
            })
        return res
