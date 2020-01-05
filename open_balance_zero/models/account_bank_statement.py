# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError

import time


class AccountBankStatement(models.Model):

    _inherit = "account.bank.statement"

    @api.multi
    def _get_opening_balance(self, journal_id):
        last_bnk_stmt = self.search([('journal_id', '=', journal_id)], limit=1)
        if last_bnk_stmt:
            return 0
        return 0

    @api.multi
    def button_confirm_bank(self):
        # self._balance_check()
        statements = self.filtered(lambda r: r.state == 'open')
        for statement in statements:
            moves = self.env['account.move']
            for st_line in statement.line_ids:
                if st_line.account_id and not st_line.journal_entry_ids.ids:
                    st_line.fast_counterpart_creation()
                elif not st_line.journal_entry_ids.ids:
                    raise UserError(_('All the account entries lines must be processed in order to close the statement.'))
                moves = (moves | st_line.journal_entry_ids)
            if moves:
                moves.post()
            statement.message_post(body=_('Statement %s confirmed, journal items were created.') % (statement.name,))
        statements.link_bank_to_partner()
        statements.write({'state': 'confirm', 'date_done': time.strftime("%Y-%m-%d %H:%M:%S")})
