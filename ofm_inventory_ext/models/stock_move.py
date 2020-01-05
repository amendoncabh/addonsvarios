# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    def _default_branch(self):
        branch_id = self._context.get('branch_id', False)
        if branch_id:
            return branch_id
        return self.env.user.branch_id

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        default=_default_branch,
    )

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        res.update({
            'branch_id': self.branch_id.id,
        })
        return res

    @api.multi
    def _get_accounting_data_for_valuation(self):
        self.ensure_one()

        journal_id, acc_src, acc_dest, acc_valuation = super(StockMove, self)._get_accounting_data_for_valuation()
        if self.origin_returned_move_id.purchase_line_id and self.picking_type_id.code == 'outgoing':
            return_acc_dest = self.product_id.product_tmpl_id.categ_id.property_stock_return_account
            if not return_acc_dest:
                raise UserError(_(
                    'You don\'t have any Stock Return Account defined on your product category, check if you have installed a chart of accounts')
                )
            if return_acc_dest:
                acc_src = return_acc_dest.id
        return journal_id, acc_src, acc_dest, acc_valuation

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
        res = super(StockMove, self)._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
        for line in res:
            line[2].update({
                'product_cp_cid': self.product_id.cp_cid_ofm or None,
            })
        return res

    @api.multi
    def action_done(self):
        res = super(StockMove, self).action_done()
        for move in self:
            if move.picking_id.date_done:
                move.date = move.picking_id.date_done
            if move.picking_id.account_move_id and \
                    move.picking_id.account_move_id.state == 'draft':
                move.picking_id.account_move_id.group_line_ofm()
                move.picking_id.account_move_id.post()
            elif move.inventory_id.account_move_id and \
                    move.inventory_id.account_move_id.state == 'draft':
                move.inventory_id.account_move_id.group_line_ofm()
                move.inventory_id.account_move_id.post()
        return res
