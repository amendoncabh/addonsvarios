# -*- coding: utf-8 -*-

from functools import partial
from openerp import SUPERUSER_ID
from openerp import api
from openerp import fields
from openerp import models
from openerp.osv import osv
from openerp import tools
from datetime import datetime, timedelta
from openerp.exceptions import UserError
from openerp.tools.translate import _


class pos_session(models.Model):
    _inherit = 'pos.session'
    
    reason_id = fields.Many2one(
        'pos.cash.box.reason',
        string='Reason',
        readonly=True,
        states={
            'opening_control': [('readonly', False)],
            'opened': [('readonly', False)],
        },
        track_visibility='onchange',
        ondelete='restrict',
    )

    config_id = fields.Many2one(
        'pos.config',
        'Point of Sale',
        help="The physical point of sale you will use.",
        required=True,
        select=1,
        domain="[('active', '=', 'True')]",
        track_visibility='onchange',
    )

    @api.multi
    def action_pos_session_open(self):
        for rec in self:
            if rec.cash_register_balance_start > 0:
                super(pos_session, self).action_pos_session_open()
            else:
                raise UserError(_("The Opening Balance do not set."
                                  " Please, set."))

        return True

    @api.multi
    def action_pos_session_close(self):
        # Close CashBox
        for session in self:
            company_id = session.config_id.company_id.id
            ctx = dict(self.env.context, force_company=company_id, company_id=company_id, branch_id=session.config_id.branch_id.id)
            for st in session.statement_ids:
                if (st.journal_id.type not in ['bank', 'cash']):
                    raise UserError(_("The type of the journal for your payment method should be bank or cash "))
                st.with_context(ctx).sudo().button_confirm_bank()
        self.with_context(ctx)._confirm_orders()
        self.write({'state': 'closed'})
        return {
            'type': 'ir.actions.client',
            'name': 'Point of Sale Menu',
            'tag': 'reload',
            'params': {'menu_id': self.env.ref('point_of_sale.menu_point_root').id},
        }