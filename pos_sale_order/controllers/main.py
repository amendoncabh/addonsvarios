# -*- coding: utf-8 -*-
import json
import logging

import werkzeug.utils

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SaleController(http.Controller):

    # @http.route('/sale/web/<string:param>', type='http', auth='user')
    @http.route('/sale/web/', type='http', auth='user')
    def sale_web(self, debug=False, **k):
        sale_session = request.env['sale.session'].search([
            ('user_id', '=', request.session.uid),
        ], order="write_date desc, id desc", limit=1)

        if not sale_session:
            return werkzeug.utils.redirect('/web#action=pos_sale_order.action_pos_config_kanban_so')

        sale_session.login()
        session_info = request.env['ir.http'].session_info()
        session_info.update({
            'sale_session_id': sale_session.id,
            'config_id': sale_session.config_id.id,
            'company_id': sale_session.company_id.id,
            'branch_id': sale_session.branch_id.id,
            'sale_type': sale_session.sale_type
        })

        context = {
            'session_info': json.dumps(session_info),
            'sale': True,
        }
        return request.render('point_of_sale.index', qcontext=context)

    @http.route('/web/search_sale_order_api/', type='json', auth="user")
    def search_sale_order_api(self, key=None, sale_type=None, object_id=None):

        records = None
        if key:
            key = ''.join([key, '%'])

            params = (
                sale_type,
                key,
                key,
                key,
                key,
                key,
                key,
            )

            query_str = """
                select so.id
                from sale_order so
                inner join res_partner rp on rp.id = so.partner_id
                left join (
                    select so_id, number
                    from account_invoice
                )inv on inv.so_id = so.id
                where
                type_sale_ofm = %s
                and (
                    so.name like '%s'::text
                    or inv.number like '%s'::text
                    or so.quotation_no like '%s'::text
                    or rp.name like '%s'::text
                    or rp.first_name like '%s'::text
                    or rp.last_name like '%s'::text
                )
            """ % params
            request.env.cr.execute(query_str)
            results = request.env.cr.dictfetchall()

            records = request.env['sale.order'].search_read(
                [('id', 'in', [item['id'] for item in results])],
                ['name', 'quotation_no', 'partner_id', 'date_order', 'amount_total', 'state',
                 'return_status', 'branch_id'],
            )

        else:
            records = request.env['sale.order'].with_context({
                'object_id': int(object_id),
            }).search_read_so_from_ui()

        if not records:
            return {
                'length': 0,
                'records': []
            }
        return {
            'length': len(records),
            'records': records
        }

    @http.route('/web/new_tab_api/', type='json', auth="user")
    def action_open_new_tab(self, model_name, menu_id, action_id):

        menu_id = request.env.ref(menu_id).id
        action_id = request.env.ref(action_id).id

        view_type_url = "view_type=form"
        model_str_url = "model=%s" % model_name
        menu_id_url = "menu_id=%s" % str(menu_id)
        action_id_url = "action=%s" % str(action_id)

        record_url = '&'.join([
            view_type_url,
            model_str_url,
            menu_id_url,
            action_id_url
        ])

        return record_url
