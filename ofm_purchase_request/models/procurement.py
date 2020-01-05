# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime
from psycopg2 import OperationalError
from odoo import api, fields, models, registry, _
from odoo.exceptions import except_orm
from odoo.tools import float_compare, float_round, DEFAULT_SERVER_DATETIME_FORMAT


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    def _default_branch(self):
        return self.env.user.branch_id

    ofm_purchase_line_id = fields.Many2one(
        'ofm.purchase.order.line',
        string='Purchase Order Line'
    )

    def _make_po_get_domain(self, partner):
        domain = super(ProcurementOrder, self)._make_po_get_domain(partner)
        if self._context.get('type_purchase_ofm', False):
            domain += (
                ('branch_id', '=', self.env.user.branch_id.id),
                ('type_purchase_ofm', '=', True)
            )
        return domain

    @api.multi
    def _prepare_purchase_order(self, partner):
        res = super(ProcurementOrder, self)._prepare_purchase_order(partner)
        if self._context.get('type_purchase_ofm', False):
            res.update({
                'branch_id': self.env.user.branch_id.id
            })
        return res

    @api.multi
    def make_po(self):
        cache = {}
        res = []
        type_purchase_ofm = self._context.get('type_purchase_ofm', False)

        for procurement in self:
            if type_purchase_ofm:
                prs_default_vendor = self.env['ir.config_parameter'].search([
                    ('key', '=', 'prs_default_vendor')
                ]).value
                partner_id = self.env['res.partner'].search([
                    ('vat', '=', prs_default_vendor)
                ])
                suppliers = procurement.product_id.seller_ids.filtered(
                    lambda rec:
                        rec.name == partner_id
                )
            else:
                suppliers = procurement.product_id.seller_ids \
                    .filtered(lambda r: (not r.company_id or r.company_id == procurement.company_id) and (
                            not r.product_id or r.product_id == procurement.product_id))

            if not suppliers:
                procurement.message_post(
                    body=_('No vendor associated to product %s. Please set one to fix this procurement.') % (
                        procurement.product_id.name))
                continue

            supplier = procurement._make_po_select_supplier(suppliers)
            partner = supplier.name

            domain = procurement._make_po_get_domain(partner)

            if domain in cache:
                po = cache[domain]
            else:
                po = self.env['purchase.order'].search([dom for dom in domain])
                po = po[0] if po else False
                cache[domain] = po
            if not po:
                vals = procurement._prepare_purchase_order(partner)
                if type_purchase_ofm:
                    vals['type_purchase_ofm'] = type_purchase_ofm
                    vals['type_to_ofm'] = 'fulfillment'

                    if type_purchase_ofm:
                        default_vendor = procurement.env['ir.config_parameter'].search([('key', '=', 'prs_default_vendor')]).value
                        vals['partner_id'] = procurement.env['res.partner'].search([('vat', '=', default_vendor)]).id

                if procurement._context.get('branch_id', False):
                    vals['branch_id'] = procurement._context.get('branch_id', False).id

                po = self.env['purchase.order'].create(vals)
                name = (procurement.group_id and (procurement.group_id.name + ":") or "") + (
                            procurement.name != "/" and procurement.name or procurement.move_dest_id.raw_material_production_id and procurement.move_dest_id.raw_material_production_id.name or "")
                message = _(
                    "This purchase order has been created from: <a href=# data-oe-model=procurement.order data-oe-id=%d>%s</a>") % (
                          procurement.id, name)
                po.message_post(body=message)
                cache[domain] = po
            elif not po.procurement_name or procurement.origin not in po.procurement_name.split(', '):
                # Keep track of all procurements
                if po.procurement_name:
                    if procurement.origin:
                        po.write({'procurement_name': po.procurement_name + ', ' + procurement.origin})
                    else:
                        po.write({'procurement_name': po.procurement_name})
                else:
                    po.write({'procurement_name': procurement.origin})
                name = (self.group_id and (self.group_id.name + ":") or "") + (
                            self.name != "/" and self.name or self.move_dest_id.raw_material_production_id and self.move_dest_id.raw_material_production_id.name or "")
                message = _(
                    "This purchase order has been modified from: <a href=# data-oe-model=procurement.order data-oe-id=%d>%s</a>") % (
                          procurement.id, name)
                po.message_post(body=message)
            if po:
                res += [procurement.id]

            # Create Line
            po_line = False

            if type_purchase_ofm:
                po_order_line = po.ofm_purchase_order_line_ids
            else:
                po_order_line = po.order_line

            for line in po_order_line:
                if procurement.id not in line.procurement_ids.ids:
                    if line.product_id == procurement.product_id and line.product_uom == procurement.product_id.uom_po_id:
                        procurement_uom_po_qty = procurement.product_uom._compute_quantity(
                            procurement.product_qty,
                            procurement.product_id.uom_po_id
                        )
                        seller = procurement.product_id._select_seller(
                            partner_id=partner,
                            quantity=line.product_qty + procurement_uom_po_qty,
                            date=po.date_order and po.date_order[:10],
                            uom_id=procurement.product_id.uom_po_id)

                        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                                             line.product_id.supplier_taxes_id,
                                                                                             line.taxes_id,
                                                                                             self.company_id) if seller else 0.0
                        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
                            price_unit = seller.currency_id.compute(price_unit, po.currency_id)

                        po_line = line.write({
                            'product_qty': line.product_qty + procurement_uom_po_qty,
                            'price_unit': price_unit,
                            'procurement_ids': [(4, procurement.id)]
                        })
                        break
                else:
                    po_line = line

            if not po_line:
                vals = procurement._prepare_purchase_order_line(po, supplier)

                if type_purchase_ofm:
                    self.env['ofm.purchase.order.line'].create(vals)
                else:
                    self.env['purchase.order.line'].create(vals)

        return res

    def get_product_context(self, location_orderpoints):
        if self._context.get('branch_id', False):
            branch_id = self._context.get('branch_id').id
        else:
            branch_id = location_orderpoints[0].branch_id.id

        product_context = dict(
            self._context,
            location=location_orderpoints[0].location_id.id,
            branch_id=branch_id
        )

        return product_context

    @api.multi
    def run(self, autocommit=False):
        res = super(ProcurementOrder, self).run(autocommit)

        if self._context.get('type_purchase_ofm', False):
            if res:
                res = []
            for procurement in self:
                res += procurement._run()

        return res

    @api.model
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=False):
        """ Create procurements based on orderpoints.
        :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing
            1000 orderpoints.
            This is appropriate for batch jobs only.
        """
        if company_id and self.env.user.company_id.id != company_id:
            # To ensure that the company_id is taken into account for
            # all the processes triggered by this method
            # i.e. If a PO is generated by the run of the procurements the
            # sequence to use is the one for the specified company not the
            # one of the user's company
            self = self.with_context(company_id=company_id, force_company=company_id)

        OrderPoint = self.env['stock.warehouse.orderpoint']
        domain = self._get_orderpoint_domain(company_id=company_id)
        orderpoints_noprefetch = OrderPoint.with_context(prefetch_fields=False).search(
            domain,
            order=self._procurement_from_orderpoint_get_order()
        ).ids

        if len(orderpoints_noprefetch) == 0:
            value = False

        type_purchase_ofm = self._context.get('type_purchase_ofm', False)

        while orderpoints_noprefetch:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            OrderPoint = self.env['stock.warehouse.orderpoint']
            Procurement = self.env['procurement.order']
            ProcurementAutorundefer = Procurement.with_context(procurement_autorun_defer=True)
            procurement_list = []

            orderpoints = OrderPoint.browse(orderpoints_noprefetch[:1000])
            orderpoints_noprefetch = orderpoints_noprefetch[1000:]

            if type_purchase_ofm:
                orderpoints = orderpoints.filtered(
                    lambda x: x.branch_id.id == self.env.user.branch_id.id
                )

            # Calculate groups that can be executed together
            location_data = defaultdict(
                lambda: dict(products=self.env['product.product'], orderpoints=self.env['stock.warehouse.orderpoint'],
                             groups=list()))
            for orderpoint in orderpoints:
                key = self._procurement_from_orderpoint_get_grouping_key([orderpoint.id])
                location_data[key]['products'] += orderpoint.product_id
                location_data[key]['orderpoints'] += orderpoint
                location_data[key]['groups'] = self._procurement_from_orderpoint_get_groups([orderpoint.id])

            for location_id, location_data in location_data.iteritems():
                location_orderpoints = location_data['orderpoints']
                product_context = self.get_product_context(location_orderpoints)
                substract_quantity = location_orderpoints.subtract_procurements_from_orderpoints()

                for group in location_data['groups']:
                    if group.get('from_date'):
                        product_context['from_date'] = group['from_date'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if group['to_date']:
                        product_context['to_date'] = group['to_date'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    product_quantity = location_data['products'].with_context(product_context)._product_available()
                    for orderpoint in location_orderpoints:
                        try:
                            op_product_virtual = product_quantity[orderpoint.product_id.id]['virtual_available']
                            if op_product_virtual is None:
                                continue
                            if float_compare(op_product_virtual, orderpoint.product_min_qty,
                                             precision_rounding=orderpoint.product_uom.rounding) <= 0:
                                qty = max(orderpoint.product_min_qty, orderpoint.product_max_qty) - op_product_virtual
                                remainder = orderpoint.qty_multiple > 0 and qty % orderpoint.qty_multiple or 0.0

                                if float_compare(remainder, 0.0,
                                                 precision_rounding=orderpoint.product_uom.rounding) > 0:
                                    qty += orderpoint.qty_multiple - remainder

                                if float_compare(qty, 0.0, precision_rounding=orderpoint.product_uom.rounding) < 0:
                                    continue

                                qty -= substract_quantity[orderpoint.id]
                                qty_rounded = float_round(qty, precision_rounding=orderpoint.product_uom.rounding)
                                if qty_rounded > 0:
                                    new_procurement = ProcurementAutorundefer.create(
                                        orderpoint._prepare_procurement_values(qty_rounded,
                                                                               **group['procurement_values']))
                                    procurement_list.append(new_procurement)
                                    new_procurement.message_post_with_view('mail.message_origin_link',
                                                                           values={'self': new_procurement,
                                                                                   'origin': orderpoint},
                                                                           subtype_id=self.env.ref('mail.mt_note').id)
                                    self._procurement_from_orderpoint_post_process([orderpoint.id])
                                if use_new_cursor:
                                    cr.commit()

                        except OperationalError:
                            if use_new_cursor:
                                orderpoints_noprefetch += [orderpoint.id]
                                cr.rollback()
                                continue
                            else:
                                raise

            try:
                # TDE CLEANME: use record set ?
                procurement_list.reverse()
                procurements = self.env['procurement.order']
                for p in procurement_list:
                    procurements += p
                value = procurements.run()
                if use_new_cursor:
                    cr.commit()
            except OperationalError:
                if use_new_cursor:
                    cr.rollback()
                    continue
                else:
                    raise

            if use_new_cursor and not type_purchase_ofm:
                cr.commit()
                cr.close()

        if type_purchase_ofm:
            if value:
                procurement_order_ids = self.env['procurement.order'].search([
                    ('id', 'in', value)
                ])

                for procurement_order_id in procurement_order_ids:
                    action = self.env.ref(
                        'ofm_purchase_request.ofm_purchase_request_action'
                    ).read()[0]
                    action['view_mode'] = 'form'
                    action['views'].pop(0)
                    action['res_id'] = procurement_order_id.ofm_purchase_line_id.order_id.id

                    return action
            else:
                raise except_orm(_('Error!'),
                                 'Don\'t have suggest fulfillment or PR has been created by suggest fulfillment.')

        return {}

