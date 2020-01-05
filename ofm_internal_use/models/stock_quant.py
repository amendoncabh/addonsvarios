# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, journal_id):
        quant_cost_qty = defaultdict(lambda: 0.0)

        for quant in self:
            quant_cost_qty[quant.cost] += quant.qty

        AccountMove = self.env['account.move']

        for cost, qty in quant_cost_qty.iteritems():
            if move.internal_use_id:
                move_lines = move._prepare_account_move_line(qty, cost, move.credit_account_id.id, move.debit_account_id.id)
            else:
                move_lines = move._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            if move.picking_id.account_move_id:
                move.picking_id.account_move_id.write({'line_ids': move_lines})
            elif move.inventory_id.account_move_id:
                move.inventory_id.account_move_id.write({'line_ids': move_lines})
            elif move.internal_use_id.account_move_id:
                move.internal_use_id.account_move_id.write({'line_ids': move_lines})
            else:
                new_account_move = AccountMove.create({
                    'branch_id': move.branch_id.id,
                    'journal_id': journal_id,
                    'line_ids': move_lines,
                    'date': date,
                    'ref': move.picking_id.name
                })
                if move.picking_id:
                    move.picking_id.account_move_id = new_account_move.id
                elif move.internal_use_id:
                    AccountMove.search([('id', '=', new_account_move.id)]).ref = move.inventory_id.name
                    move.internal_use_id.account_move_id = new_account_move.id
                else:
                    AccountMove.search([('id', '=', new_account_move.id)]).ref = move.inventory_id.name
                    move.inventory_id.account_move_id = new_account_move.id


        