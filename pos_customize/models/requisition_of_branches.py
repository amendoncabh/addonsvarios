# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

import odoo.addons.decimal_precision as dp

from odoo import api, fields, models, _
from odoo.exceptions import UserError

__author__ = 'papatpon'


class RequisitionBranches(models.Model):
    _name = 'requisition.branches'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Requisition Branches"
    _order = 'date desc, id desc'

    user_id = fields.Many2one(
        'res.users',
        readonly=True,
        string='Confirm User',
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        readonly=True,
        string='Company User',
        copy=False,
    )
    user_allow_id = fields.Many2one(
        'res.users',
        readonly=True,
        string='Allow User',
        copy=False,
    )
    name = fields.Char(
        'Number',
        default=lambda self: _('New'),
        track_visibility='onchange',
        readonly=True,
        copy=False,
    )
    date = fields.Date(
        string='Request Date',
        default=fields.Datetime.now,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        readonly=True,
    )
    date_schedule = fields.Date(
        string='Schedule Date',
        default=fields.Datetime.now,
        # default=lambda *a: (datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'),
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        readonly=True,
        copy=False
    )
    date_allowable_submit = fields.Date(
        string='Allowable Date',
        readonly=True,
        track_visibility='onchange',
        copy=False
    )
    pos_branch = fields.Many2one(
        'pos.branch',
        'Branch Location',
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        copy=False,
    )
    branch_phone = fields.Char(
        string='Phone',
        required=True,
    )

    picking_in_id = fields.Many2one(
        'stock.picking',
        'Picking In',
        readonly=True,
        track_visibility='onchange',
        copy=False,
    )
    picking_out_id = fields.Many2one(
        'stock.picking',
        'Picking Out',
        readonly=True,
        track_visibility='onchange',
        copy=False,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirm'),
            ('passed', 'Pass'),
            ('waiting', 'Waiting Receive'),
            ('done', 'Done'),
            ('canceled', 'Canceled'),
        ],
        string='Status',
        readonly=True,
        track_visibility='onchange',
        default='draft',
    )
    requisition_branches_line_ids = fields.One2many(
        'requisition.branches.line',
        'request_id',
        string='Requisition Branches Line',
        states={'canceled': [('readonly', True)], 'done': [('readonly', True)]},
    )
    note = fields.Text(
        'Notes',
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        copy=False,
    )
    procurement_group_id = fields.Many2one(
        'procurement.group',
        'Procurement Group',
        copy=False
    )
    product_template_created = fields.Boolean(
        'Product template Created',
        default=False,
        copy=False,
    )
    product_template_id = fields.Many2one(
        'pos_product.template',
        'Product Template Select',
        copy=False
    )
    requisition_branches_round_id = fields.Many2one(
        'requisition.branches.round',
        'Requisition Branch Round',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        copy=False,
    )
    picking_out_ids = fields.One2many(
        'stock.picking',
        'request_out_id',
        'Pickings Out of RB',
        readonly=True,
    )
    picking_in_ids = fields.One2many(
        'stock.picking',
        'request_in_id',
        'Pickings In of RB',
        readonly=True,
    )
    count_picking_out_ids = fields.Integer(
        'Picking Out Ids',
        compute='_get_picking_out_count'
    )
    count_picking_in_ids = fields.Integer(
        'Picking In Ids',
        compute='_get_picking_in_count'
    )

    @api.multi
    def _get_picking_out_count(self):
        for requisition_branch in self:
            count_picking_out_ids = len(requisition_branch.picking_out_ids)
            requisition_branch.count_picking_out_ids = count_picking_out_ids

    @api.multi
    def _get_picking_in_count(self):
        for requisition_branch in self:
            count_picking_in_ids = len(requisition_branch.picking_in_ids)
            requisition_branch.count_picking_in_ids = count_picking_in_ids

    @api.onchange('pos_branch')
    def onchange_domain_template_product(self):

        domain = [('check_active', '=', True)]

        requisition_product_template_ids = []

        for item in self.pos_branch.requisition_product_template_ids:
            for template_line in item.product_ids:
                requisition_product_template_ids.append(template_line.product_id.id)

        domain += [('id', 'in', requisition_product_template_ids)]

        return {
            'domain': {
                'product_template_id': domain
            }
        }

    @api.multi
    def get_origin_name_picking(self, request_id):

        requisition_round_id = request_id.requisition_branches_round_id
        requisition_round_name = '-' + requisition_round_id.name if requisition_round_id else ""
        product_template_name = '-' + request_id.product_template_id.name if request_id.product_template_id else ""
        pos_branch_name = '-' + request_id.pos_branch.name if request_id.pos_branch else ""

        origin_name = request_id.name + \
                      pos_branch_name + \
                      requisition_round_name + \
                      product_template_name

        return origin_name

    @api.multi
    def search_picking_existing(self, move, field_in_picking=None):
        pick_obj = self.env["stock.picking"]
        picks = pick_obj.search([
            ('group_id', '=', move.group_id.id,),
            ('printed', '=', False),
            (field_in_picking, '!=', False),
            ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])
        ], limit=1)

        return picks

    @api.multi
    def check_exiting_procument_group(self, order):

        if not order.procurement_group_id:
            vals = order._prepare_procurement_group()
            procurement_group_id = self.env["procurement.group"].create(vals).id
            order.procurement_group_id = procurement_group_id
        else:
            procurement_group_id = order.procurement_group_id.id

        return procurement_group_id

    @api.multi
    def view_pickings_list(self, field_in_picking=None):
        group_ids = set([proc.procurement_group_id.id for proc in self if proc.procurement_group_id])
        group_ids_str = ','.join(map(str, list(group_ids)))
        domain = "[('group_id','in',[%s]),('%s', '!=', False)]" % (group_ids_str, field_in_picking)
        print domain
        return {
            'name': _("Pickings for Groups"),
            'view_mode': 'tree,form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'domain': domain,
        }

    @api.multi
    def rb_view_pickings_out(self):
        fields_name = self.env.context['field_picking']
        return self.view_pickings_list(fields_name)

    @api.multi
    def rb_view_pickings_in(self):
        fields_name = self.env.context['field_picking']
        return self.view_pickings_list(fields_name)

    @api.model
    def create(self, vals):

        if self._context is None:
            self._context = {}

        if self.env.user.pos_config.branch_id.id:
            vals['pos_branch'] = self.env.user.pos_config.branch_id.id
        vals['company_id'] = self.env.user.company_id.id
        result = super(RequisitionBranches, self).create(vals)
        return result

    @api.multi
    def write(self, values):
        if not values:
            values = {}

        if 'requisition_branches_line_ids' in values \
                and values.get('requisition_branches_line_ids') \
                and self.state != 'draft':
            for line_id in values.get('requisition_branches_line_ids'):
                if line_id[0] == 2:
                    raise UserError(_(u"Can't Remove Line when state is not draft"))
                if line_id[0] == 0:
                    raise UserError(_(u"Can't Create Line when state is not draft"))

        return super(RequisitionBranches, self).write(values)

    @api.multi
    def _prepare_picking_assign(self, move, request_id, field_picking, picks=None):
        """ Prepares a new picking for this move as it could not be assigned to
        another picking. This method is designed to be inherited.
        """
        values = {
            'origin': move.origin,
            'company_id': move.company_id and move.company_id.id or False,
            'move_type': move.group_id and move.group_id.move_type or 'direct',
            'group_id': move.group_id.id,
            'partner_id': move.partner_id.id or False,
            'picking_type_id': move.picking_type_id and move.picking_type_id.id or False,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            field_picking: request_id,
        }

        if picks and 'out' not in field_picking:
            pick = picks

            if pick.fleet_vehicle_id:
                values.update({'fleet_vehicle_id': pick.fleet_vehicle_id.id})
            if pick.driver_id:
                values.update({'driver_id': pick.driver_id.id})
            if pick.driver_assistant_id:
                values.update({'driver_assistant_id': pick.driver_assistant_id.id})
        return values

    @api.multi
    def prepare_requisition_line(self, product_id, request_id):
        """ Prepares a new picking for this move as it could not be assigned to
        another picking. This method is designed to be inherited.
        """
        name = product_id.name_get()[0][1]
        if product_id.description_sale:
            name += '\n' + product_id.description_sale

        values = {
            'product_id': product_id.id,
            'qty': 0,
            'product_uom': product_id.uom_id.id,
            'name': name,
            'request_id': request_id.id,
        }

        self.create_requisition_line(values)

    @api.multi
    def create_requisition_line(self, values):
        self.env['requisition.branches.line'].create(values)

    @api.model
    def _prepare_procurement_group(self):
        res = {'name': self.name}
        res.update({'move_type': 'direct'})
        return res

    @api.multi
    def action_create_template(self):
        for order in self:
            product_template = order.product_template_id
            for item in product_template.product_ids:
                self.prepare_requisition_line(item.product_id, order)
            order.write({'product_template_created': True})
        return True

    def action_move_confirm(self, cr, uid, move, context=None):
        self.pool.get('stock.move').action_confirm(cr, uid, move, context=None)

    @api.multi
    def get_rb_name(self, order):

        if order.name == 'New':
            return order.env['ir.sequence'].next_by_code(order._name) or 'New'

    @api.multi
    def action_confirm(self):
        for order in self:

            order.name = order.get_rb_name(order)

            msg = []
            if not order.requisition_branches_line_ids.ids:
                msg += [_(u"requisition branches line is empty")]
            if order.requisition_branches_line_ids.ids:
                for requisition_branches_line_id in order.requisition_branches_line_ids:
                    if requisition_branches_line_id.qty == 0:
                        requisition_branches_line_id.unlink()
            if not order.pos_branch.id:
                msg += [_(u"Branch Location is Null")]

            result = [x for x in msg if x]
            if result:
                all_message = '\n'.join(result)
                raise UserError(_(u"Can't not confirm when\n%s") % all_message)

            if order.requisition_branches_line_ids.ids:
                for requisition_branches_line_id in order.requisition_branches_line_ids:
                    requisition_branches_line_id.qty_allow = requisition_branches_line_id.qty

            order.state = 'confirmed'
            order.user_id = self.env.user.id

    @api.multi
    def action_waiting(self):
        vals = {'state': 'waiting'}
        self.update(vals)

    @api.multi
    def action_done(self):
        vals = {'state': 'done'}
        self.update(vals)

    @api.multi
    def action_cancel(self):
        for order in self:
            if order.picking_out_id:
                if order.picking_out_id.state == 'done':
                    raise UserError(_(u"Can't Cancel Because Picking Out is Done"))
                else:
                    order.picking_out_id.action_cancel()

            vals = {'state': 'canceled'}
            order.update(vals)

    @api.multi
    def action_approve(self, context=None):
        for order in self:
            move_obj = self.env['stock.move']
            pick_obj = order.env["stock.picking"]

            qty_allow_all = 0

            for requisition_branches_line_id in order.requisition_branches_line_ids:
                qty_allow_all += requisition_branches_line_id.qty_allow
            if not qty_allow_all:
                raise UserError(_(u"Can't Approve Because Quantity Allow is equal Zero"))

            # picking in of center company #############################################################################################################################

            company_obj = order.env.user.company_id

            source_location_id = company_obj.warehouse_id.wh_output_stock_loc_id.id
            transit_location_id = company_obj.location_transit_id.id
            picking_type_out_id = company_obj.warehouse_id.int_type_id.id
            move_ids = []

            for line in order.requisition_branches_line_ids:

                if line.qty_allow:
                    origin_name = self.get_origin_name_picking(order)

                    procurement_group_id = self.check_exiting_procument_group(line.request_id)
                    model_line_name = order.requisition_branches_line_ids._name
                    move_dict = self.env[model_line_name]._run_move_create(
                        order,
                        procurement_group_id,
                        origin_name,
                        company_obj.id,
                        source_location_id,
                        transit_location_id,
                        picking_type_out_id,
                        company_obj.warehouse_id.id,
                        line.qty_allow,
                        line.product_id,
                    )

                    move = move_obj.create(move_dict)
                    move_ids += [move.id]

                    picks = order.search_picking_existing(move, 'request_out_id')
                    if picks:
                        pick = picks[0]
                    else:
                        values = self._prepare_picking_assign(move, order.id, 'request_out_id')
                        pick = pick_obj.create(values)

                    move.write({'picking_id': pick.id})
                    order.write({'picking_out_id': pick.id})
                    picking_id = pick
                    picking_id.write({
                        'min_date': line.request_id.date_schedule
                    })

            if move_ids:
                self.action_move_confirm(move_ids)

                picking_id.force_assign()

                order.state = 'passed'
                import time
                order.date_allowable_submit = time.strftime("%Y-%m-%d")
                order.user_allow_id = self.env.user.id

    @api.multi
    def action_create_picking_diff(self):
        order = self
        move_obj = self.env['stock.move']
        pick_obj = order.env["stock.picking"]
        company_obj = order.env.user.company_id

        source_location_id = company_obj.warehouse_id.wh_output_stock_loc_id.id
        transit_location_id = company_obj.location_transit_id.id
        picking_type_out_id = company_obj.warehouse_id.int_type_id.id
        move_ids = []
        picking_id = self.env['stock.picking'].search([
            ('request_out_id', '=', order.id),
            ('state', '=', 'done')
        ], limit=1, order='id desc')
        packing_ids = []

        if picking_id:
            packing_ids += [picking_id.pack_operation_ids]
            packing_ids += [picking_id.pack_operation_product_remove_ids]
            for packing_id in packing_ids:

                for line in packing_id:

                    if line.qty_left:

                        origin_name = self.get_origin_name_picking(order)
                        procurement_group_id = self.check_exiting_procument_group(order)
                        model_line_name = order.requisition_branches_line_ids._name
                        move_dict = order.env[model_line_name]._run_move_create(
                            order,
                            procurement_group_id,
                            origin_name,
                            company_obj.id,
                            source_location_id,
                            transit_location_id,
                            picking_type_out_id,
                            company_obj.warehouse_id.id,
                            abs(line.qty_left),
                            line.product_id,
                        )
                        move = move_obj.create(move_dict)
                        move_ids += [move.id]

                        picks = order.search_picking_existing(move, 'request_out_id')
                        if picks:
                            pick = picks[0]
                        else:
                            values = self._prepare_picking_assign(move, order.id, 'request_out_id')
                            pick = pick_obj.create(values)

                        move.write({'picking_id': pick.id})
                        picking_id = pick
                        picking_id.write({
                            'min_date': order.date_schedule
                        })

            if move_ids:
                self.action_move_confirm(move_ids)

                picking_id.force_assign()

                return True

    @api.multi
    def create_picking_in(self, pack_oparetion_ids):

        # picking in of branch #############################################################################################################################
        for order in self:

            move_obj = order.env['stock.move']
            pick_obj = order.env["stock.picking"]

            company_obj = order.env.user.company_id
            transit_location_id = company_obj.location_transit_id.id
            warehouse_branch_obj = order.pos_branch.warehouse_id
            move_ids = []
            picking_type_in_id = warehouse_branch_obj.int_type_id.id
            if not warehouse_branch_obj.wh_shelf_stock_loc_id.id:
                raise UserError(_(
                    u"Not have shelf location in branch ware house,\n Please config shelf location in warehouse managment"))
            dest_location_id = warehouse_branch_obj.wh_shelf_stock_loc_id.id
            picking_id = None
            for pack_line in pack_oparetion_ids:

                origin_name = self.get_origin_name_picking(order)

                procurement_group_id = self.check_exiting_procument_group(order)
                model_line_name = order.requisition_branches_line_ids._name
                move_dict = order.env[model_line_name]._run_move_create(
                    order,
                    procurement_group_id,
                    origin_name,
                    company_obj.id,
                    transit_location_id,
                    dest_location_id,
                    picking_type_in_id,
                    warehouse_branch_obj.id,
                    pack_line.qty_done,
                    pack_line.product_id,
                )
                move = move_obj.create(move_dict)
                # move.action_confirm()
                move_ids += [move.id]

                if picking_id:
                    pick = picking_id
                else:
                    values = self._prepare_picking_assign(move, order.id, 'request_in_id', pack_line.picking_id)
                    pick = pick_obj.create(values)

                move.write({'picking_id': pick.id})
                order.write({'picking_in_id': pick.id})
                picking_id = pick_obj.browse(pick.id)

            self.action_move_confirm(move_ids)

            picking_id.force_assign()


