# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _quant_create_from_move(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, force_location_from=False, force_location_to=False):
        if move.picking_id.group_id.id:
            purchase_id = self.env['purchase.order'].search(
                [
                    ('group_id', '=', move.picking_id.group_id.id)
                ]
            )
            if purchase_id and move.picking_id.group_id:
                purchase_order_lines = purchase_id.order_line.filtered(
                    lambda x: x.product_id.id == move.product_id.id
                )

                if purchase_order_lines:
                    purchase_order_line = purchase_order_lines[0]
                    force_valuation_amount = purchase_order_line.price_unit
                    move = move.with_context(force_valuation_amount=force_valuation_amount)
        else:
            average_id = self.env['average.price'].search(
                [
                    ('product_id', '=', move.product_id.id),
                    ('branch_id', '=', move.branch_id.id)
                ],
                order="id desc",
                limit=1
            )
            if average_id:
                force_valuation_amount = average_id.cost
            else:
                force_valuation_amount = move.product_id.price_normal
            move = move.with_context(force_valuation_amount=force_valuation_amount)
        quant = super(StockQuant, self)._quant_create_from_move(
            qty,
            move,
            lot_id=lot_id,
            owner_id=owner_id,
            src_package_id=src_package_id,
            dest_package_id=dest_package_id,
            force_location_from=force_location_from,
            force_location_to=force_location_to
        )

        return quant

    def _quant_update_from_move(self, move, location_dest_id, dest_package_id, lot_id=False, entire_pack=False):
        if move.picking_id.group_id.id:
            purchase_id = self.env['purchase.order'].search(
                [
                    ('group_id', '=', move.picking_id.group_id.id)
                ]
            )
            if purchase_id:
                purchase_order_lines = purchase_id.order_line.filtered(
                    lambda x: x.product_id.id == move.product_id.id
                )
                if purchase_order_lines:
                    purchase_order_line = purchase_order_lines[0]
                    force_valuation_amount = purchase_order_line.price_unit
                    move = move.with_context(force_valuation_amount=force_valuation_amount)
        else:
            average_id = self.env['average.price'].search(
                [
                    ('product_id', '=', move.product_id.id),
                    ('branch_id', '=', move.branch_id.id)
                ],
                order='id desc',
                limit= 1
            )
            if average_id:
                force_valuation_amount = average_id.cost
            else:
                force_valuation_amount = move.product_id.price_normal
            move = move.with_context(force_valuation_amount=force_valuation_amount)
        res = super(StockQuant, self)._quant_update_from_move(move, location_dest_id, dest_package_id, lot_id=lot_id, entire_pack=entire_pack)
        return res

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, journal_id):
        quant_cost_qty = defaultdict(lambda: 0.0)

        for quant in self:
            quant_cost_qty[quant.cost] += quant.qty

        AccountMove = self.env['account.move']

        for cost, qty in quant_cost_qty.iteritems():
            move_lines = move._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
            date = self._context.get('force_period_date', fields.Date.context_today(self))

            if move.picking_id.account_move_id:
                move.picking_id.account_move_id.write({'line_ids': move_lines})
            elif move.inventory_id.account_move_id:
                move.inventory_id.account_move_id.write({'line_ids': move_lines})
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
                else:
                    AccountMove.search([('id', '=', new_account_move.id)]).ref = move.inventory_id.name
                    move.inventory_id.account_move_id = new_account_move.id
