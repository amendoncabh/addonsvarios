# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.inventory"
    _order = "id desc"

    date_now = fields.Date(
        'Date',
        required=True,
        readonly=True,
        default=fields.Datetime.now
    )

    finish_date = fields.Date(
        'Finish Date',
        required=True,
        readonly=True,
        default=fields.Datetime.now()
    )

    template_id = fields.Many2one(
        'template.of.product',
        string='Template'
    )

    is_template = fields.Boolean(
        default=False
    )

    type = fields.Selection([
        ('full', 'Full Stock Take'),
        ('cyclic', 'Cyclic Count')
    ])

    inventory_of = fields.Selection([
        ('dept', 'Product Dept'),
        ('sub_dept', 'Product Sub Dept'),
        ('category', 'One product category'),
        ('product', 'One product only'),
        ('partial', 'Select products manually')
    ])

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

    @api.onchange('template_id','type')
    def onchange_template(self):
        self.inventory_of = ''
        if self.template_id:
            self.is_template = False
        else:
            self.is_template = True

    @api.onchange('type')
    def onchange_type(self):
        if self.type == 'full':
            self.product_dept = False
            self.product_sub_dept = False
            self.category_id = False
            self.product_id = False
    
    @api.onchange('inventory_of')
    def onchange_inventory_of(self):
        if self.inventory_of == 'dept':
            self.product_sub_dept = False
            self.product_id = False
            self.category_id = False

        elif self.inventory_of == 'sub_dept':
            self.product_dept = False
            self.product_id = False
            self.category_id = False

        elif self.inventory_of == 'category':
            self.product_dept = False
            self.product_sub_dept = False
            self.product_id = False

        elif self.inventory_of == 'product':
            self.product_dept = False
            self.product_sub_dept = False
            self.category_id = False
            self.filter = 'product'
        else:
            self.product_dept = False
            self.product_sub_dept = False
            self.category_id = False
            self.product_id = False

    @api.multi
    def action_start_manual(self):
        for inventory in self:
            vals = {'state': 'confirm', 'date': fields.Datetime.now()} 
            if (inventory.inventory_of != 'partial') and not inventory.line_ids:
                vals.update({
                    'line_ids': [(0, 0, line_values) for line_values in inventory._get_inventory_lines_values_manual()],
                })
            inventory.write(vals)
        return True
    prepare_inventory_manual = action_start_manual

    @api.multi
    def _get_inventory_lines_values_manual(self):
        # TDE CLEANME: is sql really necessary ? I don't think so
        locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
        domain = ' location_id in %s AND active = TRUE'
        args = (tuple(locations.ids),)

        vals = []
        product_list = self.env['product.product']
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
        
        if self.template_id:
            product_tmpl_ids = self.env['product.template']
            for dept in self.template_id.dept_ids:
                product_tmpl_ids += self.env['product.template'].search([('dept_ofm', '=',dept.dept_id.id)])
            product_ids = Product.search([('product_tmpl_id', 'in', product_tmpl_ids.ids)])
            products_to_filter |= product_ids
            domain += ' AND product_id = ANY (%s)'
            args += (product_ids.ids,)
            self.filter = 'partial'
        else:
            if self.product_dept and self.inventory_of == 'dept':
                product_tmpl_ids = self.env['product.template'].search([('parent_dept_ofm', 'in',self.product_dept.ids)])
                product_ids = Product.search([('product_tmpl_id', 'in', product_tmpl_ids.ids)])
                domain += ' AND product_id = ANY (%s)'
                args += (product_ids.ids,)

            if self.product_sub_dept and self.inventory_of == 'sub_dept':
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
        else:
            products_to_filter |= product_list
        if self.exhausted:
            exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
            vals.extend(exhausted_vals)
        return vals
        
    @api.multi
    def action_done(self):
        self.finish_date = fields.Datetime.now()
        result = super(StockMove, self).action_done()
        return result