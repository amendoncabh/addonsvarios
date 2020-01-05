# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.addons.decimal_precision as dp

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class OfmStockInternalMove(models.Model):
    _name = "ofm.stock.internal.move"

    name = fields.Char(
        string="Name",
        required=False,
        defualt='Draft',
    )

    group_id = fields.Many2one(
        'procurement.group',
        'Procurement Group',
        copy=False,
        readonly=True,
    )

    note = fields.Text(
        'Notes',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
    )

    move_type = fields.Selection([
        ('direct', 'Partial'),
        ('one', 'All at once')],
        'Delivery Type',
        default='direct',
        required=True,
        states={
            'done': [
                ('readonly', True)
            ],
            'cancel': [
                ('readonly', True)
            ]
        },
        help="It specifies goods to be deliver partially or all at once",
        readonly=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('assigned', 'Available'),
        ('done', 'Done')],
        string='Status',
        default='draft',
        compute='_compute_state',
        copy=False,
        index=True,
        readonly=True,
        track_visibility='onchange',
    )

    min_date = fields.Date(
        'Scheduled Date',
        compute='_compute_dates',
        inverse='_set_min_date',
        store=True,
        index=True,
        track_visibility='onchange',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        help="Scheduled time for the first part of the shipment to be processed. Setting manually a value here would set it as expected date for all the stock moves.")

    max_date = fields.Date(
        'Max. Expected Date',
        compute='_compute_dates',
        store=True,
        index=True,
        help="Scheduled time for the last part of the shipment to be processed"
    )

    company_id = fields.Many2one(
        'res.company',
        'Source Company',
        index=True,
        required=True,
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        default=lambda self: self.env.user.company_id.id,
    )

    company_dest_id = fields.Many2one(
        'res.company',
        'Destination Company',
        index=True,
        required=True,
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        default=lambda self: self.env.user.company_id.id,
    )

    branch_id = fields.Many2one(
        'pos.branch',
        "Source Branch",
        readonly=True,
        required=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        # default=lambda self: self.env.user.branch_id.id,
    )

    branch_dest_id = fields.Many2one(
        'pos.branch',
        "Destination Branch",
        readonly=True,
        required=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
    )

    ofm_move_lines = fields.One2many(
        'ofm.stock.internal.move.line',
        'ofm_stock_internal_move_id',
        string="Stock Moves",
        copy=True,
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        'Source Warehouse',
        readonly=True,
        required=True,
        related='branch_id.warehouse_id',
    )

    warehouse_dest_id = fields.Many2one(
        'stock.warehouse',
        'Destination Warehouse',
        readonly=True,
        required=True,
        related='branch_dest_id.warehouse_id',
    )

    warehouse_code = fields.Char(
        'Source Warehouse Code',
        readonly=True,
        required=True,
        related='warehouse_id.code',
    )

    warehouse_dest_code = fields.Char(
        'Destination Warehouse Code',
        readonly=True,
        required=True,
        related='warehouse_dest_id.code',
    )

    picking_type_id = fields.Many2one(
        'stock.picking.type',
        'Picking Type',
        readonly=True,
        required=True,
        related='warehouse_id.out_type_id',
    )

    picking_type_dest_id = fields.Many2one(
        'stock.picking.type',
        'Picking Type',
        readonly=True,
        required=True,
        related='warehouse_dest_id.in_type_id',
    )

    picking_type_code = fields.Selection([
        ('incoming', 'Vendors'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal')],
        related='picking_type_id.code',
        readonly=True,
    )

    picking_type_dest_code = fields.Selection([
        ('incoming', 'Vendors'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal')],
        related='picking_type_dest_id.code',
        readonly=True,
    )

    location_id = fields.Many2one(
        'stock.location',
        "Source Location",
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        required=True,
        domain=[
            ('usage', '=', 'internal')
        ],
        # related='picking_type_id.default_location_src_id',
    )

    location_dest_id = fields.Many2one(
        'stock.location',
        "Destination Location",
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        required=True,
        domain=[
            ('usage', '=', 'internal')
        ],
        # related='picking_type_dest_id.default_location_dest_id',
    )

    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Source Picking",
        required=False,
        readonly=True,
    )

    picking_dest_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Destination Picking",
        required=False,
        readonly=True,
    )

    picking_state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'),
        ('done', 'Done')],
        string='Source Picking Status',
        required=False,
        readonly=True,
        related='picking_id.state'
    )

    picking_dest_state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'),
        ('done', 'Done')],
        string='Destination Picking Status',
        required=False,
        readonly=True,
        related='picking_dest_id.state'
    )

    @api.one
    @api.depends('ofm_move_lines.date_expected')
    def _compute_dates(self):
        self.min_date = min(self.ofm_move_lines.mapped('date_expected') or [False])
        self.max_date = max(self.ofm_move_lines.mapped('date_expected') or [False])

    @api.multi
    @api.depends('picking_id.state', 'picking_dest_id.state')
    def _compute_state(self):
        for record in self:
            if record.picking_id and record.picking_dest_id:
                # have both
                if record.picking_state == 'cancel' or record.picking_dest_state == 'cancel':
                    record.action_cancel()
                    record.state = 'cancel'
                elif record.picking_state == 'done' and record.picking_dest_state == 'done':
                    if record.state != 'done':
                        record.force_done()
                    record.state = 'done'
                elif record.picking_state == 'done' and record.picking_dest_state == 'assigned':
                    record.state = 'assigned'
                else:
                    record.state = 'assigned'
            elif record.picking_id:
                # have only source
                if record.picking_state == 'cancel':
                    record.action_cancel()
                    record.state = 'cancel'
                else:
                    record.state = 'assigned'
            else:
                # no picking ether source and dest
                record.state = 'draft'

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.branch_id = None
        self.branch_dest_id = None

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        self.location_id = None
        self.ofm_move_lines = None

    @api.onchange('branch_dest_id')
    def _onchange_branch_dest_id(self):
        self.location_dest_id = None

    @api.one
    def _set_min_date(self):
        self.ofm_move_lines.write({'date_expected': self.min_date})

    @api.multi
    def force_assign(self):
        # TDE CLEANME: removed return value
        partner_id = self.env['res.partner'].search([('ref', '=', '0001')], limit=1, order='id desc').id

        for record in self:
            if record.picking_id and record.picking_state != 'assigned':
                record.picking_id.partner_id = partner_id
                record.picking_id.action_assign()
                record.picking_id.force_assign()
                
                for pack in record.picking_id.pack_operation_ids:
                    if pack.product_qty > 0:
                        pack.write({'qty_done': pack.product_qty})
                    else:
                        pack.unlink()

                record.picking_id.do_transfer()
            if record.picking_state == 'done' and not record.picking_dest_id:
                record.create_destination_stock_picking()
            if record.picking_dest_id and record.picking_dest_state not in ('assigned', 'done', 'cancel'):
                record.picking_dest_id.partner_id = partner_id
                record.picking_dest_id.action_assign()

            record.mapped('ofm_move_lines').filtered(lambda move: move.state in ['draft']).action_assign()

    @api.multi
    def action_assign(self):
        for record in self:
            if record.picking_id and record.picking_state not in ('assigned', 'done', 'cancel'):
                record.picking_id.action_assign()
            if record.picking_id and record.picking_state == 'assigned':
                record.picking_id.do_transfer()
            if record.picking_state == 'done' and not record.picking_dest_id:
                record.create_destination_stock_picking()
            if record.picking_dest_id and record.picking_dest_state not in ('assigned', 'done', 'cancel'):
                record.picking_dest_id.action_assign()
            record.mapped('ofm_move_lines').filtered(
                lambda move: move.state not in ('assigned', 'done', 'cancel')).action_assign()

    @api.multi
    def action_cancel(self):
        for record in self:
            if record.picking_id and record.picking_state != 'cancel':
                record.picking_id.action_cancel()
            if record.picking_dest_id and record.picking_dest_state != 'cancel':
                record.picking_dest_id.action_cancel()
            if record.picking_state == 'cancel' or record.picking_dest_state == 'cancel':
                record.mapped('ofm_move_lines').filtered(
                    lambda move: move.state in ['draft', 'assigned']).action_cancel()
        return True

    @api.multi
    def force_done(self):
        for record in self:
            if record.state != 'done':
                record.mapped('ofm_move_lines').filtered(lambda move: move.state not in ('done', 'cancel')).force_done()
                record.write({'state': 'done'})

    @api.multi
    def action_confirm(self):
        stock_picking = self.env['stock.picking']
        transit = self.env.ref('stock.stock_location_inter_wh')

        for record in self:
            if record.branch_id.id == record.branch_dest_id.id:
                raise UserError(_('Source and Destination branch cannot be the same.'))

            if not record.ofm_move_lines:
                raise UserError(_('Please add an initial demand line.'))

            record.name = record.branch_id.warehouse_id.int_type_id.sequence_id.with_context({
                'date': record.min_date
            }).next_by_id()

            record.group_id = self.env["procurement.group"].create({
                'name': record.name,
            })

            src_vals = self.prepare_stock_picking(record, record.branch_id.id, record.picking_type_id.id,
                                                  record.location_id.id, transit.id)

            record.picking_id = stock_picking.create(src_vals)

            record.force_assign()
        return True

    def prepare_stock_move(self, stock, move, branch_id, picking_type_id, location_id, location_dest_id):
        return {
            'branch_id': branch_id,
            'picking_type_id': picking_type_id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'product_id': move.product_id.id,
            'name': move.product_id.name,
            'group_id': stock.group_id.id,
            'product_uom': move.product_uom.id,
            'product_uom_qty': move.product_qty,
            'date_expected': move.date_expected,
        }

    def prepare_stock_picking(self, stock, branch_id, picking_type_id, location_id, location_dest_id):
        move_vals = []
        for move in stock.ofm_move_lines:
            move_vals.append([0, False, self.prepare_stock_move(stock, move, branch_id, picking_type_id, location_id,
                                                                location_dest_id)])
        return {
            'branch_id': branch_id,
            'company_id': stock.company_id.id,
            'origin': stock.name,
            'group_id': stock.group_id.id,
            'min_date': stock.min_date,
            'max_date': stock.max_date,
            'note': stock.note,
            'move_type': stock.move_type,
            'picking_type_id': picking_type_id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_lines': move_vals,
        }

    @api.one
    def create_destination_stock_picking(self):
        if not self.picking_dest_id:
            stock_picking = self.env['stock.picking']
            transit = self.env.ref('stock.stock_location_inter_wh')

            dest_vals = self.prepare_stock_picking(self, self.branch_dest_id.id, self.picking_type_dest_id.id,
                                                   transit.id, self.location_dest_id.id)
            self.picking_dest_id = stock_picking.create(dest_vals)

    @api.multi
    def write(self, vals):
        branch_id = vals.get('branch_id') or self.branch_id.id
        branch_dest_id = vals.get('branch_dest_id') or self.branch_dest_id.id

        if branch_id and branch_dest_id and branch_id == branch_dest_id:
            raise UserError(_('Source and Destination branch cannot be the same.'))

        res = super(OfmStockInternalMove, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        if vals.get('branch_id') == vals.get('branch_dest_id'):
            raise UserError(_('Source and Destination branch cannot be the same.'))
        if not vals.get('name'):
            vals.update({'name': 'Draft'})
        return super(OfmStockInternalMove, self).create(vals)

    @api.multi
    def unlink(self):
        self.action_cancel()
        self.mapped('ofm_move_lines').unlink()  # Checks if moves are not done
        return super(OfmStockInternalMove, self).unlink()


class OfmStockInternalMoveLine(models.Model):
    _name = "ofm.stock.internal.move.line"

    def _default_location_from_context(self):
        if not self._context.get('location_id', False):
            raise UserError(_('Please choose Source Branch and Source Location.'))
        return self._context.get('location_id', False)

    ofm_stock_internal_move_id = fields.Many2one(
        comodel_name="ofm.stock.internal.move",
        string="ofm stock internal move id",
    )

    state = fields.Selection([
        ('draft', 'New'),
        ('cancel', 'Cancelled'),
        ('assigned', 'Available'),
        ('done', 'Done')],
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

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        domain=[
            ('type', 'in', ['product', 'consu']),
            ('qty_available', '>', 0)
        ],
        index=True,
        required=True,
        states={
            'done': [
                ('readonly', True)
            ],
            'cancel': [
                ('readonly', True)
            ]
        },
    )

    product_uom = fields.Many2one(
        'product.uom',
        string='Unit of Measure',
        readonly=True,
        related='product_id.uom_id',
    )

    qty_available = fields.Float(
        string='Quantity On Hand',
        readonly=True,
        compute='_compute_product_qty',
        store=True,
    )

    product_qty = fields.Float(
        'Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
        states={
            'done': [
                ('readonly', True)
            ],
            'cancel': [
                ('readonly', True)
            ]
        },
        readonly=False,
    )

    date_expected = fields.Date(
        'Expected Date',
        default=fields.Datetime.now,
        index=True,
        required=True,
        states={
            'done': [
                ('readonly', True)
            ],
            'cancel': [
                ('readonly', True)
            ]
        },
        help="Scheduled date for the processing of this move",
    )

    location_id = fields.Many2one(
        'stock.location',
        "Source Location",
        readonly=True,
        default=_default_location_from_context,
    )

    @api.multi
    @api.depends('product_id')
    def _compute_product_qty(self):
        for record in self:
            if record.product_id:
                value = record.product_id.with_context({
                    'location': record.location_id.id,
                })._product_available()

                product_available = value.get(record.product_id.id, False)
                record.qty_available = product_available.get('qty_available', 0)
                record.product_qty = record.qty_available

            else:
                record.qty_available = 0
                record.product_qty = 0

    @api.onchange('product_qty')
    def onchange_check_product_qty(self):
        if any([
            self.product_qty > self.qty_available,
            self.product_qty < 0
        ]):
            self.product_qty = self.qty_available

            self.env.user.notify_warning(
                "Warning",
                'Quantity more than Quantity On Hand or Quantiy less than 0',
                False
            )

    @api.onchange('product_id')
    def onchange_product_qty(self):
        if self.product_id and self.location_id:
            value = self.product_id.with_context({'location': self.location_id.id})._product_available()
            product_available = value.get(self.product_id.id, False)
            self.qty_available = product_available.get('qty_available', 0)
            self.product_qty = self.qty_available
        else:
            self.qty_available = 0
            self.product_qty = 0

    @api.multi
    def action_assign(self):
        for record in self:
            record.write({'state': 'assigned'})

    @api.multi
    def action_cancel(self):
        """ Cancels the moves and if all moves are cancelled it cancels the picking. """
        # TDE DUMB: why is cancel_procuremetn in ctx we do quite nothing ?? like not updating the move ??

        if any(move.state == 'done' for move in self):
            raise UserError(_('You cannot cancel a stock move that has been set to \'Done\'.'))

        for record in self:
            record.write({'state': 'cancel'})
        return True

    @api.multi
    def force_done(self):
        for record in self:
            record.write({'state': 'done'})

    @api.multi
    def unlink(self):
        if any(move.state not in ('draft', 'cancel') for move in self):
            raise UserError(_('You can only delete draft moves.'))
        return super(OfmStockInternalMoveLine, self).unlink()
