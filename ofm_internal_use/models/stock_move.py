# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class StockMove(models.Model):
    _inherit = "stock.move"

    internal_use_id = fields.Many2one(
        'internal.use'
    )
    internal_use_line_id = fields.Many2one(
        'internal.use.line'
    )
    credit_account_id = fields.Many2one(
        'account.account'
    )
    debit_account_id = fields.Many2one(
        'account.account'
    )

    @api.multi
    def action_done(self):
        res = super(StockMove, self).action_done()
        for move in self:
            if move.internal_use_id.account_move_id and \
                    move.internal_use_id.account_move_id.state == 'draft':
                move.internal_use_id.account_move_id.group_line_ofm()
                move.internal_use_id.account_move_id.post()
        return res

    def _prepare_new_average_price(self):
        pos_id = None
        po_id = None
        so_id = None  # waiting
        sa_id = None  # waiting
        int_id = None
        stock_location_id = None
        move_type = None
        price = 0
        priority = None
        product_uom_qty = None

        pos_order_obj = False
        po_order_obj = False
        source_internal_move_obj = False
        dest_internal_move_obj = False
        so_obj = False
        sa_obj = False
        iu_id = None
        ui_obj = False

        if self.picking_id:
            pos_order_obj = self.env['pos.order'].search([
                ('picking_id', '=', self.picking_id.id)
            ], order="id desc", limit=1)
            po_order_obj = self.env['purchase.order'].search([
                ('group_id', '=', self.picking_id.group_id.id)
            ], order="id desc", limit=1)
            source_internal_move_obj = self.env['ofm.stock.internal.move'].search([
                ('picking_id', '=', self.picking_id.id)
            ], order="id desc", limit=1)
            dest_internal_move_obj = self.env['ofm.stock.internal.move'].search([
                ('picking_dest_id', '=', self.picking_id.id)
            ], order="id desc", limit=1)
            so_obj = self.env['sale.order'].search([
                ('procurement_group_id', '=', self.picking_id.group_id.id)
            ], order="id desc", limit=1)

        if self.inventory_id and self.inventory_id.id:
            sa_obj = self.inventory_id

        if self.internal_use_id and self.internal_use_id.id:
            ui_obj = self.internal_use_id

        if pos_order_obj:
            pos_id = pos_order_obj.id

            if pos_order_obj.is_return_order is True or pos_order_obj.is_void_order is True:
                move_type = 'RT_POS'
                priority = 2
                stock_location_id = self.location_dest_id.id
                product_uom_qty = self.product_uom_qty
            else:
                move_type = 'POS'
                priority = 12
                stock_location_id = self.location_id.id
                product_uom_qty = self.product_uom_qty * (-1)
        elif source_internal_move_obj:
            int_id = source_internal_move_obj.id
            move_type = 'OUT_INT'
            priority = 14
            stock_location_id = self.location_id.id
            product_uom_qty = self.product_uom_qty * (-1)
        elif dest_internal_move_obj:
            price = self.env['average.price'].search([
                ('branch_id', '=', dest_internal_move_obj.branch_id.id),
                ('stock_location_id', '=', dest_internal_move_obj.location_id.id),
                ('product_id', '=', self.product_id.id),
            ], order="id desc", limit=1).price

            int_id = dest_internal_move_obj.id
            move_type = 'IN_INT'
            priority = 4
            stock_location_id = self.location_dest_id.id
            product_uom_qty = self.product_uom_qty
        elif po_order_obj:
            po_id = po_order_obj.id
            price = self.price_unit

            if self.picking_id.picking_type_id.code == 'outgoing':
                move_type = 'RT_PO'
                priority = 11
                stock_location_id = self.location_id.id
                product_uom_qty = self.product_uom_qty * (-1)
            else:
                move_type = 'PO'
                priority = 1
                stock_location_id = self.location_dest_id.id
                product_uom_qty = self.product_uom_qty
        elif so_obj:
            so_id = so_obj.id

            if self.picking_id.picking_type_id.code == 'incoming':
                move_type = 'RT_SO'
                priority = 3
                stock_location_id = self.location_dest_id.id
                product_uom_qty = self.product_uom_qty
            else:
                move_type = 'SO'
                priority = 13
                stock_location_id = self.location_id.id
                product_uom_qty = self.product_uom_qty * (-1)
        elif sa_obj:
            sa_id = sa_obj.id
            move_type = 'SA'
            stock_location_id = self.location_dest_id.id
            product_uom_qty = self.product_uom_qty
            if self.location_dest_id.usage == 'inventory':
                move_type = 'RT_SA'
                stock_location_id = self.location_id.id
                product_uom_qty = self.product_uom_qty * (-1)

        elif ui_obj:
            ui_id = ui_obj.id
            move_type = 'UI'
            stock_location_id = self.location_dest_id.id
            product_uom_qty = self.product_uom_qty
            if self.location_dest_id.usage == 'inventory':
                move_type = 'RT_UI'
                stock_location_id = self.location_id.id
                product_uom_qty = self.product_uom_qty * (-1)

        else:
            sa_id = sa_obj.id
            move_type = 'OTHER'
            stock_location_id = self.location_dest_id.id
            product_uom_qty = self.product_uom_qty
            if self.location_dest_id.usage == 'inventory':
                move_type = 'RT_SA'
                stock_location_id = self.location_id.id
                product_uom_qty = self.product_uom_qty * (-1)

        parameter = (
            int(stock_location_id),
            '%/',
            '/%',
        )

        self._cr.execute("""
            select pob.id as branch_id
            from pos_branch pob
            inner join stock_warehouse swh on pob.warehouse_id = swh.id
            inner join (
                        select *
                        from stock_location
                        where id = %s
                       ) stl on stl.complete_name like concat(%s, swh.code, %s)
                """, parameter)

        branch_obj = self._cr.dictfetchone()

        branch_id = branch_obj['branch_id'] if branch_obj else self.env.user.branch_id.id

        new_stock_move = [{
            'branch_id': branch_id,
            'int_id': int_id,
            'move_date': self.date,
            'move_id': self.id,
            'move_type': move_type,
            'picking_id': self.picking_id.id,
            'po_id': po_id,
            'pos_id': pos_id,
            'price': price,
            'priority': priority,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'product_uom_qty': product_uom_qty,
            'sa_id': sa_id,
            'so_id': so_id,
            'stock_location_id': stock_location_id,
        }]

        return new_stock_move