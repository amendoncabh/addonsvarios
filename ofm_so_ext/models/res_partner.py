# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.addons.base.res.res_partner import FormatAddress
from odoo.exceptions import except_orm


class SoExtResPartner(models.Model, FormatAddress):
    _inherit = "res.partner"

    vendor_ship_id = fields.Integer(
        string='Vendor Shipping Address ID',
        readonly=True,
        default=0,
    )

    is_update_shipping = fields.Boolean(
        string="Flag Update Shipping Address",
        readonly=True,
        default=False,
    )

    def vendor_call_api_update_ship_address(self):
        call_api = self.env['tr.call.api']
        ship_address = call_api.with_context(self._context).get_shipping_address_by_query()

        ctx = dict(self._context)
        ctx.update({
            'ship_address': ship_address,
        })

        call_api.with_context(ctx).call_api_shipping()

    def get_child_ids_from_vals(self, vals):
        child_ids = vals.get('child_ids', False)
        child_ids_delete = []

        if child_ids:
            for child_id in child_ids:
                if child_id[0] == 1:
                    child_id[2].update({
                        'is_update_shipping': True,
                    })
                elif child_id[0] == 2:
                    child_ids_delete.append(child_id[1])

            vals.update({
                'child_ids': child_ids
            })
        else:
            vals.update({
                'is_update_shipping': True,
            })

        return {
            'vals': vals,
            'child_ids_delete': child_ids_delete,
        }

    def update_vals_child_ids(self, vals):
        vals_return = self.get_child_ids_from_vals(vals)

        vals = vals_return.get('vals', vals)
        child_ids_delete = vals_return.get('child_ids_delete', vals)

        ctx = dict(self._context)
        ctx.update({
            'child_ids_delete': child_ids_delete,
            'ship_type': 'delivery',
            'is_except_raise': True,
        })

        # self.with_context(ctx).vendor_call_api_update_ship_address()

        return vals

    @api.multi
    def write(self, vals):
        for rec in self:
            vals = rec.update_vals_child_ids(vals)

            res = super(SoExtResPartner, self).write(vals)

            return res

    @api.model
    def get_partner_info(self, keys):
        if not keys.get('key', False):
            raise except_orm(_('Error!'), _("Api Attribute Fail."))

        key = ''.join([
            '%',
            keys['key'],
            '%'
        ])

        params = (
            key,
            key,
            key,
            key,
            key,
        )

        query_str = """
        select id
        from res_partner
        where active = true and customer = true 
        and parent_id is null
        and (
            first_name like '%s' or
            last_name like '%s' or
            phone like '%s' or
            email like '%s'or
            vat like '%s'
        )
        """ % params
        self.env.cr.execute(query_str)
        results = self.env.cr.dictfetchall()
        partner_ids = [item['id'] for item in results]
        partner_ids = self.search_read([
            ('id', 'in', partner_ids)
        ], [])

        for partner_id in partner_ids:
            child_ids = partner_id.get('child_ids', False)
            if child_ids and len(child_ids):
                partner_id['child_res_partner_ids'] = self.search_read([
                    ('id', 'in', child_ids)
                ], [])

        return partner_ids

    @api.multi
    def _sale_total(self):
        sale_order = self.env['sale.order']
        all_partners_and_children = {}
        all_partner_ids = []

        for partner in self:
            all_partners_and_children[partner] = self.search([('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]

            # for partner in self:
            sale = sale_order.search(
                [
                    ('partner_id', 'in', all_partner_ids),
                    ('state', '=', 'sale'),
                    ('sale_payment_type', '=', 'credit')
                ]
            )
            inv_total = 0
            sale_total = 0
            for sl in sale:
                invoice = sl.invoice_ids.filtered(
                    lambda x: x.state in ['paid', 'open'] and x.type in ['out_invoice', 'in_invoice']
                )
                inv_total += sum(line.amount_total - line.residual_signed for line in invoice)
                sale_total += sl.amount_total

            partner.total_sale = sale_total - inv_total

    @api.multi
    def _invoice_total(self):
        account_invoice_report = self.env['account.invoice.report']
        if not self.ids:
            self.total_invoiced = 0.0
            return True

        user_currency_id = self.env.user.company_id.currency_id.id
        all_partners_and_children = {}
        all_partner_ids = []
        for partner in self:
            # price_total is in the company currency
            all_partners_and_children[partner] = self.search([('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]

        # searching account.invoice.report via the orm is comparatively expensive
        # (generates queries "id in []" forcing to build the full table).
        # In simple cases where all invoices are in the same currency than the user's company
        # access directly these elements

        invoice_ids = self.env['account.invoice'].search([
            ('partner_id', 'in', all_partner_ids),
            ('state', 'not in', ['draft', 'cancel', 'open']),
            ('company_id', '=', self.env.user.company_id.id),
            ('type', '=', 'out_invoice'),
            ('so_id.sale_payment_type', '=', 'credit'),
        ])

        # generate where clause to include multicompany rules

        domain_query = [
            ('partner_id', 'in', all_partner_ids),
            ('state', 'not in', ['draft', 'cancel']),
            ('company_id', '=', self.env.user.company_id.id),
            ('type', '=', 'out_invoice'),
        ]

        if invoice_ids:
            domain_query += [('id', 'in', invoice_ids.ids)]

            where_query = account_invoice_report._where_calc(domain_query)
            account_invoice_report._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()

            # price_total is in the company currency
            query = """
                      SELECT SUM(residual) as total, partner_id
                        FROM account_invoice_report account_invoice_report
                       WHERE %s
                       GROUP BY partner_id
                    """ % where_clause
            self.env.cr.execute(query, where_clause_params)
            price_totals = self.env.cr.dictfetchall()
            for partner, child_ids in all_partners_and_children.items():
                partner.total_invoiced = sum(
                    price['total'] for price in price_totals if price['partner_id'] in child_ids
                )