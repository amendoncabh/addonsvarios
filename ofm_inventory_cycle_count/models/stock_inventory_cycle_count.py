# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_utils
import datetime


class Inventory(models.Model):
    _name = "stock.inventory.cycle.count"
    _inherit = ['mail.thread']
    _description = "Inventory"
    _order = 'id desc'

    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))

    name = fields.Char(
        'Inventory Reference',
        readonly=True, 
        required=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange'
    )
    date = fields.Date(
        'Start Date',
        required=True,
        readonly=True,
        default=fields.Datetime.now,
        track_visibility='onchange'
    )
    inventory_date = fields.Date(
        'Document Date',
        required=True,
        readonly=True,
        default=fields.Datetime.now,
        track_visibility='onchange'
    )
    finish_date = fields.Date(
        'Finish Date',
        required=True,
        readonly=True,
        default=fields.Datetime.now,
        track_visibility='onchange'
    )
    line_ids = fields.One2many(
        'stock.inventory.cycle.count.line', 'inventory_id', string='Inventories',
        copy=True, 
        readonly=False,
        states={'done': [('readonly', True)]},
        track_visibility='onchange'
    )
    state = fields.Selection(string='Status', 
        selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('progress', 'In Progress'),
            ('confirm', 'To Approve'),
            ('done', 'Validated')
        ],
        copy=False, 
        index=True, 
        readonly=True,
        default='draft',
        track_visibility='onchange'
    )
    company_id = fields.Many2one(
        'res.company', 'Company',
        index=True, 
        required=True,
        default=lambda self: self.env['res.company']._company_default_get('stock.inventory.cycle.count'),
        track_visibility='onchange'
    )   
    location_id = fields.Many2one(
        'stock.location', 'Inventoried Location',
        readonly=True, 
        required=True,
        states={'draft': [('readonly', False)]},
        default=_default_location_id,
        track_visibility='onchange'
    )
    product_id = fields.Many2one(
        'product.product', 'Inventoried Product',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Product to focus your inventory on a particular Product."
    )
    package_id = fields.Many2one(
        'stock.quant.package', 'Inventoried Pack',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Pack to focus your inventory on a particular Pack."
    )
    partner_id = fields.Many2one(
        'res.partner', 'Inventoried Owner',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Owner to focus your inventory on a particular Owner."
    )
    lot_id = fields.Many2one(
        'stock.production.lot', 'Inventoried Lot/Serial Number',
        copy=False, 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Lot/Serial Number to focus your inventory on a particular Lot/Serial Number."
    )
    type = fields.Selection(
        [
            ('full', 'Full Stock Take'),
            ('cyclic', 'Cyclic Count')
        ],
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    filter = fields.Selection(
        string='Inventory of', 
        selection='_selection_filter',
        default='none',
        help="If you do an entire inventory, you can choose 'All Products' and it will prefill the inventory with the current stock.  If you only do some products  "
             "(e.g. Cycle Counting) you can choose 'Manual Selection of Products' and the system won't propose anything.  You can also let the "
             "system propose for a single product / lot /... ")
    total_qty = fields.Float('Total Quantity', 
        compute='_compute_total_qty')
    category_id = fields.Many2many(
        comodel_name='product.category', 
        string='Inventoried Category',
        readonly=True, states={'draft': [('readonly', False)]},
        help="Specify Product Category to focus your inventory on a particular Category.")
    exhausted = fields.Boolean('Include Exhausted Products', 
        readonly=True, 
        states={'draft': [('readonly', False)]}, 
        default=False)
    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        required=True,
        readonly=True,
        index=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user.branch_id,
        track_visibility='onchange'
    )
    branch_name = fields.Char(
        'Branch Name', 
        related='branch_id.name', 
        store=True, 
        readonly=True)
    value = fields.Float('Total Value', 
        readonly=True)
    fee = fields.Float('Total Fee', 
        readonly=True)
    product_dept = fields.Many2many(
        comodel_name='ofm.product.dept',
        string='Dept OFM',
        translate=True,
        domain="[('dept_parent_id', '=', False)]")
    product_sub_dept = fields.Many2many(
        comodel_name='ofm.product.dept',
        string='Sub Dept OFM',
        translate=True,
        domain="[('dept_parent_id', '!=', False)]")
    number = fields.Char(
        string="No.",
        required=False,
        default='Draft',
        readonly=True,
    )
    approved = fields.Boolean(
        'Approved',
        default=False
    )
    adjust_id = fields.Many2one(
        'stock.inventory',
        'Adjustment',
        readonly=True
    )
    adjust_name = fields.Char(
        'Adjustment Number',
        readonly=True,
        related='adjust_id.number',
        default='Draft',
    )
    template = fields.Many2one(
        'template.of.product',
        string='Template',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    is_template = fields.Boolean(
        default=False
    )
    is_manager_edit  = fields.Boolean(
        default=False
    )
    is_owner = fields.Boolean(
        compute='_compute_is_owner',
        default=False
    )
    is_staff = fields.Boolean(
        compute='_compute_is_staff',
        default=False
    )
    is_manager = fields.Boolean(
        compute='_compute_is_manager',
        default=False
    )
    is_hide_to_approve = fields.Boolean(
        compute='_compute_is_hide_to_approve',
        default=False
    )
    is_hide_validate = fields.Boolean(
        compute='_compute_is_hide_validate',
        default=False
    )
    approved_user = fields.Selection(
        string='User approve',
        selection=[
            ('owner', 'Owner'),
            ('manager', 'Manager'),
            ('staff', 'Staff')
        ],
        readonly=True
    )
    total_real_qty = fields.Integer(
        string='Total Real Quantity',
        compute='_compute_total_real_qty'
    )
    total_system_qty = fields.Integer(
        string='Total System Quantity',
        compute='_compute_total_system_qty'
    )

    @api.depends('line_ids','line_ids.product_qty')
    def _compute_total_real_qty(self):
        self.total_real_qty = 0
        for line in self.line_ids:
            self.total_real_qty += line.product_qty

    @api.depends('line_ids','line_ids.theoretical_qty')
    def _compute_total_system_qty(self):
        self.total_system_qty = 0
        for line in self.line_ids:
            self.total_system_qty += line.theoretical_qty

    @api.depends('line_ids')
    def _compute_is_hide_to_approve(self):
        self.is_hide_to_approve = (self.env.user.has_group('ofm_inventory_cycle_count.group_stock_owner') and self.is_manager_edit == True) \
            or self.is_manager_edit == False

    @api.depends('line_ids')
    def _compute_is_owner(self):
        self.is_owner = self.env.user.has_group('ofm_inventory_cycle_count.group_stock_owner')

    @api.depends('line_ids')
    def _compute_is_hide_validate(self):
        if self.is_owner == True:
            self.is_hide_validate = False
        elif self.is_owner == True and self.state == 'confirm' \
            and self.approved_user == 'owner':
            self.is_hide_validate = False
        elif (self.state == 'confirm' \
            and self.approved_user == 'owner' \
            and (self.is_manager == True or self.is_staff == True) or self.state != 'confirm'):
            self.is_hide_validate = True

    @api.depends('line_ids')
    def _compute_is_staff(self):
        self.is_staff = self.env.user.has_group('ofm_inventory_cycle_count.group_stock_staff')
    
    @api.depends('line_ids')
    def _compute_is_manager(self):
        self.is_manager = self.env.user.has_group('stock.group_stock_manager')

    @api.multi
    def write(self, values):
        if self.env.user.has_group('stock.group_stock_manager') and \
            not self.env.user.has_group('ofm_inventory_cycle_count.group_stock_owner') and \
            'line_ids' in values:
            values.update({
                'is_manager_edit': True
            })
        masege_obj = self.env['mail.message']
        body=''
        if 'line_ids' in values:
            for val in values['line_ids']:
                if val[0] != 5:
                    line = self.env['stock.inventory.cycle.count.line'].browse(val[1])
                    if not val[1] and val[2]:
                        if 'product_id' in val[2]:
                            product = self.env['product.product'].browse(val[2]['product_id'])
                            if 'inventory_id' in val[2]:
                                continue
                            else:
                                if 'product_qty' in val[2]:
                                    if val[2]['product_qty']:
                                        body += '&bull; ' + 'Add product: ' + product.product_tmpl_id.name + ' with quntity: ' + str(val[2]['product_qty']) + '<p/>'
                                    else:
                                        body += '&bull; ' + 'Add product: ' + product.product_tmpl_id.name + '<p/>'
                                else:
                                    body += '&bull; ' + 'Add product: ' + product.product_tmpl_id.name + '<p/>'
                    elif val[0] == 0:
                        body += '&bull; ' + 'Delete product: ' + line.product_name + '<p/>'
                    elif val[0] == 2 and val[1]:
                        body += '&bull; ' + 'Delete product: ' + line.product_name + '<p/>'
                    elif val[2]:
                        if 'product_id' in val[2]:
                            product = self.env['product.product'].browse(val[2]['product_id'])
                            condition=''
                            if 'product_qty' in val[2]:
                                condition = ' with quantity: ' + str(val[2]['product_qty'])
                            body += '&bull; ' + 'Change product: ' + line.product_name + ' &rArr; ' + product.product_tmpl_id.name + condition + '<p/>'
                        elif 'product_qty' in val[2]:
                            body += '&bull; ' + 'Edit quantity of ' + line.product_name + ':  ' + str(line.product_qty) + ' &rArr; ' + str(val[2]['product_qty']) + '<p/>'
        if body != '':
            body = "<div style='background-color: rgb(228 ,228 ,228);'>{}</div>".format(body)
            message_qty_before = len(masege_obj.search
                                    ([('model', '=', 'stock.inventory.cycle.count'),('res_id', '=', self.id)]))
            res = super(Inventory, self).write(values)
            message_qty_after = len(masege_obj.search
                                    ([('model', '=', 'stock.inventory.cycle.count'), ('res_id', '=', self.id)]))
            if message_qty_before != message_qty_after:
                masege_id = masege_obj.search([
                ('model', '=', 'stock.inventory.cycle.count'),
                ('res_id', '=', self.id), ], limit=1)
                masege_id.write({'body': body})
            else:
                messg_vals = {
                        'model': 'stock.inventory.cycle.count',
                        'res_id': self.id,
                        'parent_id': False,
                        'body': body,
                        'date': datetime.datetime.now()
                    }
                masege_obj.create(messg_vals)
        else:
            res = super(Inventory, self).write(values)
        
        return res

    @api.onchange('product_dept')
    def set_dept_ofm(self):
        self.product_sub_dept = False

        query_parent_dept_ofm = ''

        if all([
            self.product_dept,
            not self.product_sub_dept,
        ]):
            query_parent_dept_ofm = """
                and dept_parent_id = %s
            """ % self.product_dept.ids

        query_string = """
            select min(id) as id
            from ofm_product_dept
            where dept_parent_id is not null
            %s
            group by name
        """ % query_parent_dept_ofm

        self.env.cr.execute(query_string)
        result_model = self.env.cr.dictfetchall()

        sub_dept_ids = []

        for result in result_model:
            sub_dept_ids.append(result['id'])

        dept_ofm_domain = [
            ('dept_parent_id', '!=', False),
            ('id', 'in', sub_dept_ids)
        ]

        return {
            'domain': {
                'product_sub_dept': dept_ofm_domain
            },
        }

    @api.onchange('template')
    def onchange_filter(self):
        if self.filter == 'dept':
            self.product_sub_dept = False
            self.product_id = False
            self.category_id = False

        elif self.filter == 'sub_dept':
            self.product_dept = False
            self.product_id = False
            self.category_id = False

        elif self.filter == 'category':
            self.product_dept = False
            self.product_sub_dept = False
            self.product_id = False

        elif self.filter == 'product':
            self.product_dept = False
            self.product_sub_dept = False
            self.category_id = False

        else:
            self.product_dept = False
            self.product_sub_dept = False
            self.category_id = False
            self.product_id = False

    @api.one
    @api.depends('product_id', 'line_ids.product_qty')
    def _compute_total_qty(self):
        """ For single product inventory, total quantity of the counted """
        if self.product_id:
            self.total_qty = sum(self.mapped('line_ids').mapped('product_qty'))
        else:
            self.total_qty = 0
        for line in self.line_ids:
            line.diff = line.product_qty - line.theoretical_qty

    @api.onchange('template','type')
    def onchange_template(self):
        self.filter = ''
        if self.template:
            self.is_template = False
        else:
            self.is_template = True
    
    @api.onchange('line_ids.product_qty')
    def cal(self):
        fee = 0.0
        value = 0.0
        for line in self.line_ids:
            line.diff =  line.product_qty - line.theoretical_qty
            fee += line.fee
            value += line.value
        self.fee = fee
        self.value = value

    def import_cal_fee(self):
        fee = 0.0
        value = 0.0
        for line in self:
            fee += line.fee
            value += line.value
        self.fee = fee
        self.value = value

    @api.multi
    def unlink(self):
        for inventory in self:
            if inventory.state == 'done':
                raise UserError(_('You cannot delete a validated inventory adjustement.'))
        return super(Inventory, self).unlink()

    @api.model
    def _selection_filter(self):
        """ Get the list of filter allowed according to the options checked
        in 'Settings\Warehouse'. """
        res_filter = [
            ('dept', _('Product Dept')),
            ('sub_dept', _('Product Sub Dept')),
            ('category', _('One product category')),
            ('product', _('One product only')),
            ('partial', _('Select products manually'))
            ]

        if self.user_has_groups('stock.group_tracking_owner'):
            res_filter += [('owner', _('One owner only')), ('product_owner', _('One product for a specific owner'))]
        if self.user_has_groups('stock.group_production_lot'):
            res_filter.append(('lot', _('One Lot/Serial Number')))
        if self.user_has_groups('stock.group_tracking_lot'):
            res_filter.append(('pack', _('A Pack')))
        return res_filter

    @api.onchange('filter')
    def onchange_filter(self):
        if self.filter not in ('product', 'product_owner'):
            self.product_id = False
        if self.filter != 'lot':
            self.lot_id = False
        if self.filter not in ('owner', 'product_owner'):
            self.partner_id = False
        if self.filter != 'pack':
            self.package_id = False
        if self.filter != 'category':
            self.category_id = False
        if self.filter == 'product':
            self.exhausted = True

    @api.onchange('location_id')
    def onchange_location_id(self):
        if self.location_id.company_id:
            self.company_id = self.location_id.company_id

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.branch_id = None

    @api.onchange('branch_id')
    def _onchange_company_id(self):
        self.location_id = None

    @api.multi
    def action_to_approve(self):
        is_zero = False
        if self.env.user.has_group('ofm_inventory_cycle_count.group_stock_owner'):
            self.approved_user = 'owner'
        elif self.env.user.has_group('stock.group_stock_manager'):
            self.approved_user = 'manager'
        elif self.env.user.has_group('ofm_inventory_cycle_count.group_stock_staff'):
            self.approved_user = 'staff'

        for item in self.line_ids:
            if item.product_qty == 0:
                is_zero = True
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form', 
                    'view_mode': 'form',
                    'res_model': 'zero.quantity.warning', 
                    'target': 'new', 
                }
        if is_zero == False:
            self.approved = True
            self.state = 'confirm'

    @api.multi
    def action_to_denied(self):
        self.approved = False
        self.state = 'progress'

    @api.one
    @api.constrains('filter', 'product_id', 'lot_id', 'partner_id', 'package_id')
    def _check_filter_product(self):
        if self.filter == 'none' and self.product_id and self.location_id and self.lot_id:
            return
        if self.filter not in ('product', 'product_owner') and self.product_id:
            raise UserError(_('The selected inventory options are not coherent.'))
        if self.filter != 'lot' and self.lot_id:
            raise UserError(_('The selected inventory options are not coherent.'))
        if self.filter not in ('owner', 'product_owner') and self.partner_id:
            raise UserError(_('The selected inventory options are not coherent.'))
        if self.filter != 'pack' and self.package_id:
            raise UserError(_('The selected inventory options are not coherent.'))

    def get_cc_no(self):
        if not all([
            self.branch_id,
            self.branch_id.warehouse_id,
        ]):
            return 'Draft'

        ctx = dict(self._context)
        ctx.update({'res_model': 'stock.inventory.cycle.count'})
        prefix = 'CC-' + self.branch_id.branch_code + '%(y)s%(month)s'
        cc_no = self.branch_id.with_context(ctx).next_sequence(self.date, prefix, 5) or '/'
        return cc_no

    def get_aj_no(self):
        if not all([
            self.branch_id,
            self.branch_id.warehouse_id,
        ]):
            return 'Draft'

        ctx = dict(self._context)
        ctx.update({'res_model': 'stock.inventory'})

        prefix = 'AJ-' + self.branch_id.branch_code + '%(y)s%(month)s'
        aj_no = self.branch_id.with_context(ctx).next_sequence(self.date, prefix, 5) or '/'
        return aj_no

    @api.multi
    def action_done(self):
        ctx = dict(self.env.context)
        ctx.update({
            'branch_id': self.branch_id.id,
        })
        negative = next((line for line in self.mapped('line_ids') if line.product_qty < 0 and line.product_qty != line.theoretical_qty), False)
        if negative:
            raise UserError(_('You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s') % (negative.product_id.name, negative.product_qty))
        self.write({'state': 'done'})
             

        def create_adjustment(self):
            adj = self.env['stock.inventory']
            adj_id = adj.create({
                # add data here
                'name': self.name,
                'date': self.date,
                'company_id': self.company_id.id,
                'branch_id': self.branch_id.id,
                'location_id': self.location_id.id,
                'exhausted': self.exhausted,
                'number': self.get_aj_no(),
                'state': 'confirm',
                'filter': 'partial' if self.filter == 'random' or self.filter == 'dept' or self.filter == 'sub_dept' else self.filter,
                'inventory_of': self.filter if self.filter else False,
                'template_id': self.template.id if self.template else False,
                'type': self.type if self.type else False,
                'category_id': self.category_id.id if self.category_id else False,
                'product_id': self.product_id.id if self.product_id else False,
                'date': self.inventory_date,
                'date_now': self.date,
                'finish_date': self.finish_date

            })
            line_ids = []
            for item in self.line_ids:
                if item.diff != 0:
                    adj_line = self.env['stock.inventory.line']
                    line_ids.append(adj_line.create({
                        'inventory_id': adj_id.id,
                        'partner_id': item.partner_id.id,
                        'product_id': item.product_id.id,
                        'product_name': item.product_name,
                        'product_code': item.product_code,
                        'product_uom_id': item.product_uom_id.id,
                        'product_qty': item.product_qty,
                        'location_id': item.location_id.id,
                        'package_id': item.package_id.id,
                        'prod_lot_id': item.prod_lot_id.id,
                        'prodlot_name': item.prodlot_name,
                        'company_id': item.company_id.id,
                        'state': item.state,
                        'theoretical_qty': item.theoretical_qty,
                        'inventory_location_id': item.inventory_location_id.id,
                        'branch_id': item.branch_id.id
                    }))
            
            return adj_id
        self.finish_date = fields.Datetime.now()
        self.adjust_id = create_adjustment(self)
        if self.product_sub_dept:
            self.adjust_id.product_sub_dept = self.product_sub_dept
        if self.product_dept:
            self.adjust_id.product_dept = self.product_dept
        return True

    @api.multi
    def action_cancel_draft(self):
        self.write({
            'line_ids': [(5,)],
            'state': 'draft'
        })

    @api.multi
    def action_start(self):
        for inventory in self:
            vals = {'state': 'progress', 'inventory_date': fields.Datetime.now()}
            if (inventory.filter != 'partial') and not inventory.line_ids: 
                vals.update({
                    'line_ids': [(0, 0, line_values) for line_values in inventory._get_inventory_lines_values()],
                })
            vals.update({
                'number': inventory.get_cc_no(),
            })
            inventory.write(vals)
        return True
    prepare_inventory = action_start

    @api.multi
    def action_inventory_cycle_count_line_tree(self):
        action = self.env.ref('ofm_inventory_cycle_count.action_inventory_cycle_count_line_tree').read()[0]
        action['context'] = {
            'default_location_id': self.location_id.id,
            'default_product_id': self.product_id.id,
            'default_prod_lot_id': self.lot_id.id,
            'default_package_id': self.package_id.id,
            'default_partner_id': self.partner_id.id,
            'default_inventory_id': self.id,
        }
        return action

    @api.multi
    def _get_inventory_lines_values(self):
        # TDE CLEANME: is sql really necessary ? I don't think so
        locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
        domain = ' location_id in %s AND active = TRUE'
        args = (tuple(locations.ids),)

        vals = []
        Product = self.env['product.product']
        # Empty recordset of products available in stock_quants
        quant_products = self.env['product.product']
        # Empty recordset of products to filter
        products_to_filter = self.env['product.product']

        # case 0: Filter on company
        if self.company_id:
            domain += ' AND company_id = %s'
            args += (self.company_id.id,)
        
        #case 1: Filter on One owner only or One product for a specific owner
        if self.partner_id:
            domain += ' AND owner_id = %s'
            args += (self.partner_id.id,)
        #case 2: Filter on One Lot/Serial Number
        if self.lot_id:
            domain += ' AND lot_id = %s'
            args += (self.lot_id.id,)
        #case 3: Filter on One product
        
        #case 4: Filter on A Pack
        if self.package_id:
            domain += ' AND package_id = %s'
            args += (self.package_id.id,)
        #case 5: Filter on One product category + Exahausted Products
        if self.category_id:
            categ_products = Product.search([('categ_id', 'in', self.category_id.ids)])
            domain += ' AND product_id = ANY (%s)'
            args += (categ_products.ids,)
            products_to_filter |= categ_products
        
        if self.template:
            product_tmpl_ids = []
            for dept in self.template.dept_ids:
                self.env.cr.execute("""select id from ofm_product_dept where ofm_sub_dept_id::integer = %s
                    """ % dept.dept_id.ofm_sub_dept_id)
                sub_dept_ids = self.env.cr.dictfetchall()
                sub_dept_ids = [d['id'] for d in sub_dept_ids if 'id' in d]
                sub_dept_ids = ','.join(map(str, sub_dept_ids))
                if dept.brand_id:
                    self.env.cr.execute("""select pt.id
                        from product_product pp
                        inner join product_template pt on pp.product_tmpl_id = pt.id
                        inner join stock_quant sq on sq.product_id = pp.id
                        inner join stock_location sl on sq.location_id = sl.id
                        where pt.dept_ofm::integer in ({0})
                            and pt.active = true
                            and sq.location_id::integer = {1}
                            and brand_id::integer = {2}
                    """.format(sub_dept_ids, self.location_id.id, dept.brand_id.id))
                    prod = self.env.cr.dictfetchall()
                    prod = [d['id'] for d in prod if 'id' in d]
                    product_tmpl_ids += prod
                else:
                    self.env.cr.execute("""select pt.id
                        from product_product pp
                        inner join product_template pt on pp.product_tmpl_id = pt.id
                        inner join stock_quant sq on sq.product_id = pp.id
                        inner join stock_location sl on sq.location_id = sl.id
                        where pt.dept_ofm::integer in ({0})
                            and pt.active = true
                            and sq.location_id::integer = {1}
                    """ .format(sub_dept_ids, self.location_id.id))
                    prod = self.env.cr.dictfetchall()
                    prod = [d['id'] for d in prod if 'id' in d]
                    product_tmpl_ids += prod
            product_tmpl_ids = ','.join(map(str, product_tmpl_ids))
            self.env.cr.execute("""select id 
                        from product_product 
                        where product_tmpl_id::integer in (%s)
                    """ % product_tmpl_ids)
            product_ids = self.env.cr.dictfetchall()
            product_ids = [d['id'] for d in product_ids if 'id' in d]
            product_ids = Product.browse(product_ids)
            products_to_filter |= product_ids
            domain += ' AND product_id = ANY (%s)'
            args += (product_ids.ids,)
            self.filter = 'partial'
        else:
            if self.product_dept and self.filter == 'dept':
                product_tmpl_ids = self.env['product.template'].search([('parent_dept_ofm', 'in',self.product_dept.ids)])
                product_ids = Product.search([('product_tmpl_id', 'in', product_tmpl_ids.ids)])
                domain += ' AND product_id = ANY (%s)'
                args += (product_ids.ids,)

            if self.product_sub_dept and self.filter == 'sub_dept':
                product_tmpl_ids = self.env['product.template'].search([('dept_ofm', 'in',self.product_sub_dept.ids)])
                product_ids = Product.search([('product_tmpl_id', 'in', product_tmpl_ids.ids)])
                domain += ' AND product_id = ANY (%s)'
                args += (product_ids.ids,)

            if self.product_id:
                domain += ' AND product_id = %s'
                args += (self.product_id.id,)
                products_to_filter |= self.product_id
            
        domain += ' GROUP BY product_id, location_id, lot_id, package_id, partner_id'
        
        self.env.cr.execute("""SELECT product_id, sum(qty) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
            FROM stock_quant sq
            LEFT JOIN product_product pp
            ON pp.id = sq.product_id
            WHERE %s
            """ % domain, args)
        data = self.env.cr.dictfetchall()
        if data:
            for product_data in data:
                # replace the None the dictionary by False, because falsy values are tested later on
                for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                    product_data[void_field] = False
                product_data['theoretical_qty'] = product_data['product_qty']
                product_data['product_qty'] = 0
                if product_data['product_id']:
                    product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
                    quant_products |= Product.browse(product_data['product_id'])
                vals.append(product_data)
        if self.exhausted:
            if products_to_filter or self.type == 'full':
                exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
                vals.extend(exhausted_vals)
        return vals

    def _get_exhausted_inventory_line(self, products, quant_products):
        '''
        This function return inventory lines for exausted products
        :param products: products With Selected Filter.
        :param quant_products: products available in stock_quants
        '''
        vals = []
        exhausted_domain = [('type', 'not in', ('service', 'consu', 'digital'))]
        if products:
            exhausted_products = products - quant_products
            exhausted_domain += [('id', 'in', exhausted_products.ids)]
        else:
            exhausted_domain += [('id', 'not in', quant_products.ids)]
        exhausted_products = self.env['product.product'].search(exhausted_domain)
        for product in exhausted_products:
            vals.append({
                'inventory_id': self.id,
                'product_id': product.id,
                'location_id': self.location_id.id,
            })
        return vals

