# -*- coding: utf-8 -*-

from odoo import api, models, fields, tools, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class ProductChangeQuantity(models.TransientModel):
    _inherit = "stock.change.product.qty"

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.user.company_id.id,
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string="Branch",
        index=True,
        required=True,
        default=lambda self: self.env.user.branch_id.id,
    )

    current_quantity = fields.Float(
        'Current Quantity on Hand',
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=True,
    )

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.branch_id = False

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        self.location_id = False

    @api.onchange('location_id', 'product_id')
    def onchange_location_id(self):
        if self.location_id and self.product_id:
            availability = self.product_id.with_context({
                'compute_child': False,
                'location': self.location_id.id,
            })._product_available()
            self.new_quantity = availability[self.product_id.id]['qty_available']
            self.current_quantity = self.new_quantity

    def _prepare_inventory(self):
        return {
            'name': _('INV: %s') % tools.ustr(self.product_id.name),
            'product_id': self.product_id.id,
            'location_id': self.location_id.id,
            'lot_id': self.lot_id.id,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
        }

    @api.multi
    def change_product_qty(self):
        """ Changes the Product Quantity by making a Physical Inventory. """
        Inventory = self.env['stock.inventory']
        for wizard in self:
            product = wizard.product_id.with_context(location=wizard.location_id.id, lot_id=wizard.lot_id.id)
            line_data = wizard._prepare_inventory_line()

            if self.product_id.id and self.lot_id.id:
                inventory_filter = 'none'
            elif self.product_id.id:
                inventory_filter = 'product'
            else:
                inventory_filter = 'none'

            inventory_val = wizard._prepare_inventory()
            inventory_val.update({
                'filter': inventory_filter,
                'line_ids': [(0, 0, line_data)],
            })
            inventory = Inventory.create(inventory_val)
            inventory.action_done()
        return {
            'type': 'ir.actions.act_window_close'
        }