class RequisitionBranchesLine(models.Model):
    _name = 'requisition.branches.line'

    @api.multi
    @api.depends('qty', 'qty_allow')
    def compute_qty_diff(self):
        for record in self:
            record.qty_diff = record.qty_allow - record.qty

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        domain=[('sale_ok', '=', True)],
    )
    name = fields.Char('Description')
    product_uom = fields.Many2one(
        'product.uom',
        string='Unit of Measure',
        readonly=True,
    )
    qty = fields.Float(
        string='Quantity',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=0.0,
    )
    qty_allow = fields.Float(
        string='Quantity Allow',
        required=True,
        readonly=True,
        states={'confirmed': [('readonly', False)]},
        default=0.0,
    )
    qty_diff = fields.Float(
        compute='compute_qty_diff',
        string='Quantity Different',
        readonly=True,
    )
    request_id = fields.Many2one(
        'requisition.branches',
        string='Request',
    )
    state = fields.Selection(
        "requisition.branches",
        related='request_id.state',
        string="State",
        readonly=True,
        default='draft',
    )

    _sql_constraints = [
        ('qty', 'CHECK(qty >= 0.0)', 'Quantity must be greater than or equal to 0.0!')]

    @api.onchange('product_id')
    def product_id_change(self):

        if self.product_id:

            if not self.product_uom or (self.product_id.uom_id.category_id.id != self.product_uom.category_id.id):
                self.product_uom = self.product_id.uom_id.id

            name = self.product_id.name_get()[0][1]
            if self.product_id.description_sale:
                name += '\n' + self.product_id.description_sale
            self.name = name

    @api.model
    def create(self, vals):

        if 'product_id' in vals and vals.get('product_id'):
            product_id = self.product_id.browse(vals.get('product_id'))
            vals.update({
                'product_uom': product_id.uom_id.id,
            })

        result = super(RequisitionBranchesLine, self).create(vals)
        return result

    @api.multi
    def write(self, values):
        if not values:
            values = {}

        if 'product_id' in values and values.get('product_id'):
            product_id = self.product_id.browse(values.get('product_id'))
            values.update({
                'product_uom': product_id.uom_id.id,
            })

        return super(RequisitionBranchesLine, self).write(values)

    @api.multi
    def _run_move_create(self, request_id, group_id, origin_name, company_id, location_id, location_dest_id,
                         picking_type_id, warehouse_id, qty, product_id):
        newdate = (datetime.strptime(request_id.date, '%Y-%m-%d')).strftime('%Y-%m-%d')
        vals = {
            'name': request_id.name,
            'company_id': company_id,
            'product_id': product_id.id,
            'product_uom': product_id.uom_id.id,
            'product_uom_qty': qty,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'picking_type_id': picking_type_id,
            'warehouse_id': warehouse_id,
            'group_id': group_id,
            'origin': origin_name,
            'date': newdate,
            'date_expected': newdate,
        }
        return vals