class InventoryLine(models.Model):
    _name = "stock.inventory.cycle.count.line"
    _description = "Inventory Line"

    inventory_id = fields.Many2one(
        'stock.inventory.cycle.count', 'Inventory',
        index=True, ondelete='cascade'
    )
    partner_id = fields.Many2one(
        'res.partner', 
        'Owner'
    )
    product_id = fields.Many2one(
        'product.product', 'Product',
        index=True, required=True
    )
    product_name = fields.Char(
        'Product Name', 
        related='product_id.name', 
        store=True, 
        readonly=True
    )
    product_code = fields.Char(
        'Product Code', 
        related='product_id.default_code', 
        store=True
    )
    product_uom_id = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        required=True,
        readonly=True,
        default=lambda self: self.env.ref('product.product_uom_unit', raise_if_not_found=True)
    )
    product_uom_name = fields.Char(
        'Product UOM name', 
        related='product_uom_id.name', 
        store=True
    )
    product_qty = fields.Integer(
        'Checked Quantity',
        default=False
    )
    location_id = fields.Many2one(
        'stock.location', 'Location',
        index=True, 
        required=True
    )
    # TDE FIXME: necessary ? only in order -> replace by location_id
    location_name = fields.Char(
        'Location Name', 
        related='location_id.complete_name', 
        store=True
    )
    package_id = fields.Many2one(
        'stock.quant.package', 
        'Pack', 
        index=True
    )
    prod_lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        domain="[('product_id','=',product_id)]")
    # TDE FIXME: necessary ? -> replace by location_id
    prodlot_name = fields.Char(
        'Serial Number Name',
        related='prod_lot_id.name', 
        store=True, 
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company', 'Company', 
        related='inventory_id.company_id',
        index=True, 
        readonly=True, 
        store=True
    )
    # TDE FIXME: necessary ? -> replace by location_id
    state = fields.Selection(
        'Status',  
        related='inventory_id.state', 
        readonly=True
    )
    theoretical_qty = fields.Float(
        'System Quantity', 
        compute='_compute_theoretical_qty',
        digits=dp.get_precision('Product Unit of Measure'), 
        readonly=True, 
        store=True
    )
    inventory_location_id = fields.Many2one(
        'stock.location', 'Location', 
        related='inventory_id.location_id', 
        related_sudo=False
    )
    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        related="inventory_id.branch_id"
    )
    value = fields.Float(
        'Product value', 
    )
    fee = fields.Float(
        'Fee',
        compute="fee_calculate",
        store=True 
    )
    diff = fields.Integer(
        'Different', 
        default=0
    )
    last_count = fields.Integer(
        'Last Counted',
        default=0
    )
    counted_number = fields.Integer(
        'Counted number',
        default=1
    )
    barcode = fields.Char(
        string='Barcode',
        related='product_id.barcode', 
        store=True, 
        readonly=True
    )
    reason_code = fields.Many2one(
        'inventory.reason.code',
        string='Reason Code'
    )
    is_real_quantity_edit = fields.Boolean(
        default=False
    )

    @api.one
    @api.depends('product_id','product_qty')
    def fee_calculate(self):
        for inven in self:
            inven.fee = inven.value * 0.05

    @api.one
    @api.depends('location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id')
    def _compute_theoretical_qty(self):
        if not self.product_id:
            self.theoretical_qty = 0
            return
        theoretical_qty = sum([x.qty for x in self._get_quants()])
        if theoretical_qty and self.product_uom_id and self.product_id.uom_id != self.product_uom_id:
            theoretical_qty = self.product_id.uom_id._compute_quantity(theoretical_qty, self.product_uom_id)
        self.theoretical_qty = theoretical_qty
    
    @api.onchange('product_id')
    def onchange_product(self):
        res = {}
        # If no UoM or incorrect UoM put default one from product
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            res['domain'] = {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return res

    @api.onchange('product_qty')
    def onchange_product_qty(self):
        avg_price = self.env['average.price'].search([('branch_id', '=', self.inventory_id.branch_id.id),
                                                ('stock_location_id', '=', self.inventory_location_id.id),
                                                ('product_id', '=', self.product_id.id)]
                                                , limit=1)
        self.is_real_quantity_edit = True
        self.write({
            'diff': self.product_qty - self.theoretical_qty,
            'last_count': self.product_qty,
            'value': avg_price.cost * self.diff if avg_price else self.product_id.product_tmpl_id.list_price * self.diff,
            'fee': self.value * 0.05,
            'count_number': self.counted_number + 1,
        })

    @api.onchange('product_id', 'location_id', 'product_uom_id', 'prod_lot_id', 'partner_id', 'package_id')
    def onchange_quantity_context(self):
        if self.product_id and self.location_id and self.product_id.uom_id.category_id == self.product_uom_id.category_id:  # TDE FIXME: last part added because crash
            self._compute_theoretical_qty()
            self.product_qty = self.theoretical_qty

    @api.multi
    def write(self, values):
        values.pop('product_name', False)
        if 'product_qty' in values:
            values.update({
                'diff':  int(values['product_qty']) - self.theoretical_qty,
                'last_count': values['product_qty']
            })
        res = super(InventoryLine, self).write(values)
        return res

    @api.model
    def create(self, values):
        values.pop('product_name', False)
        if 'product_id' in values and 'product_uom_id' not in values:
            values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
            # values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
        existings = self.search([
            ('product_id', '=', values.get('product_id')),
            ('inventory_id.state', '=', 'confirm'),
            ('location_id', '=', values.get('location_id')),
            ('partner_id', '=', values.get('partner_id')),
            ('package_id', '=', values.get('package_id')),
            ('prod_lot_id', '=', values.get('prod_lot_id'))])
        res = super(InventoryLine, self).create(values)
        if existings:
            raise UserError(_("You cannot have two inventory adjustements in state 'in Progess' with the same product"
                              "(%s), same location(%s), same package, same owner and same lot. Please first validate"
                              "the first inventory adjustement with this product before creating another one.") %
                            (res.product_id.display_name, res.location_id.display_name))
        return res

    def _get_quants(self):
        return self.env['stock.quant'].search([
            ('company_id', '=', self.company_id.id),
            ('location_id', '=', self.location_id.id),
            ('lot_id', '=', self.prod_lot_id.id),
            ('product_id', '=', self.product_id.id),
            ('owner_id', '=', self.partner_id.id),
            ('package_id', '=', self.package_id.id)])

    