# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import OrderedDict
from datetime import datetime

import odoo.addons.decimal_precision as dp

import odoo
from odoo import api, models
from odoo import fields
from odoo.exceptions import UserError
from odoo.exceptions import except_orm
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Stock Warehouse
# ----------------------------------------------------------
class stock_warehouse(models.Model):
    _inherit = "stock.warehouse"
    _name = "stock.warehouse"

    _order = 'code'

    wh_shelf_stock_loc_id = fields.Many2one(
        'stock.location',
        'Shelf Location',
        domain=[('usage', '=', 'internal')],
    )


# ----------------------------------------------------------
# Stock Picking
# ----------------------------------------------------------

class stock_picking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _default_branch_id(self):
        if self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id
            return branch_id
        else:
            raise except_orm(_('Error!'), _(u" Please Set Branch For This User "))

    @api.multi
    @api.depends('picking_type_name')
    def _compute_invisible_reverse(self):
        res = {}
        for record in self:
            res[record.id] = False
            if record.state != 'done' \
                    or (record.picking_type_name != 'PoS Orders' and record.warehouse_code != 'PPT') \
                    or record.check_flag_reverse:
                res[record.id] = True
        return res

    @api.multi
    @api.depends('picking_type_name')
    def _compute_reverse_flag(self):
        res = {}
        for record in self:
            res[record.id] = False
            picking_resource_id = self.search([('name', '=', record.origin)])
            if picking_resource_id:
                res[record.id] = True
        return res

    def _default_location_destination(self):
        # retrieve picking type from context; if none this returns an empty recordset
        picking_type_id = self._context.get('default_picking_type_id')
        picking_type = self.env['stock.picking.type'].browse(picking_type_id)
        return picking_type.default_location_dest_id

    def _default_location_source(self):
        # retrieve picking type from context; if none this returns an empty recordset
        picking_type_id = self._context.get('default_picking_type_id')
        picking_type = self.env['stock.picking.type'].browse(picking_type_id)
        return picking_type.default_location_src_id

    @api.depends('purchase_id')
    @api.multi
    def _compute_check_from_po(self):
        res = {}
        for record in self:
            if record.purchase_id:
                record.is_from_po = True
            else:
                record.is_from_po = False
        return res

    @api.model
    def _domain_location(self):
        domain = []
        return domain

    location_id = odoo.fields.Many2one(
        'stock.location',
        required=True,
        string="Source Location Zone",
        domain=_domain_location,
        default=_default_location_source,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    location_dest_id = odoo.fields.Many2one(
        'stock.location',
        required=True,
        string="Destination Location Zone",
        domain=_domain_location,
        default=_default_location_destination,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    pack_operation_product_remove_ids = odoo.fields.One2many(
        'stock.pack.operation.remove',
        'picking_id',
        readonly=True,
        string='Related Packing Operations Remove',
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        default=_default_branch_id,
        readonly=True,
    )

    request_out_id = fields.Many2one(
        'requisition.branches',
        readonly=False,
        string='Request OUT Of Branch',
        index=True,
    )
    request_in_id = fields.Many2one(
        'requisition.branches',
        readonly=False,
        string='Request IN Of Branch',
        index=True,
    )
    request_sale_out_id = fields.Many2one(
        'requisition.branches.sale',
        readonly=False,
        string='Request OUT Of Branch For Sale',
        index=True,
    )
    request_sale_in_id = fields.Many2one(
        'requisition.branches.sale',
        readonly=False,
        string='Request IN Of Branch For Sale',
        index=True,
    )
    picking_type_name = fields.Char(
        related='picking_type_id.name',
        string='Picking Type Name',
    )
    warehouse_id = fields.Many2one(
        'picking_type_id.warehouse_id',
        readonly=True,
        string='Warehouse',
    )
    warehouse_code = fields.Char(
        related='picking_type_id.warehouse_id.code',
        readonly=True,
        string='Warehouse Code',

    )
    reverse_invisible = fields.Boolean(
        compute='_compute_invisible_reverse',
        string='Invisible Reverse',
        readonly=True,
    )
    check_flag_reverse = fields.Boolean(
        compute='_compute_reverse_flag',
        string='Reverse Flag',
        readonly=True,
    )
    is_from_po = fields.Boolean(
        string="",
        compute='_compute_check_from_po',
    )

    @api.model
    def create(self, vals):

        if 'sequence_pos_picking' in self._context and self._context.get('sequence_pos_picking'):
            vals.update({
                'name': self._context.get('sequence_pos_picking')
            })

        defaults = self.default_get(['name', 'picking_type_id'])
        picking_type_id = self.env['stock.picking.type'].browse(
            vals.get('picking_type_id', defaults.get('picking_type_id'))
        )
        if vals.get('branch_id', False):
            branch_id = self.env['pos.branch'].browse(
                vals.get('branch_id')
            )
        else:
            raise UserError(_(u"Don't Have Branch ID"))

        date_order = vals.get('min_date', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        sequence_id = picking_type_id.sequence_id

        vals['name'] = sequence_id.with_context({'date': date_order}).next_by_id()

        res_id = super(stock_picking, self).create(vals)

        self.env.cr.commit()

        return res_id

    @api.multi
    def write(self, values):
        if not values:
            values = {}

        if 'pack_operation_product_ids' in values and values.get('pack_operation_product_ids'):
            for line_id in values.get('pack_operation_product_ids'):
                if line_id[0] == 2:
                    raise UserError(_(u"Can't Remove Pack Operation Line"))

        return super(stock_picking, self).write(values)

    def do_transfer(self):
        pos_order_id = self.check_picking_from_pos()
        if pos_order_id:
            self.action_pos_order_invoice(pos_order_id)
            pos_order_id.write({
                'is_return_order': True,
                'refund_user_id': self.env.user.id,
            })
        else:
            po_id = self.env['purchase.order'].search([
                ('name', '=', self.group_id.name)
            ])

            so_id = self.env['sale.order'].search([
                ('name', '=', self.group_id.name)
            ])

            self.create_invoice(self)

            if all([
                self.get_picking_type_return(),
                any([
                    po_id,
                    so_id,
                ])
            ]):

                self.create_cn(self)

        super(stock_picking, self).do_transfer()
        return True

    def action_pos_order_invoice(self, orders):
        Invoice = self.env['account.invoice']

        for order in orders:
            # Force company for all SUPERUSER_ID action
            local_context = dict(self.env.context, force_company=order.company_id.id, company_id=order.company_id.id)

            if not order.partner_id:
                raise UserError(_('Please provide a customer for the order: ') + order.name)

            invoice = Invoice.new(order._prepare_invoice())
            invoice.type = 'out_refund'
            invoice._onchange_partner_id()
            invoice.fiscal_position_id = order.fiscal_position_id

            if order.invoice_id:
                invoice.parent_invoice_id = order.invoice_id.id

            inv = invoice._convert_to_write({name: invoice[name] for name in invoice._cache})
            new_invoice = Invoice.with_context(local_context).sudo().create(inv)
            message = _(
                "This invoice has been created from the point of sale session: <a href=# data-oe-model=pos.order data-oe-id=%d>%s</a>") % (
                      order.id, order.name)
            new_invoice.message_post(body=message)
            new_invoice.write({
                'pos_id': order.id
            })
            # order.write({'invoice_id': new_invoice.id, 'state': 'invoiced'})
            Invoice += new_invoice

            for line in self.move_lines:
                self.with_context(local_context)._action_create_invoice_line(line, new_invoice.id, order)

            new_invoice.with_context(local_context).sudo().compute_taxes()
            # order.sudo().write({'state': 'invoiced'})

            # this workflow signal didn't exist on account.invoice -> should it have been 'invoice_open' ? (and now method .action_invoice_open())
            # shouldn't the created invoice be marked as paid, seing the customer paid in the POS?
            # new_invoice.sudo().signal_workflow('validate')

        if not Invoice:
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('account.invoice_form').id,
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': Invoice and Invoice.ids[0] or False,
        }

    def _action_create_invoice_line(self, line=False, invoice_id=False, order_id=False):
        InvoiceLine = self.env['account.invoice.line']
        inv_name = line.product_id.name_get()[0][1]
        inv_line = {
            'invoice_id': invoice_id,
            'product_id': line.product_id.id,
            'quantity': line.product_uom_qty,
            'name': inv_name,
        }
        # Oldlin trick
        invoice_line = InvoiceLine.sudo().new(inv_line)
        invoice_line._onchange_product_id()
        invoice_line.invoice_line_tax_ids = invoice_line.invoice_line_tax_ids.filtered(
            lambda t: t.company_id.id == order_id.company_id.id
        ).ids
        fiscal_position_id = order_id.fiscal_position_id
        if fiscal_position_id:
            invoice_line.invoice_line_tax_ids = fiscal_position_id.map_tax(
                invoice_line.invoice_line_tax_ids, line.product_id, order_id.partner_id
            )
        invoice_line.invoice_line_tax_ids = invoice_line.invoice_line_tax_ids.ids
        # We convert a new id object back to a dictionary to write to
        # bridge between old and new api
        inv_line = invoice_line._convert_to_write({
            name: invoice_line[name] for name in invoice_line._cache
        })
        # inv_line.update(price_unit=line.price_unit, discount=line.discount)
        return InvoiceLine.sudo().create(inv_line)

    def check_picking_from_pos(self):
        picking_ids = self.env['stock.picking'].search([
            ('group_id', '=', self.group_id.id),
        ])
        origin_list = []
        for picking_id in picking_ids:
            origin_list.append(picking_id.origin)

        pos_order_id = self.env['pos.order'].search([
            ('name', 'in', origin_list),
            ('name', '!=', self.origin)
        ], limit=1)

        return pos_order_id

    def _prepare_pack_ops(self, quants, forced_qties):
        vals = super(stock_picking, self)._prepare_pack_ops(quants, forced_qties)
        for val in vals:
            val.update({
                'qty_real': val.get('product_qty')
            })
        return vals

    @api.multi
    def action_cancel(self):

        def loop_check_state(picking_list):
            state_return = None
            state_list = [picking.state for picking in picking_list]
            if state_list:
                if 'assigned' in state_list:
                    state_return = 'waiting'
                elif 'done' in state_list:
                    state_return = 'done'
                else:
                    state_return = 'canceled'
            return state_return

        def set_state_to_rb(picking, state_rb):
            if picking.request_in_id:
                picking.request_in_id.write({'state': state_rb})
            elif picking.request_out_id:
                picking.request_out_id.write({'state': state_rb})

            if picking.request_sale_in_id:
                picking.request_sale_in_id.write({'state': state_rb})
            elif picking.request_sale_out_id:
                picking.request_sale_out_id.write({'state': state_rb})

        for pick in self:
            super(stock_picking, pick).action_cancel()

            if pick.request_out_id or pick.request_in_id:
                picking_in_list = pick.env['stock.picking'].search([
                    ('group_id', '=', pick.group_id.id),
                    ('request_in_id', '!=', False),
                    ('id', '!=', pick.id),
                ])

                picking_out_list = pick.env['stock.picking'].search([
                    ('group_id', '=', pick.group_id.id),
                    ('request_out_id', '!=', False),
                    ('id', '!=', pick.id),
                ])

                picking_state = loop_check_state(picking_out_list)

                if picking_state and picking_state == 'done':
                    picking_state = loop_check_state(picking_in_list)
                    if picking_state:
                        set_state_to_rb(pick, picking_state)
                    else:
                        set_state_to_rb(pick, 'canceled')
                elif picking_state and picking_state != 'done':
                    set_state_to_rb(pick, picking_state)
                else:
                    set_state_to_rb(pick, 'waiting')

            if pick.request_sale_out_id or pick.request_sale_in_id:
                picking_in_list = pick.env['stock.picking'].search([
                    ('group_id', '=', pick.group_id.id),
                    ('request_sale_in_id', '!=', False),
                    ('id', '!=', pick.id),
                ])

                picking_out_list = pick.env['stock.picking'].search([
                    ('group_id', '=', pick.group_id.id),
                    ('request_sale_out_id', '!=', False),
                    ('id', '!=', pick.id),
                ])

                picking_state = loop_check_state(picking_out_list)

                if picking_state and picking_state == 'done':
                    picking_state = loop_check_state(picking_in_list)
                    if picking_state:
                        set_state_to_rb(pick, picking_state)
                    else:
                        set_state_to_rb(pick, 'canceled')
                elif picking_state and picking_state != 'done':
                    set_state_to_rb(pick, picking_state)
                else:
                    set_state_to_rb(pick, 'waiting')

        return True

# ----------------------------------------------------------
# Stock Pack Operation
# ----------------------------------------------------------

class stock_pack_operation(models.Model):
    _inherit = "stock.pack.operation"

    @api.multi
    @api.depends('qty_real', 'qty_done')
    def _compute_qty_left(self, name, args):
        res = {}
        for record in self:
            res[record.id] = record.qty_done - record.qty_real
        return res

    qty_left = fields.Float(
        compute='_compute_qty_left',
        digits=0,
        digits_compute=dp.get_precision('Product Unit of Measure'),
        string='Different',
        readonly=True,
    ),
    qty_real = fields.Float(
        digits_compute=dp.get_precision('Product Unit of Measure'),
        string='QTY Move',
        store=True,
        readonly=True,
    )

    def write(self, vals):
        stock_pack_operation_id = self
        old_pack_lot_ids = stock_pack_operation_id.pack_lot_ids

        if 'pack_lot_ids' in vals and vals.get('pack_lot_ids'):
            pack_lot_ids = vals.get('pack_lot_ids')
            array_packs_remove = []
            for pack_lot_id in pack_lot_ids:
                if pack_lot_id[0] == 2:
                    array_packs_remove.append(pack_lot_id[1])
            temp_pack_lot_ids = []
            lots_temp = OrderedDict()
            lots_edit_temp = OrderedDict()
            for pack_lot_id in pack_lot_ids:
                if pack_lot_id[0] == 0:
                    if 'lot_id' in pack_lot_id[2] and pack_lot_id[2]['lot_id']:
                        old_pack_lot_id = old_pack_lot_ids.filtered(
                            lambda x: x.lot_id.id == pack_lot_id[2]['lot_id']
                        )
                        if old_pack_lot_id and old_pack_lot_id.id not in array_packs_remove:
                            key = pack_lot_id[2]['lot_id']
                            if not lots_edit_temp.get(key):
                                lots_edit_temp[key] = {
                                    'qty': pack_lot_id[2]['qty'] + old_pack_lot_id.qty,
                                }
                            else:
                                qty = lots_edit_temp[key]['qty']
                                lots_edit_temp[key] = {
                                    'qty': pack_lot_id[2]['qty'] + qty,
                                }
                        elif 'lot_name' in pack_lot_id[2] and pack_lot_id[2]['lot_id']:
                            key = pack_lot_id[2]['lot_id']
                            if not lots_temp.get(key):
                                lots_temp[key] = {
                                    u'lot_id': pack_lot_id[2]['lot_id'],
                                    u'lot_name': pack_lot_id[2]['lot_name'],
                                    u'plus_visible': pack_lot_id[2]['plus_visible'],
                                    u'qty': pack_lot_id[2]['qty'],
                                    u'qty_todo': pack_lot_id[2]['qty_todo'],
                                }
                            else:
                                qty = lots_temp[key]['qty']
                                id = lots_temp[key]['lot_id']

                                lots_temp[key] = {
                                    u'lot_id': id,
                                    u'lot_name': pack_lot_id[2]['lot_name'],
                                    u'plus_visible': pack_lot_id[2]['plus_visible'],
                                    u'qty': (pack_lot_id[2]['qty'] + qty),
                                    u'qty_todo': pack_lot_id[2]['qty_todo'],
                                }
                        else:
                            key = pack_lot_id[2]['lot_id']
                            if not lots_temp.get(key):
                                lots_temp[key] = {
                                    u'lot_id': pack_lot_id[2]['lot_id'],
                                    u'plus_visible': pack_lot_id[2]['plus_visible'],
                                    u'qty': pack_lot_id[2]['qty'],
                                }
                            else:
                                qty = lots_temp[key]['qty']

                                lots_temp[key] = {
                                    u'lot_id': pack_lot_id[2]['lot_id'],
                                    u'plus_visible': pack_lot_id[2]['plus_visible'],
                                    u'qty': (pack_lot_id[2]['qty'] + qty),
                                }

                    else:
                        old_pack_lot_id = old_pack_lot_ids.filtered(
                            lambda x: x.lot_name == pack_lot_id[2]['lot_name']
                        )

                        key = pack_lot_id[2]['lot_name']

                        if old_pack_lot_id and old_pack_lot_id.id not in array_packs_remove:
                            if not lots_edit_temp.get(key):
                                lots_edit_temp[key] = {
                                    'qty': pack_lot_id[2]['qty'] + old_pack_lot_id.qty,
                                }
                            else:
                                qty = lots_edit_temp[key]['qty']
                                lots_edit_temp[key] = {
                                    'qty': pack_lot_id[2]['qty'] + qty,
                                }

                        else:

                            if not lots_temp.get(key):
                                lots_temp[key] = {
                                    u'lot_name': pack_lot_id[2]['lot_name'],
                                    u'qty': pack_lot_id[2]['qty'],
                                }
                            else:
                                qty = lots_temp[key]['qty']

                                lots_temp[key] = {
                                    u'lot_name': pack_lot_id[2]['lot_name'],
                                    u'qty': (pack_lot_id[2]['qty'] + qty),
                                }

            for lot_temp in lots_temp:
                temp_pack_lot_ids.append([0, False, lots_temp[lot_temp]])

            if lots_temp:
                vals['pack_lot_ids'] = temp_pack_lot_ids

            for lot_edit_temp in lots_edit_temp:
                old_pack_lot_id = old_pack_lot_ids.filtered(
                    lambda x: x.lot_id.id == lot_edit_temp or x.lot_name == lot_edit_temp
                )
                temp_pack_lot_ids.append([1, old_pack_lot_id.id, lots_edit_temp[lot_edit_temp]])

            if lots_edit_temp:
                vals['pack_lot_ids'] = temp_pack_lot_ids

            for array_pack_remove in array_packs_remove:
                vals['pack_lot_ids'].insert(0, [2, array_pack_remove, False])

        res = super(stock_pack_operation, self).write(vals)
        return res


# ----------------------------------------------------------
# Stock Move
# ----------------------------------------------------------

class stock_move(models.Model):
    _inherit = "stock.move"

    def action_scrap(self, cr, uid, ids, quantity, location_id, restrict_lot_id=False, restrict_partner_id=False,
                     context=None):
        """ Move the scrap/damaged product into scrap location
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be scrapped
        @param quantity : specify scrap qty
        @param location_id : specify scrap location
        @param context: context arguments
        @return: Scraped lines
        """
        quant_obj = self.pool.get("stock.quant")
        # quantity should be given in MOVE UOM
        if quantity <= 0:
            raise UserError(_('Please provide a positive quantity to scrap.'))
        res = []
        for move in self.browse(cr, uid, ids, context=context):
            source_location = move.location_id
            if move.state == 'done':
                source_location = move.location_dest_id
            # Previously used to prevent scraping from virtual location but not necessary anymore
            # if source_location.usage != 'internal':
            # restrict to scrap from a virtual location because it's meaningless and it may introduce errors in stock ('creating' new products from nowhere)
            # raise UserError(_('Forbidden operation: it is not allowed to scrap products from a virtual location.'))
            move_qty = move.product_qty
            move.write({'product_uom_qty': (move_qty - quantity)})
            default_val = {
                'location_id': source_location.id,
                'product_uom_qty': quantity,
                'state': move.state,
                'scrapped': True,
                'location_dest_id': location_id,
                'restrict_lot_id': restrict_lot_id,
                'restrict_partner_id': restrict_partner_id,
            }
            new_move = self.copy(cr, uid, move.id, default_val)

            res += [new_move]
            product_obj = self.pool.get('product.product')
            for product in product_obj.browse(cr, uid, [move.product_id.id], context=context):
                if move.picking_id:
                    uom = product.uom_id.name if product.uom_id else ''
                    message = _("%s %s %s has been <b>moved to</b> scrap.") % (quantity, uom, product.name)
                    move.picking_id.message_post(body=message)

            # We "flag" the quant from which we want to scrap the products. To do so:
            #    - we select the quants related to the move we scrap from
            #    - we reserve the quants with the scrapped move
            # See self.action_done, et particularly how is defined the "preferred_domain" for clarification
            scrap_move = self.browse(cr, uid, new_move, context=context)
            if move.state == 'done' and scrap_move.location_id.usage not in ('supplier', 'inventory', 'production'):
                domain = [('qty', '>', 0), ('history_ids', 'in', [move.id])]
                # We use scrap_move data since a reservation makes sense for a move not already done
                quants = quant_obj.quants_get_preferred_domain(cr, uid, quantity, scrap_move, domain=domain,
                                                               context=context)
                quant_obj.quants_reserve(cr, uid, quants, scrap_move, context=context)
        self.action_done(cr, uid, res, context=context)
        return res

    @api.multi
    def check_tracking(self, pack_operation):
        """ Checks if serial number is assigned to stock move or not and raise an error if it had to. """
        # TDE FIXME: I cannot able to understand
        for move in self:
            if move.picking_id and \
                    (
                            move.picking_id.picking_type_id.use_existing_lots or move.picking_id.picking_type_id.use_create_lots) and \
                    move.product_id.tracking != 'none' and \
                    not (move.restrict_lot_id or (
                            pack_operation and (pack_operation.product_id and pack_operation.pack_lot_ids)) or (
                                 pack_operation and not pack_operation.product_id)):
                raise UserError(_('You need to provide a Lot/Serial Number for product %s') % (
                        "%s (%s)" % (move.product_id.name, move.picking_id.name)))


class StockPackOperationLot(models.Model):
    _inherit = "stock.pack.operation.lot"

    qty = odoo.fields.Float(
        'Done',
        default=0.0,
    )

    _sql_constraints = [
        ('uniq_lot_name', 'check(1=1)', 'You have already mentioned this lot name in another line')
    ]


class stock_pack_operation_remove(models.Model):
    _name = "stock.pack.operation.remove"
    _inherit = "stock.pack.operation"