class RequisitionBranchesSale(models.Model):
    _inherit = 'requisition.branches'
    _name = 'requisition.branches.sale'

    @api.depends('requisition_branches_stock_line_ids', 'check_branches_stock_line')
    def _check_branches_stock_line_ids(self):

        for line in self:

            if line.requisition_branches_stock_line_ids:
                line.update({
                    'check_branches_stock_line': True,
                })

    @api.depends('requisition_branches_receive_line_ids', 'check_branches_receive_line')
    def _check_branches_receive_line_ids(self):

        for line in self:

            if line.requisition_branches_receive_line_ids:
                line.update({
                    'check_branches_receive_line': True,
                })

    @api.depends('requisition_branches_reverse_line_ids', 'check_branches_reverse_line')
    def _check_branches_reverse_line_ids(self):

        for line in self:

            if line.requisition_branches_reverse_line_ids:
                line.update({
                    'check_branches_reverse_line': True,
                })

    @api.depends('requisition_branches_line_ids.price_total',
                 'requisition_branches_stock_line_ids.price_total',
                 'requisition_branches_reverse_line_ids.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO PPT.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.requisition_branches_line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

            stock_amount_untaxed = stock_amount_tax = 0.0
            for line in order.requisition_branches_stock_line_ids:
                stock_amount_untaxed += line.price_subtotal
                stock_amount_tax += line.price_tax
            order.update({
                'stock_amount_untaxed': order.pricelist_id.currency_id.round(stock_amount_untaxed),
                'stock_amount_tax': order.pricelist_id.currency_id.round(stock_amount_tax),
                'stock_amount_total': stock_amount_untaxed + stock_amount_tax,
            })

            reverse_amount_untaxed = reverse_amount_tax = 0.0
            for line in order.requisition_branches_reverse_line_ids:
                reverse_amount_untaxed += line.price_subtotal
                reverse_amount_tax += line.price_tax
            order.update({
                'reverse_amount_untaxed': order.pricelist_id.currency_id.round(reverse_amount_untaxed),
                'reverse_amount_tax': order.pricelist_id.currency_id.round(reverse_amount_tax),
                'reverse_amount_total': reverse_amount_untaxed + reverse_amount_tax,
            })

            receive_amount_untaxed = receive_amount_tax = 0.0
            for line in order.requisition_branches_receive_line_ids:
                receive_amount_untaxed += line.price_subtotal
                receive_amount_tax += line.price_tax
            order.update({
                'receive_amount_untaxed': order.pricelist_id.currency_id.round(receive_amount_untaxed),
                'receive_amount_tax': order.pricelist_id.currency_id.round(receive_amount_tax),
                'receive_amount_total': receive_amount_untaxed + receive_amount_tax,
            })

    @api.multi
    def action_create_template(self):
        for order in self:
            product_template = order.product_template_id
            for item in product_template.product_ids:
                self.prepare_requisition_line(item.product_id, order)
            order.write({'product_template_created': True})

            for requisition_branches_line_id in order.requisition_branches_line_ids:
                requisition_branches_line_id.product_id_change()

        return True

    @api.multi
    def create_requisition_line(self, values):
        self.env['requisition.branches.sale.line'].create(values)

    @api.multi
    def write(self, values):

        for requisition_branches_line_id in self.requisition_branches_line_ids:
            requisition_branches_line_id.product_id_change()

        return super(RequisitionBranchesSale, self).write(values)

    picking_out_ids = fields.One2many(
        'stock.picking',
        'request_sale_out_id',
        'Pickings Out of RBS',
        readonly=True,
    )
    picking_in_ids = fields.One2many(
        'stock.picking',
        'request_sale_in_id',
        'Pickings In of RBS',
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        readonly=True,
        states={
            'draft': [('readonly', False)]
        },
        required=True,
        change_default=True,
        index=True,
        track_visibility='always'
    )
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )
    amount_tax = fields.Monetary(
        string='Taxes',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )
    amount_total = fields.Monetary(
        string='Total',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )

    stock_amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )
    stock_amount_tax = fields.Monetary(
        string='Taxes',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )
    stock_amount_total = fields.Monetary(
        string='Total',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )

    reverse_amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )
    reverse_amount_tax = fields.Monetary(
        string='Taxes',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )
    reverse_amount_total = fields.Monetary(
        string='Total',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )

    receive_amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )
    receive_amount_tax = fields.Monetary(
        string='Taxes',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )
    receive_amount_total = fields.Monetary(
        string='Total',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='always'
    )

    requisition_branches_line_ids = fields.One2many(
        'requisition.branches.sale.line',
        'request_id',
        string='Requisition Branches Sale Line',
        states={'canceled': [('readonly', True)], 'done': [('readonly', True)]},
    )
    requisition_branches_stock_line_ids = fields.One2many(
        'requisition.branches.line.stock',
        'request_id',
        string='Requisition Branches Sale Line Stock',
        states={'canceled': [('readonly', True)], 'done': [('readonly', True)]},
    )
    requisition_branches_receive_line_ids = fields.One2many(
        'requisition.branches.line.receive',
        'request_id',
        string='Requisition Branches Sale Line Receive',
        states={'canceled': [('readonly', True)], 'done': [('readonly', True)]},
    )
    requisition_branches_reverse_line_ids = fields.One2many(
        'requisition.branches.line.reverse',
        'request_id',
        string='Requisition Branches Sale Line Reverse',
        states={'canceled': [('readonly', True)], 'done': [('readonly', True)]},
    )

    check_branches_stock_line = fields.Boolean(
        string='Production Order Stock Line',
        compute='_check_branches_stock_line_ids',
    )
    check_branches_receive_line = fields.Boolean(
        string='Production Order Receive Line',
        compute='_check_branches_receive_line_ids',
    )
    check_branches_reverse_line = fields.Boolean(
        string='Production Order Reverse Line',
        compute='_check_branches_reverse_line_ids',
    )

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        required=True,
        readonly=True,
        states={
            'draft': [('readonly', False)],
            'sent': [('readonly', False)]
        },
        help="Pricelist for current sales order."
    )
    currency_id = fields.Many2one(
        "res.currency",
        related='pricelist_id.currency_id',
        string="Currency",
        readonly=True,
        required=True
    )

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment term
        - Invoice address
        - Delivery address
        """

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
        }
        if self.env.user.company_id.sale_note:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note

        if self.partner_id.user_id:
            values['user_id'] = self.partner_id.user_id.id
        self.update(values)

    @api.multi
    def _prepare_branches_stock_line(self, pack_line):
        """ Prepares a new picking for this move as it could not be assigned to
        another picking. This method is designed to be inherited.
        """
        requisition_branches_line_id = self.env['requisition.branches.line'].search([
            ('request_id', '=', self.id),
            ('product_id', '=', pack_line.product_id.id)
        ])

        values = {
            'name': requisition_branches_line_id.name,
            'product_id': pack_line.product_id.id,
            'qty': pack_line.qty_done,
            'price_unit': requisition_branches_line_id.price_unit,
            'product_uom': requisition_branches_line_id.product_uom.id,
            'tax_id': [(6, 0, [tax_id.id for tax_id in requisition_branches_line_id.tax_id])],
            'qty_allow': requisition_branches_line_id.qty_allow,
            'request_id': self.id,
        }
        return values

    @api.multi
    def _prepare_branches_receive_reverse_line(self, pack_line):
        """ Prepares a new picking for this move as it could not be assigned to
        another picking. This method is designed to be inherited.
        """
        requisition_branches_line_id = self.env['requisition.branches.line'].search([
            ('request_id', '=', self.id),
            ('product_id', '=', pack_line.product_id.id)
        ])

        values = {
            'name': requisition_branches_line_id.name,
            'product_id': pack_line.product_id.id,
            'qty': pack_line.qty_done,
            'price_unit': requisition_branches_line_id.price_unit,
            'product_uom': requisition_branches_line_id.product_uom.id,
            'tax_id': [(6, 0, [tax_id.id for tax_id in requisition_branches_line_id.tax_id])],
            'qty_allow': requisition_branches_line_id.qty_allow,
            'request_id': self.id,
        }
        return values

    @api.multi
    def create_receive_stock(self, pack_oparetion_ids):

        # receive qty show in RBS
        for order in self:

            for pack_line in pack_oparetion_ids:
                branches_receive_line = order._prepare_branches_receive_reverse_line(pack_line)

                self.env['requisition.branches.line.receive'].create(branches_receive_line)

    @api.multi
    def create_reverse_stock(self, pack_oparetion_ids):

        # picking in of branch #############################################################################################################################
        for order in self:

            for pack_line in pack_oparetion_ids:
                branches_reverse_line = order._prepare_branches_receive_reverse_line(pack_line)

                self.env['requisition.branches.line.reverse'].create(branches_reverse_line)

    @api.multi
    def create_picking_in(self, pack_oparetion_ids):

        # picking in of branch #############################################################################################################################
        for order in self:

            for pack_line in pack_oparetion_ids:
                branches_stock_line = order._prepare_branches_stock_line(pack_line)

                self.env['requisition.branches.line.stock'].create(branches_stock_line)

        return super(RequisitionBranchesSale, self).create_picking_in(pack_oparetion_ids)


class RequisitionBranchesSaleLine(models.Model):
    _inherit = 'requisition.branches.line'
    _name = 'requisition.branches.sale.line'

    @api.depends('qty_allow', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.request_id.currency_id, line.qty_allow, product=line.product_id,
                                            partner=line.request_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.depends('price_subtotal', 'qty_allow', 'qty')
    def _get_price_reduce(self):
        for line in self:
            line.price_reduce = line.price_subtotal / line.qty_allow if line.qty_allow else 0.0

    @api.multi
    def _compute_tax_id(self):
        for line in self:
            fpos = line.request_id.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(lambda r: not line.company_id or r.company_id == line.company_id)
            line.tax_id = fpos.map_tax(taxes) if fpos else taxes

    @api.onchange('product_uom', 'qty', 'qty_allow')
    def product_uom_change(self):
        if not self.product_uom:
            self.price_unit = 0.0
            return
        if self.request_id.pricelist_id and self.request_id.partner_id:
            product = self.product_id.with_context(
                lang=self.request_id.partner_id.lang,
                partner=self.request_id.partner_id.id,
                quantity=self.qty,
                date_order=self.request_id.date,
                pricelist=self.request_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_unit = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id,
                                                                              self.tax_id)

    request_id = fields.Many2one(
        'requisition.branches.sale',
        string='Request',
    )

    company_id = fields.Many2one(
        related='request_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )

    order_partner_id = fields.Many2one(
        related='request_id.partner_id',
        store=True,
        string='Customer'
    )

    price_unit = fields.Float(
        'Unit Price',
        required=True,
        digits=dp.get_precision('Product Price'),
        default=0.0
    )

    price_subtotal = fields.Monetary(
        compute='_compute_amount',
        string='Subtotal',
        readonly=True,
        store=True
    )
    price_tax = fields.Monetary(
        compute='_compute_amount',
        string='Taxes',
        readonly=True,
        store=True
    )
    price_total = fields.Monetary(
        compute='_compute_amount',
        string='Total',
        readonly=True,
        store=True
    )
    discount = fields.Float(
        string='Discount (%)',
        digits=dp.get_precision('Discount'),
        default=0.0
    )

    currency_id = fields.Many2one(
        related='request_id.currency_id',
        store=True,
        string='Currency',
        readonly=True
    )

    tax_id = fields.Many2many(
        'account.tax',
        string='Taxes',
        domain=[
            '|',
            ('active', '=', False),
            ('active', '=', True)
        ]
    )

    @api.multi
    @api.onchange('product_id', 'price_unit', 'product_uom', 'qty_allow', 'qty')
    def product_id_change(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not self.product_uom or (self.product_id.uom_id.category_id.id != self.product_uom.category_id.id):
            vals['product_uom'] = self.product_id.uom_id

        product = self.product_id.with_context(
            lang=self.request_id.partner_id.lang,
            partner=self.request_id.partner_id.id,
            quantity=self.qty_allow,
            date=self.request_id.date,
            pricelist=self.request_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        name = product.name_get()[0][1]
        if product.description_sale:
            name += '\n' + product.description_sale
        vals['name'] = name

        self._compute_tax_id()

        if self.request_id.pricelist_id and self.request_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id,
                                                                                 self.tax_id)
        self.update(vals)
        return {'domain': domain}


class RequisitionBranchesSaleLineStock(models.Model):
    _name = 'requisition.branches.line.stock'
    _inherit = 'requisition.branches.sale.line'


class RequisitionBranchesSaleLineReceive(models.Model):
    _name = 'requisition.branches.line.receive'
    _inherit = 'requisition.branches.sale.line'


class RequisitionBranchesSaleLineReverse(models.Model):
    _name = 'requisition.branches.line.reverse'
    _inherit = 'requisition.branches.sale.line'


class RequisitionBranchesRound(models.Model):
    _name = 'requisition.branches.round'
    _description = "Requisition of Branch Round"

    name = fields.Char(
        'Number',
        required=True,
        copy=False,
    )
