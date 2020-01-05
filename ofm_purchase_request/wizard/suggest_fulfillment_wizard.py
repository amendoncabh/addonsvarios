from datetime import datetime

from psycopg2 import OperationalError

from odoo import fields, api, models, _
from odoo.exceptions import except_orm
from odoo.tools import float_compare, float_round, DEFAULT_SERVER_DATETIME_FORMAT


class SuggestFulfillmentWizard(models.TransientModel):
    _name = 'suggest.fulfillment.wizard'

    parent_dept_ofm = fields.Many2one(
        comodel_name='ofm.product.dept',
        string='Dept OFM',
        domain=[
            ('dept_parent_id', '=', False),
        ],
        required=True,
        translate=True,
    )

    dept_ofm = fields.Many2one(
        comodel_name='ofm.product.dept',
        string='Sub Dept OFM',
        domain=[
            ('dept_parent_id', '!=', False),
        ],
        translate=True,
    )

    brand_id = fields.Many2one(
        comodel_name='product.brand',
        string='Brand',
    )

    @api.onchange('parent_dept_ofm')
    def set_dept_ofm(self):
        self.dept_ofm = False

        query_parent_dept_ofm = ''

        if all([
            self.parent_dept_ofm,
            not self.dept_ofm,
        ]):
            query_parent_dept_ofm = """
                and dept_parent_id = %s
            """ % self.parent_dept_ofm.id

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
                'dept_ofm': dept_ofm_domain
            },
        }

    @api.multi
    def action_suggest_fulfillment(self):
        for rec in self:
            context = dict(rec._context)
            context.update({
                'company_id': rec.env.user.company_id,
                'branch_id': rec.env.user.branch_id,
                'type_purchase_ofm': True,
                'action_return': {}
            })

            res = rec.with_context(context).suggest_fulfillment_calculation()

            # Search all confirmed stock_moves and try to assign them
            confirmed_moves = rec.env['stock.move'].search([
                ('state', '=', 'confirmed'),
                ('product_uom_qty', '!=', 0.0)
            ],
                limit=None,
                order='priority desc, date_expected asc'
            )

            for x in xrange(0, len(confirmed_moves.ids), 100):
                # TDE CLEANME: muf muf
                rec.env['stock.move'].browse(confirmed_moves.ids[x:x + 100]).action_assign()

            return res

    def _make_po_select_supplier(self, suppliers):
        """ Method intended to be overridden by customized modules to implement any logic in the
            selection of supplier.
        """
        return suppliers[0]

    def get_orderpoint(self):
        company_id = self._context.get('company_id', False)
        branch_id = self._context.get('branch_id', False)
        query_orderpoint_domain = ''
        query_product_domain = ''

        if company_id:
            query_orderpoint_domain += ' and company_id = %s' % company_id.id

        if branch_id:
            query_orderpoint_domain += ' and branch_id = %s' % branch_id.id

        if self.parent_dept_ofm:
            query_product_domain += ' and parent_dept_ofm = %s' % self.parent_dept_ofm.id

        if self.dept_ofm:
            dept_ofm_ids = self.env['ofm.product.dept'].search([
                ('ofm_sub_dept_id', '=', self.dept_ofm.ofm_sub_dept_id)
            ])

            dept_ofm_ids = '(' + ','.join(map(str, dept_ofm_ids.ids)) + ')'

            query_product_domain += ' and dept_ofm in %s' % dept_ofm_ids

        if self.brand_id:
            query_product_domain += ' and brand_id = %s' % self.brand_id.id

        prs_product_status = self.env['ir.config_parameter'].search([
            ('key', '=', 'prs_product_status')
        ]).value

        if prs_product_status:
            prs_product_status = prs_product_status.split(',')
            prs_product_status = ','.join('\'{0}\''.format(status) for status in prs_product_status)

            query_product_domain += ' and prod_status in ({0})'.format(prs_product_status)

        query_str = """
            select orderpoint.op_id
            from (
                select orderpoint.op_id,
                    orderpoint.op_product_id
                from (
                    select id as op_id,
                        product_id as op_product_id
                    from stock_warehouse_orderpoint
                    where active = true
                        and product_max_qty != 0
                        %s
                ) as orderpoint
                inner join (
                    select prod.prod_id
                    from (
                        select id as prod_id,
                            product_tmpl_id
                        from product_product
                        where active = true
                    ) as prod
                    inner join (
                        select id
                        from product_template
                        where active = true
                            and purchase_ok = true
                            %s
                    ) as prod_temp
                    on prod.product_tmpl_id = prod_temp.id
                ) as product
                on orderpoint.op_product_id = product.prod_id
            ) as orderpoint
            left join (
                select distinct purchase_line.product_id as po_product_id
                from (
                    select id
                    from purchase_order
                    where type_purchase_ofm = true
                        and state = 'draft'
                        %s
                ) as purchase
                inner join (
                    select order_id,
                        product_id
                    from ofm_purchase_order_line
                ) as purchase_line
                on purchase.id = purchase_line.order_id
            ) as purchase
            on orderpoint.op_product_id = purchase.po_product_id
            where purchase.po_product_id is null
        """ % (
            query_orderpoint_domain,
            query_product_domain,
            query_orderpoint_domain
        )

        self.env.cr.execute(query_str)
        query_result = self.env.cr.dictfetchall()

        orderpoint_list = []

        for orderpoint_id in query_result:
            orderpoint_list.append(orderpoint_id['op_id'])

        orderpoint_ids = self.env['stock.warehouse.orderpoint'].browse(orderpoint_list)

        return orderpoint_ids

    def prepare_product_orderpoint(self, partner_id):
        orderpoint_ids = self.get_orderpoint()

        if not orderpoint_ids:
            raise except_orm(_('Error!'),
                             'Don\'t have product for suggest fulfillment or product has been created to PR.')
        else:
            product_list = {}

            for orderpoint_id in orderpoint_ids:
                try:
                    suppliers = orderpoint_id.product_id.seller_ids.filtered(
                        lambda rec:
                        rec.name == partner_id
                    )

                    if not suppliers:
                        vendor_name = self.env.context.get(
                            'vendor_name',
                            str(partner_id)
                        )
                        msg_error = (
                            """
                            Don't Have {vendor_name} in this order point {order_point_name} 
                            """
                        ).format(
                            vendor_name=vendor_name,
                            order_point_name=orderpoint_id.name
                        )
                        raise except_orm(
                            _('Error!'),
                            msg_error
                        )

                    supplier = self._make_po_select_supplier(suppliers)

                    if supplier:
                        op_product_virtual = orderpoint_id.virtual_available
                        if op_product_virtual is None:
                            continue
                        if float_compare(op_product_virtual, orderpoint_id.product_min_qty,
                                         precision_rounding=orderpoint_id.product_uom.rounding) <= 0:
                            qty = max(orderpoint_id.product_min_qty, orderpoint_id.product_max_qty) - op_product_virtual
                            remainder = orderpoint_id.qty_multiple > 0 and qty % orderpoint_id.qty_multiple or 0.0

                            if float_compare(remainder, 0.0,
                                             precision_rounding=orderpoint_id.product_uom.rounding) > 0:
                                qty += orderpoint_id.qty_multiple - remainder

                            if float_compare(qty, 0.0, precision_rounding=orderpoint_id.product_uom.rounding) < 0:
                                continue

                            qty_rounded = float_round(qty, precision_rounding=orderpoint_id.product_uom.rounding)

                            if qty_rounded > 0:
                                branch = product_list.get(orderpoint_id.branch_id.id, False)
                                product = {
                                    'product_id': orderpoint_id.product_id,
                                    'qty': qty_rounded
                                }

                                if branch:
                                    branch.append(product)
                                else:
                                    product_list.update({
                                        orderpoint_id.branch_id.id: [product]
                                    })

                except OperationalError:
                    raise

            return product_list

    def prepare_purchase_order(self, partner_id, company_id, branch_id):
        picking_type_id = self.env['purchase.order'].get_picking_type(company_id.id, branch_id.id)

        purchase_order = {
            'type_to_ofm': 'fulfillment',
            'date_order': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'partner_id': partner_id.id,
            'company_id': company_id.id,
            'branch_id': branch_id.id,
            'type_purchase_ofm': True,
            'picking_type_id': picking_type_id.id,
            'currency_id': partner_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id,
        }

        return purchase_order

    def prepare_purchase_order_line(self, order_id, partner_id, product_suggest, company_id, branch_id):
        product_branch = product_suggest.get(branch_id.id, False)
        po_date_order = order_id.get('date_order')
        po_currency_id = partner_id.property_purchase_currency_id or self.env.user.company_id.currency_id
        order_line = []

        ctx = dict(self._context)
        ctx.update({
            'company_id': company_id.id,
            'branch_id': branch_id.id,
        })

        for product in product_branch:
            product_id = product.get('product_id')
            product_qty = product.get('qty')
            suppliers = product_id.seller_ids.filtered(
                lambda rec:
                rec.name == partner_id
            )
            supplier = self._make_po_select_supplier(suppliers)

            seller = product_id.with_context(ctx)._select_seller(
                partner_id=supplier.name,
                quantity=product_qty,
                date=po_date_order and po_date_order[:10],
                uom_id=product_id.uom_po_id)

            taxes = product_id.supplier_taxes_id
            taxes_id = taxes
            if taxes_id:
                taxes_id = taxes_id.filtered(lambda x: x.company_id.id == company_id.id)

            price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                                 product_id.supplier_taxes_id,
                                                                                 taxes_id,
                                                                                 company_id) if seller else 0.0
            if price_unit and seller and po_currency_id and seller.currency_id != po_currency_id:
                price_unit = seller.currency_id.compute(price_unit, po_currency_id)

            product_lang = product_id.with_context({
                'lang': supplier.name.lang,
                'partner_id': supplier.name.id,
            })
            name = product_lang.display_name

            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase

            date_planned = self.env['purchase.order.line']._get_date_planned(seller, po=False).strftime(
                DEFAULT_SERVER_DATETIME_FORMAT)

            order_line.append([
                0,
                False,
                {
                    'name': name,
                    'product_qty': product_qty,
                    'product_id': product_id.id,
                    'product_uom': product_id.uom_po_id.id,
                    'price_unit': price_unit,
                    'date_planned': date_planned,
                    'taxes_id': [(6, 0, taxes_id.ids)],
                }
            ])

        return order_line

    def make_po_suggest_fulfillment(self, partner_id, product_suggest):
        company_id = self._context.get('company_id', False)
        company_id = company_id if company_id else self.env.user.company_id
        branch_id = self._context.get('branch_id', False)
        branch_id = branch_id if branch_id else self.env.user.branch_id

        order_id = self.prepare_purchase_order(partner_id, company_id, branch_id)
        order_line_ids = self.prepare_purchase_order_line(order_id, partner_id, product_suggest, company_id, branch_id)

        if all([
            order_id,
            order_line_ids
        ]):
            order_id.update({
                'ofm_purchase_order_line_ids': order_line_ids
            })

            context = dict(self._context)
            context.update({
                'is_suggest': True
            })

            order_id = self.env['purchase.order'].with_context(context).create(order_id)

            if order_id:
                order_id._compute_date_planned()

                for order_line_id in order_id.ofm_purchase_order_line_ids:
                    order_line_id.onchange_product_uom_show()
                    order_line_id.onchange_price_unit_show()
                    order_line_id.onchange_date_planned_show()
                    order_line_id.onchange_product_status_name_abb()
                    order_line_id.onchange_calculate_amount()

                order_id._amount_all_ofm()

            return order_id
        else:
            return False

    def suggest_fulfillment_calculation(self):
        prs_default_vendor = self.env['ir.config_parameter'].search([
            ('key', '=', 'prs_default_vendor')
        ]).value
        partner_id = self.env['res.partner'].search([
            ('vat', '=', prs_default_vendor)
        ])

        ctx = dict(self.env.context.copy())
        ctx.update({
            'vendor_name': (partner_id.id, prs_default_vendor)
        })

        product_suggest = self.with_context(
            ctx
        ).prepare_product_orderpoint(partner_id)

        if len(product_suggest) <= 0:
            order_id = False
        else:
            order_id = self.make_po_suggest_fulfillment(partner_id, product_suggest)

        if order_id:
            action = self.env.ref(
                'ofm_purchase_request.ofm_purchase_request_action'
            ).read()[0]
            action['view_mode'] = 'form'
            action['views'].pop(0)
            action['res_id'] = order_id.id

            return action
        else:
            raise except_orm(_('Error!'),
                             'Don\'t have product suggest fulfillment or product has been created on PR.')

        return {}