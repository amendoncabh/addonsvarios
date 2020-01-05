# -*- coding: utf-8 -*-
import logging

from odoo import api, models, _
from odoo.exceptions import UserError

try:
    from tools.safe_eval import safe_eval
    import tools
except ImportError:
    from odoo.tools.safe_eval import safe_eval
    from odoo import tools

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.multi
    def print_shift_close(self):
        for record in self:
            return record.env['report'].get_action(record, 'shift.close.jasper')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.multi
    def action_view_picking(self):
        for order in self:
            if not order.partner_id:
                raise UserError(_('Please provide a customer.'))

            return {
                'view_mode': 'form',
                'view_id': order.env.ref('stock.view_picking_form').id,
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'res_id': order.picking_id.id,
            }

    def _create_account_move_line(self, session=None, move=None):
        super(PosOrder, self)._create_account_move_line(session, move)
        if move:
            self._cr.execute("""
                SELECT      aml.account_id,
                            coalesce(pt.cp_cid_ofm, aml.name),
                            sum(debit),
                            sum(credit)
                FROM        account_move_line aml
                LEFT JOIN   product_product pp on pp.id = aml.product_id
                LEFT JOIN   product_template pt on pt.id = pp.product_tmpl_id
                WHERE       aml.move_id = %s
                GROUP BY    aml.account_id,coalesce(pt.cp_cid_ofm, aml.name)
                """, (move.id,)
            )

            for row in self._cr.fetchall():
                if (row[2] * row[3]) != 0:
                    self.env['account.move.line.ofm'].create({
                        'move_id': move.id,
                        'account_id': row[0],
                        'product_cp_cid': row[1] or None,
                        'debit': 0,
                        'credit': row[3],
                        'name': row[1] or None,
                    })
                    self.env['account.move.line.ofm'].create({
                        'move_id': move.id,
                        'account_id': row[0],
                        'product_cp_cid': row[1] or None,
                        'debit': row[2],
                        'credit': 0,
                        'name': row[1] or None,
                    })

                else:
                    self.env['account.move.line.ofm'].create({
                        'move_id': move.id,
                        'account_id': row[0],
                        'product_cp_cid': row[1] or None,
                        'debit': row[2],
                        'credit': row[3],
                        'name': row[1] or None,
                    })

    @api.multi
    def action_pos_order_invoice(self):
        for order in self:
            res = super(PosOrder, order).action_pos_order_invoice()
            res.update({'type': 'ir.action.do_nothing'})
            if 'res_id' in res:
                invoice_id = self.env['account.invoice'].browse(res['res_id'])
                invoice_id.action_invoice_open()
            return res

    @api.multi
    def print_receipt_ofm(self, data):
        records = []

        # Send parameter to print
        params = {
            'IDS': ','.join(map(str, self.ids)),
            'data_dir': tools.config.get('data_dir')
        }

        if self.printed_receipt_first is False:
            self.write({'printed_receipt_first': True})
        else:
            self.write({'printed_receipt': True})

        if self.is_void_order is True:
            report_name = 'receipt.void.short.jasper'
        elif self.is_return_order is True:
            report_name = 'receipt.return.short.jasper'
        else:
            report_name = 'receipt.short.jasper'

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }

        return res

    def _reconcile_payments(self):
        for order in self:
            aml = order.statement_ids.mapped('journal_entry_ids').mapped(
                'line_ids') | order.account_move.line_ids | order.invoice_id.move_id.line_ids
            change_invoice = self.env['account.invoice'].search(
                [('pos_id', '=', order.id), ('state', '=', 'open')])
            for invoice in change_invoice:
                aml += invoice.move_id.line_ids
            aml = aml.filtered(lambda
                                   r: not r.reconciled and r.account_id.internal_type == 'receivable' and r.partner_id == order.partner_id.commercial_partner_id)
            # Reconcile returns first
            # to avoid mixing up the credit of a payment and the credit of a return
            # in the receivable account
            aml_returns = aml.filtered(
                lambda l: (l.journal_id.type == 'sale' and l.credit) or (l.journal_id.type != 'sale' and l.debit))
            try:
                aml_returns.reconcile()
                (aml - aml_returns).reconcile()
            except:
                # There might be unexpected situations where the automatic reconciliation won't
                # work. We don't want the user to be blocked because of this, since the automatichttp://localhost:8069/web#menu_id=148&action=214
                # reconciliation is introduced for convenience, not for mandatory accounting
                # reasons.
                # It may be interesting to have the Traceback logged anyway
                # for debugging and support purposes
                _logger.exception('Reconciliation did not work for order %s', order.name)

    def _confirm_orders(self):
        for session in self:
            company_id = session.config_id.journal_id.company_id.id
            orders = session.order_ids.filtered(lambda order: order.state == 'paid')
            journal_id = self.env['ir.config_parameter'].sudo().get_param(
                'pos.closing.journal_id_%s' % company_id, default=session.config_id.journal_id.id)
            if not journal_id:
                raise UserError(_("You have to set a Sale Journal for the POS:%s") % (session.config_id.name,))

            # ADD BRANCH ID TO ACCOUNT MOVE WHEN CONFIRM POS ORDER
            move = self.env['pos.order'].with_context(
                force_company=company_id,
                branch_id=session.config_id.branch_id.id
            )._create_account_move(
                session.start_at,
                session.name,
                int(journal_id),
                company_id,
            )
            orders.with_context(force_company=company_id)._create_account_move_line(session, move)
            for order in session.order_ids.filtered(lambda o: o.state not in ['done', 'invoiced']):
                if order.state not in ('paid'):
                    raise UserError(
                        _("You cannot confirm all orders of this session, because they have not the 'paid' status"))
                order.action_pos_order_done()
            orders_to_reconcile = session.order_ids.filtered(
                lambda order: order.state in ['invoiced', 'done'] and order.partner_id)
            orders_to_reconcile.sudo()._reconcile_payments()

    def update_pos_picking_id_by_cron(self):
        self._cr.execute("""
            select pod.id as pos_id
            from pos_order pod
            inner join pos_order_line pol on pod.id = pol.order_id
            inner join product_product prp on pol.product_id = prp.id
            inner join product_template prt on prp.product_tmpl_id = prt.id
            where prt.type = 'product' 
                  and pod.picking_id is null
            group by pod.id
                        """)

        pos_order_picking_id_obj = self._cr.fetchall()

        pos_order_obj = self.search([('id', 'in', pos_order_picking_id_obj)])

        for pos_order in pos_order_obj:
            local_context = dict(
                self.env.context,
                force_company=pos_order.company_id.id,
                company_id=pos_order.company_id.id
            )
            pos_order.with_context(local_context).create_picking()
