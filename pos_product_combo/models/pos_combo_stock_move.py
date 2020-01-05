# -*- encoding: UTF-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2015-Today Key Concepts IT Services LLP.
#    (<http://keyconcepts.co.in>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
from openerp import api, models


class POSOrder(models.Model):
    _name = "pos.order"
    _inherit = "pos.order"
    _description = "Point of Sale"
    _order = "id desc"

    @api.multi
    def create_picking(self):
        res = super(POSOrder, self).create_picking()
        move_obj = self.env['stock.move']
        move_list = []
        picking_id = self.picking_id.id
        picking_type = self.picking_type_id
        location_id = self.location_id.id
        destination_id = picking_type.default_location_dest_id.id
        for combo in self.lines:
            if combo.product_id.is_pack:
                for product in combo.product_id.product_pack_id:
                    pos_qty = product.product_quantity * combo.qty
                    move_list.append(move_obj.create({
                        'name': self.name,
                        'product_uom': product.product_id.uom_id.id,
                        'picking_id': picking_id,
                        'picking_type_id': picking_type.id,
                        'product_id': product.product_id.id,
                        'product_uom_qty': abs(pos_qty),
                        'state': 'draft',
                        'location_id': location_id if pos_qty >= 0 else destination_id,
                        'location_dest_id': destination_id if pos_qty >= 0 else location_id,
                    }))
        for move in move_list:
            move.action_confirm()
            move.force_assign()
            move.action_done()
        return res
