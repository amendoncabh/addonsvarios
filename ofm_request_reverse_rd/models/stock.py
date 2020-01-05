# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models, _
from odoo import fields
from odoo.exceptions import except_orm, UserError

_logger = logging.getLogger(__name__)


class stock_picking(models.Model):
    _inherit = "stock.picking"

    not_approve_request = fields.Boolean(
        string="Not Approve",
        default=True,
        readonly=True,
    )
    hide_force_button = fields.Boolean(
        string="Hide Button Request",
        compute='_compute_force_validate',
        readonly=True,
    )
    hide_available_button = fields.Boolean(
        string="Hide Button Available",
        compute='_compute_invisible_available',
        readonly=True,
    )
    hide_request_button = fields.Boolean(
        string="Hide Button Request",
        compute='_compute_invisible_request',
        readonly=True,
    )
    hide_do_new_transfer = fields.Boolean(
        string="Hide Button Validate",
        compute='_compute_hide_do_new_transfer',
        readonly=True,
    )
    hide_do_new_transfer_customer = fields.Boolean(
        string="Hide Button Validate",
        compute='_compute_hide_do_new_transfer_customer',
        readonly=True,
    )
    hide_tab_operations = fields.Boolean(
        string="Hide Tab Operations",
        compute="_compute_hide_tab_operations"
    )
    readonly_operation_pack_ids = fields.Boolean(
        string="Readonly Operation Pack",
        compute='_compute_readonly_operation_pack_ids',
        readonly=True,
    )
    is_request_created = fields.Boolean(
        string="Request Reverse Created",
        default=False,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('waiting', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('partially_available', 'Partially Available'),
            ('waiting_approve', 'Waiting Approve'),
            ('rejected', 'Rejected'),
            ('assigned', 'Available'),
            ('done', 'Done')
        ],
        string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n"
             " * Waiting Availability: still waiting for the availability of products\n"
             " * Partially Available: some products are available and reserved\n"
             " * Ready to Transfer: products reserved, simply waiting for confirmation.\n"
             " * Transferred: has been processed, can't be modified or cancelled anymore\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore"
    )

    reason_reject = fields.Char(
        string='Reason Reject From HQ',
        readonly=True
    )

    rtv_type = fields.Selection(
        selection=[
            ('change', 'Re-Delivery'),
            ('cn', 'Credit Note')
        ],
        string='RTV Type',
        readonly='True',
    )

    product_include_ids = fields.One2many(
        comodel_name='product.product',
        string='Product Include',
        compute='compute_get_product_include',
    )

    # move_lines_check_dup = fields.Char(
    #     string='Move Line Check Duplicate',
    #     compute="_compute_move_lines_check_dup"
    # )

    def get_purchase_order(self):
        active_id = self._context.get('active_id', False)
        active_model = self._context.get('active_model', False)
        purchase_order_ids = self.env['purchase.order']
        group_id_name = self.group_id.name

        if active_id and active_model and active_model == 'purchase.order':
            purchase_order_id = purchase_order_ids.search([
                ('id', '=', active_id)
            ])
        else:
            if group_id_name != 'Draft':
                purchase_order_id = self.env['purchase.order'].search([
                    ('name', '=', group_id_name)
                ])
            else:
                purchase_order_id = False

        return purchase_order_id

    @api.multi
    @api.depends('origin', 'group_id')
    def compute_get_product_include(self):
        for rec in self:
            if all([
                any([
                    rec.origin,
                    rec.group_id,
                ]),
                rec.state == 'draft',
            ]):
                picking_origin = rec.env['stock.picking']
                if rec.get_picking_type_return():
                    picking_origin = picking_origin.search([
                        ('name', '=', rec.origin)
                    ])

                    order_line_origin_ids = picking_origin.pack_operation_product_ids
                else:
                    if rec.origin == rec.group_id.name:
                        po_id = rec.get_purchase_order()
                        order_line_origin_ids = po_id.order_line if po_id else po_id
                    else:
                        picking_origin = picking_origin.search([
                            ('name', '=', rec.origin)
                        ])

                        order_line_origin_ids = picking_origin.pack_operation_product_ids

                product_include_ids = rec.env['product.product']

                for order_line_origin_id in order_line_origin_ids:
                    product_include_ids += order_line_origin_id.product_id

                rec.product_include_ids = product_include_ids

    @api.multi
    @api.depends('state')
    def _compute_hide_tab_operations(self):
        for rec in self:
            rec.hide_tab_operations = False

            if rec.state in ('draft', 'confirmed', 'waiting', 'waiting_approve', 'rejected'):
                rec.hide_tab_operations = True

    @api.multi
    @api.depends('picking_type_name')
    def _compute_force_validate(self):
        for record in self:
            record.hide_force_button = False

            if record.state not in ['confirmed', 'waiting', 'partially_available'] \
                    or (record.usage_dest_location == 'supplier' and record.picking_type_code == 'outgoing') \
                    or (record.usage_dest_location == 'internal' and record.picking_type_code == 'incoming'):
                record.hide_force_button = True

    @api.multi
    @api.depends('picking_type_name')
    def _compute_readonly_operation_pack_ids(self):
        for record in self:
            record.readonly_operation_pack_ids = False
            purchase_id = record.get_purchase_order()

            if purchase_id:
                if purchase_id.type_purchase_ofm:
                    if record.state in ['confirmed', 'assigned']:
                        record.readonly_operation_pack_ids = True
                else:
                    if record.state == 'confirmed':
                        record.readonly_operation_pack_ids = True

    @api.multi
    @api.depends('picking_type_name')
    def _compute_invisible_request(self):
        for record in self:
            purchase_order_id = self.env['purchase.order'].search([
                ('name', '=', record.group_id.name)
            ])
            record.hide_request_button = False
            if record.usage_src_location != 'internal' and record.usage_dest_location != 'supplier':
                record.hide_request_button = True
            elif record.state != 'confirmed':
                record.hide_request_button = True
            elif record.is_request_created is True:
                record.hide_request_button = True
            elif not purchase_order_id.type_purchase_ofm:
                record.hide_request_button = True\

    @api.multi
    @api.depends('picking_type_name')
    def _compute_invisible_available(self):
        for record in self:
            record.hide_available_button = False
            purchase_order_id = record.get_purchase_order()

            type_purchase_ofm = purchase_order_id.type_purchase_ofm if purchase_order_id else False

            if type_purchase_ofm:
                record.hide_available_button = True
            else:
                if record.state != 'confirmed':
                    record.hide_available_button = True

    @api.multi
    @api.depends('picking_type_name')
    def _compute_hide_do_new_transfer(self):
        for record in self:
            record.hide_do_new_transfer = False
            if record.state not in ['partially_available', 'assigned']:
                record.hide_do_new_transfer = True
            elif record.usage_dest_location == 'supplier' \
                    and record.usage_src_location == 'internal':
                if record.purchase_id.type_purchase_ofm \
                        and record.not_approve_request is True:
                    record.hide_do_new_transfer = True
                else:
                    record.hide_do_new_transfer = False



    @api.multi
    @api.depends('picking_type_name')
    def _compute_hide_do_new_transfer_customer(self):
        for record in self:
            so_validate = self.env['ir.config_parameter'].search([
                ('key', '=', 'so_validate_do_new_transfer'),
            ]).value
            if so_validate.lower() == 'true':
                # location_dest_id.id = usege(customer) and sale_order = drop_ship
                if record.group_id:
                    so_obj = record.env['sale.order'].search([
                        ('procurement_group_id', '=', record.group_id.id)
                    ], order="id desc", limit=1)
                    stock_location_id = record.env.ref('stock.stock_location_customers').id
                    if (record.location_dest_id.id == stock_location_id) and (so_obj.type_sale_ofm == 1):
                        record.hide_do_new_transfer_customer = True
                    return True

            record.hide_do_new_transfer_customer = False

    def get_picking_type_return(self):
        for rec in self:
            stock_picking_return = False

            if rec.location_id.usage == 'supplier' and rec.location_dest_id.usage == 'internal':
                stock_picking_return = False
            elif rec.location_id.usage == 'internal' and rec.location_dest_id.usage == 'supplier':
                stock_picking_return = True
            elif rec.location_id.usage == 'internal' and rec.location_dest_id.usage == 'customer':
                stock_picking_return = False
            elif rec.location_id.usage == 'customer' and rec.location_dest_id.usage == 'internal':
                stock_picking_return = True

        return stock_picking_return

    @api.multi
    @api.depends('picking_type_name')
    def _compute_invisible_reverse(self):
        for record in self:
            state_not_reverse = [
                'draft',
                'confirmed',
                'assigned',
            ]
            record.reverse_invisible = True

            picking_type_return = record.get_picking_type_return()

            is_bsr = False

            if record.location_id.usage == 'customer' and record.location_dest_id.usage == 'internal':
                is_bsr = True

            if record.state == 'done' and not is_bsr:
                if (picking_type_return is False and record.origin == record.group_id.name) \
                        or picking_type_return:
                    picking_group = record.get_picking_by_group()

                    picking_not_reverse_ids = picking_group.get('picking_group_ids', False).filtered(
                        lambda rec:
                            rec.state in state_not_reverse
                    )

                    if not picking_not_reverse_ids:
                        picking_product_remain = record.get_picking_product_remain()
                        picking_reverse_ids = picking_product_remain.get('picking_reverse_ids', False)
                        picking_product_remain = picking_product_remain.get('product_remain', {})

                        if not picking_type_return:
                            for key, value in picking_product_remain.iteritems():
                                if value > 0:
                                    record.reverse_invisible = False
                                    break
                        elif picking_type_return:
                            rd_ids = picking_reverse_ids.filtered(
                                lambda rec:
                                    rec.origin == record.name
                            )

                            if rd_ids:
                                rd_product = {}

                                for rd_id in rd_ids:
                                    for pack_id in rd_id.pack_operation_product_ids:
                                        default_code = pack_id.product_id.default_code
                                        qty_done = pack_id.qty_done

                                        if default_code in rd_product:
                                            rd_product[default_code] += qty_done
                                        else:
                                            rd_product.update({
                                                default_code: qty_done
                                            })

                                for picking_id in self:
                                    for pack_id in picking_id.pack_operation_product_ids:
                                        qty_rd = rd_product.get(pack_id.product_id.default_code, 0)
                                        qty_remain = pack_id.qty_done - qty_rd

                                        if qty_remain > 0:
                                            record.reverse_invisible = False
                                            break
                                    if not record.reverse_invisible:
                                        break
                            else:
                                record.reverse_invisible = False

    def get_picking_by_group(self):
        picking_group_ids = self.env['stock.picking'].search([
            ('group_id', '=', self.group_id.id),
            ('state', '!=', 'cancel'),
        ])

        picking_current_ids = picking_group_ids.filtered(
            lambda rec:
            rec.location_id.id == self.location_id.id and
            rec.location_dest_id.id == self.location_dest_id.id
        )

        picking_reverse_ids = picking_group_ids.filtered(
            lambda rec:
            rec.location_id.id == self.location_dest_id.id and
            rec.location_dest_id.id == self.location_id.id
        )

        picking_group = {
            'picking_group_ids': picking_group_ids,
            'picking_current_ids': picking_current_ids,
            'picking_reverse_ids': picking_reverse_ids,
        }

        return picking_group

    def get_picking_by_hierarchy(self, picking_current_id=False, picking_group_ids=False):
        picking_current_ids = self.env['stock.picking']
        picking_reverse_ids = self.env['stock.picking']

        if picking_current_id.get_picking_type_return() == self.get_picking_type_return():
            if picking_current_id not in picking_current_ids:
                picking_current_ids += picking_current_id
            else:
                picking_current_ids = picking_current_id
        else:
            if picking_current_id not in picking_reverse_ids:
                picking_reverse_ids += picking_current_id
            else:
                picking_reverse_ids = picking_current_id

        picking_parent_ids = picking_group_ids.filtered(
            lambda picking_parent_rec: picking_parent_rec.origin == picking_current_id.name
        )

        if picking_parent_ids:
            for picking_parent_id in picking_parent_ids:
                picking_hierarchy = self.get_picking_by_hierarchy(picking_parent_id, picking_group_ids)
                picking_hierarchy_current_ids = picking_hierarchy.get('picking_current_ids', False)
                picking_hierarchy_reverse_ids = picking_hierarchy.get('picking_reverse_ids', False)
                if picking_hierarchy_current_ids:
                    if picking_current_ids:
                        picking_current_ids += picking_hierarchy_current_ids
                    else:
                        picking_current_ids = picking_hierarchy_current_ids
                if picking_hierarchy_reverse_ids:
                    if picking_reverse_ids:
                        picking_reverse_ids += picking_hierarchy_reverse_ids
                    else:
                        picking_reverse_ids = picking_hierarchy_reverse_ids

        return {
            'picking_current_ids': picking_current_ids,
            'picking_reverse_ids': picking_reverse_ids
        }

    def get_picking_product_remain(self):
        picking_group = self.get_picking_by_group()
        picking_hierarchy = self.get_picking_by_hierarchy(self, picking_group.get('picking_group_ids', False))
        picking_current_ids = picking_hierarchy.get('picking_current_ids', False)
        picking_reverse_ids = picking_hierarchy.get('picking_reverse_ids', False)

        product_current = {}

        for picking_id in picking_current_ids:
            for pack_id in picking_id.pack_operation_product_ids:
                default_code = pack_id.product_id.default_code
                qty_done = pack_id.qty_done

                if default_code in product_current:
                    product_current[default_code] += qty_done
                else:
                    product_current.update({
                        default_code: qty_done
                    })

        product_reverse = {}

        for picking_reverse_id in picking_reverse_ids:
            for pack_reverse_id in picking_reverse_id.pack_operation_product_ids:
                default_code_reverse = pack_reverse_id.product_id.default_code
                qty_done_reverse = pack_reverse_id.qty_done

                if default_code_reverse in product_reverse:
                    product_reverse[default_code_reverse] += qty_done_reverse
                else:
                    product_reverse.update({
                        default_code_reverse: qty_done_reverse
                    })

        product_remain = {}

        for key, value in product_current.iteritems():
            qty_done_remain = abs(value - product_reverse.get(key, 0))

            product_remain.update({
                key: qty_done_remain
            })

        return {
            'picking_current_ids': picking_current_ids,
            'picking_reverse_ids': picking_reverse_ids,
            'product_current': product_current,
            'product_reverse': product_reverse,
            'product_remain': product_remain
        }

    @api.multi
    def action_cancel(self):
        super(stock_picking, self).action_cancel()

        if len(self.move_lines) == 0:
            self.state = 'cancel'

        return True

    @api.multi
    def action_request_reverse(self):
        for record in self:
            if record._context.get('is_force_assign', False):
                record.with_context(action_request_reverse=True).force_assign()
            else:
                record.with_context(action_request_reverse=True).action_assign()

            record.state = 'waiting_approve'

            ofm_request_reverse_id = record.env['ofm.request.reverse'].create({
                'user_id': record.env.user.id,
                'branch_id': record.branch_id.id,
                'picking_id': record.id,
            })
            record.is_request_created = True

        return ofm_request_reverse_id

    @api.multi
    def action_confirm(self):
        # if not self.move_lines:
        #     raise UserError(_('Add product, please.'))

        super(stock_picking, self).action_confirm()

    def check_status_force_assign(self):
        return [
            'confirmed',
            'waiting',
            'waiting_approve'
        ]

    @api.multi
    def force_assign(self):
        print 'ofm_request_reverse_rd/models/stock.py'
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        self.mapped('move_lines').filtered(lambda move: move.state in self.check_status_force_assign()).force_assign()
        return True


