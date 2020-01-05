# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    @api.model
    def _domain_payment_methods_company(self):
        domain = [('company_id', '=', self.env.user.company_id.id)]
        return domain

    def _default_journal(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            session = self.env['pos.order'].browse(active_id).session_id
            return session.config_id.journal_ids and session.config_id.journal_ids.ids[0] or False
        return False

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Payment Mode',
        required=False,
        default=_default_journal
    )

    payment_methods = fields.Many2one(
        comodel_name="account.payment.method.multi",
        string="Payment Methods",
        domain=_domain_payment_methods_company,
    )

    approve_code = fields.Char(
        string='Approve Code',
        size=6,
    )

    credit_card_no_pos = fields.Char(
        string='Credit Card No.',
        size=16,
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
        default='VISA',
    )

    is_credit_card = fields.Boolean(
        string="",
        default=False,

    )

    @api.onchange('is_credit_card', 'payment_methods')
    def onchange_is_credit_card(self):
        if self.payment_methods.journal_id.is_credit_card:
            self.is_credit_card = True
            self.credit_card_no_pos = None
            self.approve_code = None
            self.tender = None
        else:
            self.is_credit_card = False


    @api.multi
    def check(self):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        self.ensure_one()
        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))
        amount = order.amount_total - order.amount_paid
        data = self.read()[0]
        # Update Payment Journal_id
        data['update_journal_id'] = self.payment_methods.journal_id.id or data['journal_id'][0] or False
        # this is probably a problem of osv_memory as it's not compatible with normal OSV's
        data['journal'] = data['journal_id'][0] or self.payment_methods.journal_id.id or False

        if self.payment_methods.journal_id.is_credit_card:
            query_credit_card = """
                        ,credit_card_no = {0}
                        ,approve_code = {1}
                        ,credit_card_type = '{2}'
            """.format(
                data['credit_card_no_pos'],
                data['approve_code'],
                data['tender']
            )
        else:
            query_credit_card = ''

        if amount != 0.0:
            aa = order.add_payment(data)
        if order.test_paid():
            order.action_pos_order_paid()
            payment_select = """
                            select id
                            from account_bank_statement_line 
                            WHERE pos_statement_id = {0}
                            and amount = {1};
                        """.format(
                order.id,
                data['amount'] or 0.00
            )

            self.env.cr.execute(payment_select)
            data_payment_id = self.env.cr.dictfetchall()

            for payment_ids in data_payment_id:
                payment_id = payment_ids.get('id', False)

                if payment_ids:
                    payment_update = """
                        UPDATE account_bank_statement_line 
                        set journal_id = {0}
                            {1}
                        WHERE id = {2};
                    """.format(
                        self.payment_methods.journal_id.id or data['journal_id'][0],
                        query_credit_card,
                        payment_id
                    )

                    self.env.cr.execute(payment_update)
                    self.env.cr.commit()

            return {'type': 'ir.actions.act_window_close'}
        return self.launch_payment()



