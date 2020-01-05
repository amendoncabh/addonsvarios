from odoo import api, fields, models, _
from odoo.exceptions import UserError, except_orm

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, except_orm

_logger = logging.getLogger(__name__)


class Warehouse(models.Model):
    _inherit = "stock.warehouse"
    # _description = "OFM Warehouse"

    pos_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='POS Type',
        readonly=True,
    )

    pos_return_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='POS Return Type',
        readonly=True,
    )

    in_return_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='In Return Type',
        readonly=True,
    )

    out_return_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Out Return Type',
        readonly=True,
    )

    in_use_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Internal Usage Type",
        readonly=True,
    )

    in_use_return_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Internal Usage Return Type",
        readonly=True,
    )

    def _get_picking_type_values_ext(self, reception_steps, delivery_steps, pack_stop_location):

        input_loc, output_loc = self._get_input_output_locations(reception_steps, delivery_steps)

        vendor_location = self.env.ref('stock.stock_location_suppliers')
        customer_location = self.env.ref('stock.stock_location_customers')
        employee_location = self.env.ref('stock.stock_location_employee')

        return {
            'in_type_id': {
                'default_location_src_id': vendor_location.id
            },
            'out_type_id': {
                'default_location_dest_id': vendor_location.id
            },
            'in_return_type_id': {
                'default_location_src_id': vendor_location.id,
                'default_location_dest_id': input_loc.id
            },
            'out_return_type_id': {
                'default_location_src_id': output_loc.id,
                'default_location_dest_id': vendor_location.id
            },
            'pos_type_id': {
                'default_location_src_id': output_loc.id,
                'default_location_dest_id': customer_location.id
            },
            'pos_return_type_id': {
                'default_location_src_id': customer_location.id,
                'default_location_dest_id': input_loc.id
            },
            'in_use_type_id': {
                'default_location_src_id': output_loc.id,
                'default_location_dest_id': employee_location.id
            },
            'in_use_return_type_id': {
                'default_location_src_id': employee_location.id,
                'default_location_dest_id': input_loc.id
            }
        }

    def _get_sequence_values(self):
        sequence_values = super(Warehouse, self)._get_sequence_values()

        for item in sequence_values:
            sequence_values[item].update({
                'company_id': self.company_id.id,
            })

        company_code = self._context.get('branch_code', False)
        company_code = company_code and company_code or self.company_id.company_code_account + '00'

        sequence_suffix = company_code + '%(y)s%(month)s'

        sequence_values['in_type_id']['prefix'] = 'RD-' + sequence_suffix
        sequence_values['int_type_id']['prefix'] = 'INT-' + sequence_suffix
        sequence_values['out_type_id']['prefix'] = 'BDL-' + sequence_suffix

        sequence_values.update({
            'pos_type_id': {
                'name': self.name + ' ' + _('Picking POS'),
                'prefix': 'FDL-' + sequence_suffix,
                'padding': 5,
                'company_id': self.company_id.id,
            },
            'pos_return_type_id': {
                'name': self.name + ' ' + _('Picking POS Return'),
                'prefix': 'FSR-' + sequence_suffix,
                'padding': 5,
                'company_id': self.company_id.id,
            },
            'in_return_type_id': {
                'name': self.name + ' ' + _('Sequence in Return'),
                'prefix': 'RT-' + sequence_suffix,
                'padding': 5,
                'company_id': self.company_id.id,
            },
            'out_return_type_id': {
                'name': self.name + ' ' + _('Sequence out Return'),
                'prefix': 'BSR-' + sequence_suffix,
                'padding': 5,
                'company_id': self.company_id.id,
            },
            'in_use_type_id': {
                'name': self.name + ' ' + _('Internal Usage'),
                'prefix': 'INU-' + sequence_suffix,
                'padding': 5,
                'company_id': self.company_id.id,
            },
            'in_use_return_type_id': {
                'name': self.name + ' ' + _('Internal Usage Return'),
                'prefix': 'RIN-' + sequence_suffix,
                'padding': 5,
                'company_id': self.company_id.id,
            }
        })

        return sequence_values

    def create_sequences_and_picking_types(self):
        warehouse_data = super(Warehouse, self).create_sequences_and_picking_types()

        IrSequenceSudo = self.env['ir.sequence'].sudo()
        PickingType = self.env['stock.picking.type']

        # choose the next available color for the picking types of this warehouse
        all_used_colors = [res['color'] for res in
                           PickingType.search_read([('warehouse_id', '!=', False), ('color', '!=', False)], ['color'],
                                                   order='color')]
        available_colors = [zef for zef in [0, 3, 4, 5, 6, 7, 8, 1, 2] if zef not in all_used_colors]
        color = available_colors and available_colors[0] or 0

        # suit for each warehouse: Picking POS
        max_sequence = PickingType.search_read([
            ('sequence', '!=', False)
        ],
            ['sequence'],
            limit=1,
            order='sequence desc'
        )
        max_sequence = max_sequence and max_sequence[0]['sequence'] or 0

        sequence_data = self._get_sequence_values()

        create_data = {
            'pos_type_id': {
                'name': _('POS Order'),
                'code': 'outgoing',
                'use_create_lots': False,
                'use_existing_lots': False,
                'sequence': max_sequence + 6,
            },
            'pos_return_type_id': {
                'name': _('POS Return Order'),
                'code': 'incoming',
                'use_create_lots': False,
                'use_existing_lots': False,
                'sequence': max_sequence + 7,
            },
            'in_return_type_id': {
                'name': _('Receive Return'),
                'code': 'outgoing',
                'use_create_lots': True,
                'use_existing_lots': False,
                'sequence': max_sequence + 8,
            },
            'out_return_type_id': {
                'name': _('Delivery Orders Return'),
                'code': 'incoming',
                'use_create_lots': False,
                'use_existing_lots': True,
                'sequence': max_sequence + 9,
            },
            'in_use_type_id': {
                'name': _('Internal Usage'),
                'code': 'outgoing',
                'use_create_lots': False,
                'use_existing_lots': False,
                'sequence': max_sequence + 10,
            },
            'in_use_return_type_id': {
                'name': _('Internal Usage Return'),
                'code': 'incoming',
                'use_create_lots': False,
                'use_existing_lots': False,
                'sequence': max_sequence + 11,
            }
        }

        operation_type_list = [
            'pos_type_id',
            'pos_return_type_id',
            'in_return_type_id',
            'out_return_type_id',
            'in_use_type_id',
            'in_use_return_type_id',
        ]

        data = self._get_picking_type_values_ext(self.reception_steps, self.delivery_steps, self.wh_pack_stock_loc_id)
        for field_name, values in data.iteritems():
            if create_data.get(field_name, False):
                data[field_name].update(create_data[field_name])

        for picking_type, values in data.iteritems():
            if picking_type in operation_type_list:
                sequence = IrSequenceSudo.create(sequence_data[picking_type])
                values.update(warehouse_id=self.id, color=color, sequence_id=sequence.id)
                warehouse_data[picking_type] = PickingType.create(values).id

        PickingType.browse(warehouse_data['in_type_id']).write({
            'default_location_src_id': data['in_type_id']['default_location_src_id'],
            'return_picking_type_id': warehouse_data['in_return_type_id']
        })
        PickingType.browse(warehouse_data['in_return_type_id']).write({
            'return_picking_type_id': warehouse_data['in_type_id']
        })
        PickingType.browse(warehouse_data['out_type_id']).write({
            'default_location_dest_id': data['out_type_id']['default_location_dest_id'],
            'return_picking_type_id': warehouse_data['out_return_type_id']
        })
        PickingType.browse(warehouse_data['out_return_type_id']).write({
            'return_picking_type_id': warehouse_data['out_type_id']
        })
        PickingType.browse(warehouse_data['pos_type_id']).write({
            'return_picking_type_id': warehouse_data['pos_return_type_id']
        })
        PickingType.browse(warehouse_data['pos_return_type_id']).write({
            'return_picking_type_id': warehouse_data['pos_type_id']
        })
        PickingType.browse(warehouse_data['in_use_type_id']).write({
            'return_picking_type_id': warehouse_data['in_use_return_type_id']
        })
        PickingType.browse(warehouse_data['in_use_return_type_id']).write({
            'return_picking_type_id': warehouse_data['in_use_type_id']
        })

        return warehouse_data


class Orderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"

    def _default_branch(self):
        return self.env.user.branch_id

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        default=_default_branch,
    )

    updateon = fields.Datetime(
        'UpDateOn'
    )

    transferdate = fields.Datetime(
        'TransferDate'
    )

    virtual_available = fields.Float(
        string='Forecast Quantity',
        compute='_compute_forecast',
    )

    qty_available = fields.Float(
        string='Quantity On Hand',
        compute='_compute_forecast',
    )

    incoming_qty = fields.Float(
        string='Incoming',
        compute='_compute_forecast'
    )

    incoming_qty_po = fields.Float(
        string='Incoming PO',
        compute='_compute_forecast'
    )

    incoming_qty_pr = fields.Float(
        string='Incoming PR Sent',
        compute='_compute_forecast'
    )

    incoming_qty_pr = fields.Float(
        string='Incoming PR Sent',
        compute='_compute_forecast'
    )

    outgoing_qty = fields.Float(
        string='Outgoing',
        compute='_compute_forecast'
    )

    @api.multi
    @api.depends('product_id', 'location_id')
    def _compute_forecast(self):
        for rec in self:
            compute_quantities = rec.product_id.with_context({
                'branch_id': rec.branch_id.id,
                'location': rec.location_id.id
            })._compute_quantities_dict(
                rec._context.get('lot_id'),
                rec._context.get('owner_id'),
                rec._context.get('package_id'),
                rec._context.get('from_date'),
                rec._context.get('to_date')
            )

            product_forecast = compute_quantities.get(rec.product_id.id, False)
            if product_forecast:
                incoming_qty = product_forecast.get('incoming_qty', 0) + product_forecast.get('incoming_qty_pr_sent', 0)

                rec.virtual_available = product_forecast.get('virtual_available', 0)
                rec.qty_available = product_forecast.get('qty_available', 0)
                rec.incoming_qty = incoming_qty
                rec.incoming_qty_po = product_forecast.get('incoming_qty', 0)
                rec.incoming_qty_pr = product_forecast.get('incoming_qty_pr_sent', 0)
                rec.outgoing_qty = product_forecast.get('outgoing_qty', 0)

    @api.multi
    def _get_buy_other_pull_rule_by_route_id(self, route_id):
        if route_id is None:
            raise UserError(_("Can't find any generic Buy route."))
        return {
            'name': self._format_routename(_(' Buy')),
            'location_id': self.in_type_id.default_location_dest_id.id,
            'route_id': route_id,
            'action': 'buy',
            'picking_type_id': self.in_type_id.id,
            'warehouse_id': self.id,
            'group_propagation_option': 'none',
        }

    @api.multi
    def create_routes(self):
        res = super(Warehouse, self).create_routes()
        try:
            base_route_id = self.env['ir.model.data'].get_object_reference('purchase', 'route_warehouse0_buy')[1]
            buy_route_ids = self.env['stock.location.route'].search(
                [('name', 'like', _('Buy')), ('id', '!=', base_route_id)])
        except:
            buy_route_ids = False

        if buy_route_ids:
            for route_id in buy_route_ids:
                buy_pull_vals = self._get_buy_other_pull_rule_by_route_id(route_id.id)
                self.env['procurement.rule'].create(buy_pull_vals)
        return res

    @api.multi
    def action_on_hand(self):
        return True

    @api.multi
    def action_forecast(self):
        return True

    @api.multi
    def action_incoming_qty(self):
        return True

    @api.multi
    def action_outgoing_qty(self):
        return True

    def check_duplicate_reordering_rule(self, vals):
        stock_warehouse_orderpoint = self.env['stock.warehouse.orderpoint']

        if vals.get('branch_id', False):
            branch_id_input = vals.get('branch_id')
        else:
            branch_id_input = self.branch_id.id

        if vals.get('product_id', False):
            product_id_input = vals.get('product_id')
        else:
            product_id_input = self.product_id.id

        if self.id:
            order_point_search = [
                ('id', '!=', self.id),
                ('branch_id', '=', branch_id_input),
                ('product_id', '=', product_id_input)
            ]
        else:
            order_point_search = [
                ('branch_id', '=', branch_id_input),
                ('product_id', '=', product_id_input)
            ]

        order_point_id = stock_warehouse_orderpoint.search(order_point_search)

        if order_point_id:
            raise except_orm(_('Warning!'), 'Product is Duplicate!')

    @api.model
    def create(self, vals):
        self.check_duplicate_reordering_rule(vals)

        return super(Orderpoint, self).create(vals)

    @api.multi
    def write(self, vals):
        for rec in self:
            rec.check_duplicate_reordering_rule(vals)

            return super(Orderpoint, rec).write(vals)