class StockPackOperation(models.Model):
    _inherit = "stock.pack.operation"

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('waiting', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('partially_available', 'Partially Available'),
            ('waiting_approve', 'Waiting Approve'),
            ('rejected', 'Rejected'),
            ('assigned', 'Available'),
            ('done', 'Done')
        ],
        related='picking_id.state'
    )


class StockMove(models.Model):
    _inherit = "stock.move"

    product_uom_show = fields.Char(
        string='Unit of Measure',
        readonly=True,
        compute='_compute_product_uom_show'
    )

    state = fields.Selection(
        [
            ('draft', 'New'),
            ('cancel', 'Cancelled'),
            ('waiting', 'Waiting Another Move'),
            ('confirmed', 'Waiting Availability'),
            ('partially_available', 'Partially Available'),
            ('waiting_approve', 'Waiting Approve'),
            ('rejected', 'Rejected'),
            ('assigned', 'Available'),
            ('done', 'Done')
        ],
        string='Status',
        copy=False,
        default='draft',
        index=True,
        readonly=True,
        help="* New: When the stock move is created and not yet confirmed.\n"
             "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"
             "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to be manufactured...\n"
             "* Available: When products are reserved, it is set to \'Available\'.\n"
             "* Done: When the shipment is processed, the state is \'Done\'."
    )

    @api.multi
    @api.depends('product_uom')
    def _compute_product_uom_show(self):
        for rec in self:
            rec.product_uom_show = rec.product_uom.name

    @api.onchange('product_uom_qty')
    def onchange_check_qty_return(self):
        if self.picking_id.origin:
            picking_reverse_id = self.env['stock.picking'].search([
                ('name', '=', self.picking_id.origin),
                ('state', '!=', 'cancel'),
            ])
            picking_product_remain = picking_reverse_id.get_picking_product_remain()
            picking_product_remain = picking_product_remain.get('product_remain', {})

            if self.product_id:
                product_qty_done = picking_product_remain.get(self.product_id.default_code, False)
                if self.product_uom_qty > product_qty_done:
                    self.product_uom_qty = product_qty_done

                    message_warning = 'You input Quantity more than Quantity on Source Document'

                    self.env.user.notify_warning(
                        "Warning",
                        message_warning,
                        False
                    )

    def set_state_confirmed_unlink(self):
        if self.state == 'confirmed':
            self.update({'state': 'draft'})

    def prepare_purchase_line_id(self, vals):
        if not vals.get('purchase_line_id', False):
            location_id = self.env['stock.location']

            if vals.get('location_id', False):
                location_src_id = location_id.browse(vals.get('location_id'))
                location_src_usage = location_src_id.usage

            if vals.get('location_dest_id', False):
                location_dest_id = location_id.browse(vals.get('location_dest_id'))
                location_dest_usage = location_dest_id.usage

            if location_src_usage == 'supplier' and location_dest_usage == 'internal':
                purchase_order_id = self.env['purchase.order'].search([
                    ('name', '=', vals.get('origin'))
                ])

                purchase_order_line_id = purchase_order_id.order_line.filtered(
                    lambda rec:
                        rec.product_id.id == vals.get('product_id')
                ).id

                vals['purchase_line_id'] = purchase_order_line_id

        return vals

    @api.model
    def create(self, vals):
        vals = self.prepare_purchase_line_id(vals)

        res = super(StockMove, self).create(vals)

        return res

    @api.multi
    def unlink(self):
        self.set_state_confirmed_unlink()

        return super(StockMove, self).unlink()

    @api.multi
    def action_assign(self, no_prepare=False):
        super(StockMove, self).action_assign(no_prepare)

        for move in self:
            if move.picking_id.usage_src_location == 'internal' and move.picking_id.usage_dest_location == 'supplier':
                if self._context.get('action_request_reverse', False):
                    move.update({'state': 'waiting_approve'})


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def default_get(self, fields):
        res = super(ReturnPicking, self).default_get(fields)

        Quant = self.env['stock.quant']
        move_dest_exists = False
        product_return_moves = []
        picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        if picking:
            if picking.state != 'done':
                raise UserError(_("You may only return Done pickings"))
            for move in picking.move_lines:
                if move.scrapped:
                    continue
                if move.move_dest_id:
                    move_dest_exists = True

                quantity = move.product_id.uom_id._compute_quantity(move.product_qty, move.product_uom)
                product_return_moves.append(
                    (0, 0, {'product_id': move.product_id.id, 'quantity': quantity, 'move_id': move.id}))

            if not product_return_moves:
                raise UserError(
                    _("No products to return (only lines in Done state and not fully returned yet can be returned)!"))
            if 'product_return_moves' in fields:
                res.update({'product_return_moves': product_return_moves})
            if 'move_dest_exists' in fields:
                res.update({'move_dest_exists': move_dest_exists})
            if 'parent_location_id' in fields and picking.location_id.usage == 'internal':
                res.update({
                    'parent_location_id': picking.picking_type_id.warehouse_id and picking.picking_type_id.warehouse_id.view_location_id.id or picking.location_id.location_id.id})
            if 'original_location_id' in fields:
                res.update({'original_location_id': picking.location_id.id})
            if 'location_id' in fields:
                location_id = picking.location_id.id
                if picking.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                    location_id = picking.picking_type_id.return_picking_type_id.default_location_dest_id.id
                res['location_id'] = location_id

        return res

    return_reason_id = fields.Many2one(
        comodel_name="return.reason",
        string="Reason",
        domain=[
            ('model', '=', 'purchase.order')
        ],
    )

    @api.onchange('location_id')
    def onchange_get_return_reason(self):
        picking_id = self.env['stock.picking'].browse(self._context.get('active_id', 0))

        if picking_id:
            return_reason_model = ''
            if picking_id.usage_src_location == 'internal' and picking_id.usage_dest_location == 'customer':
                return_reason_model = 'pos.order'
            elif picking_id.usage_src_location == 'supplier' and picking_id.usage_dest_location == 'internal':
                return_reason_model = 'purchase.order'

            return {
                'domain': {
                    'return_reason_id': [
                        ('model', '=', return_reason_model),
                    ]
                }
            }

    def create_stock_picking_reverse(self):
        # TDE FIXME: store it in the wizard, stupid
        picking = self.env['stock.picking'].browse(self.env.context['active_id'])
        Quant = self.env['stock.quant']

        picking_product_remain = picking.get_picking_product_remain()
        picking_product_remain = picking_product_remain.get('product_remain')

        return_moves = self.product_return_moves.mapped('move_id')
        unreserve_moves = self.env['stock.move']
        for move in return_moves:
            to_check_moves = self.env['stock.move'] | move.move_dest_id
            while to_check_moves:
                current_move = to_check_moves[-1]
                to_check_moves = to_check_moves[:-1]
                if current_move.state not in ('done', 'cancel') and current_move.reserved_quant_ids:
                    unreserve_moves |= current_move
                split_move_ids = self.env['stock.move'].search([('split_from', '=', current_move.id)])
                to_check_moves |= split_move_ids

        if unreserve_moves:
            unreserve_moves.do_unreserve()
            # break the link between moves in order to be able to fix them later if needed
            unreserve_moves.write({'move_orig_ids': False})

        # create new picking for returned products
        picking_type_id = picking.picking_type_id.return_picking_type_id.id or picking.picking_type_id.id
        new_picking = picking.copy({
            'move_lines': [],
            'picking_type_id': picking_type_id,
            'state': 'draft',
            'origin': picking.name,
            'location_id': picking.location_dest_id.id,
            'location_dest_id': self.location_id.id,
            'return_reason_id': self.return_reason_id.id
        })
        new_picking.message_post_with_view(
            'mail.message_origin_link',
            values={'self': new_picking, 'origin': picking},
            subtype_id=self.env.ref('mail.mt_note').id
        )

        returned_lines = 0
        for return_line in self.product_return_moves:
            if not return_line.move_id:
                raise UserError(_("You have manually created product lines, please delete them to proceed"))

            if picking_product_remain.get(return_line.product_id.default_code, False):
                new_qty = picking_product_remain.get(return_line.product_id.default_code)
            else:
                if picking.get_picking_type_return():
                    new_qty = return_line.quantity
                else:
                    new_qty = False

            if new_qty:
                # The return of a return should be linked with the original's destination move if it was not cancelled
                if return_line.move_id.origin_returned_move_id.move_dest_id.id \
                        and return_line.move_id.origin_returned_move_id.move_dest_id.state != 'cancel':
                    move_dest_id = return_line.move_id.origin_returned_move_id.move_dest_id.id
                else:
                    move_dest_id = False

                returned_lines += 1
                return_line.move_id.copy({
                    'product_id': return_line.product_id.id,
                    'product_uom_qty': new_qty,
                    'picking_id': new_picking.id,
                    'state': 'draft',
                    'location_id': return_line.move_id.location_dest_id.id,
                    'location_dest_id': self.location_id.id or return_line.move_id.location_id.id,
                    'picking_type_id': picking_type_id,
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                    'origin_returned_move_id': return_line.move_id.id,
                    'procure_method': 'make_to_stock',
                    'move_dest_id': move_dest_id,
                })

        if not returned_lines:
            raise UserError(_("Please specify at least one non-zero quantity."))

        if picking.get_picking_type_return():
            new_picking.action_confirm()
            new_picking.force_assign()
        else:
            new_picking.update({
                'state': 'draft'
            })

        return new_picking.id, picking_type_id

    @api.multi
    def _create_returns(self):
        print 'ofm_request_reverse_rd/models/stock.py'
        for record in self:
            if record._context.get('active_id', False) and record._context.get('active_model', False):
                stock_picking_id = record.env[record._context.get('active_model')].browse(
                    record._context.get('active_id'))

            purchase_id = record.env['purchase.order'].search([
                ('name', '=', stock_picking_id.group_id.name)
            ])

            so_id = record.env['sale.order'].search([
                ('name', '=', stock_picking_id.group_id.name)
            ])

            invoice_ids = False

            if purchase_id:
                invoice_ids = purchase_id.invoice_ids
            elif so_id:
                invoice_ids = so_id.invoice_ids

            if not invoice_ids:
                raise except_orm(_('Error!'), _(u" Please Create Vendor Bill"))
            else:
                if not stock_picking_id.get_picking_type_return():
                    invoice_ids = invoice_ids.filtered(
                        lambda rec: rec.state == 'draft'
                    )

                    if invoice_ids:
                        raise except_orm(_('Error!'), _(u" Please Validate or Delete Vendor Bill"))

            res = record.create_stock_picking_reverse()

            stock_picking_id_new = self.env['stock.picking'].browse(res[0])
            stock_picking_id_new.update({
                'return_reason_id': self.return_reason_id.id,
            })

            return res
