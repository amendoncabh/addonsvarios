# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
import json
import psycopg2
from pytz import timezone

from datetime import datetime
from odoo.tools.translate import *
from odoo.tools.osutil import walksymlinks
from odoo import SUPERUSER_ID
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, except_orm

_logger = logging.getLogger(__name__)
_pr_model = 'purchase.order'
_so_model = 'sale.order'
_api_method_post = 'post'
_api_method_get = 'get'
_api_create_so = 'api_create_so'
_api_check_qty = 'api_check_qty'

# Methods to export the translation file

# load config from file
tools.config['prs_api_request_token'] = tools.config.get(
    'prs_api_request_token',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIxMDQxNzVjMy02OGE4LTRjMmEtYTZkZC1lMzk4NDM3MG'
    'M3NjgiLCJpYXQiOiIxNTQ3NjM4MDA2IiwidXNlcmlkIjoiMzIyMiIsImVtYWlsIjoiZmFrZUB0cmluaXR5LmNvbSIsI'
    'mVtcGxveWVlaWQiOiIiLCJleHAiOjE4NjI5OTgwMDYsImlzcyI6IkVBZWhMTWEvYnEzdnpHM2pzSC92MnZiaG5KeEN1'
    'QU5qQkxUaGRHSVc0dWlGcTVHS3RaY0xFZz09IiwiYXVkIjoiMGpTUkNlU2NSeFd4MHlQb0g3L01xWlduYWEvcTBPVnN'
    'salk3NzZYYnh2Zz0ifQ.oZXe_nGtjdAscNZS29ZLEGeP0LKPiY-DHyncmwx3-RM'
)
tools.config['prs_api_url_request_token'] = tools.config.get(
    'prs_api_url_request_token',
    'https://apis.officemate.co.th/uat-venus/authen/token'
)
tools.config['prs_api_url_check_qty'] = tools.config.get(
    'prs_api_url_check_qty',
    'https://apis.officemate.co.th/uat-venus/products/available'
)
tools.config['prs_api_url_create_so'] = tools.config.get(
    'prs_api_url_create_so',
    'https://apis.officemate.co.th/uat-venus/purchase/requisition'
)
tools.config['prs_api_url_create_rtv'] = tools.config.get(
    'prs_api_url_create_rtv',
    'https://apis.officemate.co.th/uat-venus/franchises/rtv'
)
tools.config['sale_api_url_shipping'] = tools.config.get(
    'sale_api_url_shipping',
    'https://apis.officemate.co.th/uat-venus/dropship/shipping'
)
tools.config['sale_api_url_check_qty'] = tools.config.get(
    'sale_api_url_check_qty',
    'https://apis.officemate.co.th/uat-venus/dropship/products/available'
)
tools.config['sale_api_url_create_so'] = tools.config.get(
    'sale_api_url_create_so',
    'https://apis.officemate.co.th/uat-venus/dropship/purchase/requisition'
)


class TRCallAPI(models.Model):
    _name = "tr.call.api"
    _description = "Call API By URL"

    @api.model
    def default_user_prs_api(self):
        name = 'user_api_prs'

        res_user_obj = self.env['res.users']
        res_user_id = res_user_obj.search([
            ('login', '=', name)
        ])

        if not res_user_id:
            res_user_obj.create({
                'name': name,
                'login': name,
                'password': 'ofm@api',
                'company_id': self.env.user.company_id.id,
                'groups_id': [
                    (
                        6,
                        0,
                        [
                            self.env.ref('purchase_request.group_purchase_request_user').id,
                            self.env.ref('purchase.group_purchase_user').id,
                            self.env.ref('ofm_purchase_request.purchase_request_ofm_group').id,
                            self.env.ref('ofm_so_ext.sale_dropship_group_sale_salesman_all_leads').id,
                            self.env.ref('point_of_sale.group_pos_user').id,
                            self.env.ref('base.group_partner_manager').id,
                        ]
                    )
                ],
                'active': True,
            })

    def get_shipping_address_by_query(self):
        child_ids_delete = self._context.get('child_ids_delete', [])
        partner_ids = self._context.get('partner_ids', [])
        ship_type = self._context.get('ship_type', False)

        if len(child_ids_delete) > 0:
            partner_ids = child_ids_delete
            ShipAction = 'Delete'
            query_where_ship_id = 'and vendor_ship_id <> 0 '
            quert_limit = ''
        else:
            ShipAction = 'None'
            quert_limit = 'limit 1'
            query_where_ship_id = ''

        if ship_type:
            query_where_ship_type = 'and type = \'{0}\' '.format(ship_type)
        else:
            query_where_ship_type = ''

        query_result = []

        if len(partner_ids) > 0:
            query_where_partner_ids = '{0}'.format(','.join(map(str, partner_ids)))

            query_string = """
                select ShipID as ShipID,
                    ShipOdooID,
                    ShipAction,
                    coalesce(branch.branch_code, '') as StoreCode,
                    ShipAddr1,
                    coalesce(ShipAddr2, '') as ShipAddr2,
                    coalesce(ShipAddr3, '') as ShipAddr3,
                    coalesce(ShipAddr4, '') as ShipAddr4,
                    coalesce(ShipSoi, '') as ShipSoi,
                    coalesce(ShipStreet, '') as ShipStreet,
                    coalesce(tambon.name, '') as ShipSubDistrict,
                    coalesce(amphur.name, '') as ShipDistrict,
                    coalesce(province.name, '') as ShipProvince,
                    coalesce(ShipZipCode, '') as ShipPostCode,
                    coalesce(ShipContactor, '') as ShipContactor,
                    coalesce(ShipPhoneNo, '') as ShipPhoneNo,
                    coalesce(ContactorName, '') as ContactorName,
                    ContactorPhone,
                    ContactorMobileNo,
                    ContactorEmail,
                    ContactorFax
                from (
                    select coalesce(vendor_ship_id, 0) as ShipID,
                        id as ShipOdooID,
                        (
                            case when coalesce(vendor_ship_id, 0) = 0 then 'Create'
                                when is_update_shipping = true then 'Update'
                                else '{0}'
                            end
                        ) as ShipAction,
                        branch_id,
                        substring(
                            concat(
                                street,
                                ' ',
                                street2,
                                ' ',
                                moo,
                                ' ',
                                alley
                            ),
                            1,
                            50
                        ) as ShipAddr1,
                        substring(
                            concat(
                                street,
                                ' ',
                                street2,
                                ' ',
                                moo,
                                ' ',
                                alley
                            ),
                            51,
                            100
                        ) as ShipAddr2,
                        substring(
                            concat(
                                street,
                                ' ',
                                street2,
                                ' ',
                                moo,
                                ' ',
                                alley
                            ),
                            101,
                            150
                        ) as ShipAddr3,
                        substring(
                            concat(
                                street,
                                ' ',
                                street2,
                                ' ',
                                moo,
                                ' ',
                                alley
                            ),
                            151,
                            200
                        ) as ShipAddr4,
                        alley as ShipSoi,
                        street2 as ShipStreet,
                        tambon_id,
                        amphur_id,
                        province_id,
                        zip as ShipZipCode,
                        '' as ShipRemark,
                        name as ShipContactor,
                        name as ContactorName,
                        coalesce(phone, mobile) as ShipPhoneNo,
                        coalesce(phone, '') as ContactorPhone,
                        coalesce(mobile, '') as ContactorMobileNo,
                        coalesce(email, '') as ContactorEmail,
                        coalesce(fax, '') as ContactorFax
                    from res_partner
                    where id in ({1})
                        {2}
                        {3}
                ) as shipaddr
                left join province as province
                on shipaddr.province_id = province.id
                left join amphur as amphur
                on shipaddr.amphur_id = amphur.id
                left join tambon as tambon
                on shipaddr.tambon_id = tambon.id
                left join pos_branch as branch
                on shipaddr.branch_id = branch.id
                {4}
            """.format(
                ShipAction,
                query_where_partner_ids,
                query_where_ship_id,
                query_where_ship_type,
                quert_limit
            )

            self.env.cr.execute(query_string)
            query_result = self.env.cr.dictfetchall()

        return query_result

    def get_sale_order_line_by_query(self):
        sale_order_id = self._context.get('sale_order_id', 0)

        query_string = """
            select
                sopd.product_id,
                sopd.product_uom_qty,
                sopd.default_code,
                sopd.product_tmpl_id,
                pdtemp.prod_status
            from (
                select
                    soline.product_id,
                    soline.product_uom_qty,
                    pd.default_code,
                    pd.product_tmpl_id
                from (
                    select
                        product_id,
                        sum(product_uom_qty::int) as product_uom_qty
                    from sale_order_line
                    where 
                        order_id = {0}
                        and is_line_discount_delivery_promotion is false
                    group by product_id
                ) as soline
                inner join (
                        select  pd.id,
                                pd.default_code,
                                pd.product_tmpl_id
                        from product_product pd
                        where pd.default_code is not null
                ) as pd on soline.product_id = pd.id
            ) as sopd
            inner join product_template as pdtemp
            on sopd.product_tmpl_id = pdtemp.id
        """.format(
            sale_order_id
        )

        self.env.cr.execute(query_string)
        query_result = self.env.cr.dictfetchall()

        return query_result

    def get_purchase_order_line_by_query(self):
        purchase_order_id = self._context.get('purchase_order_id', 0)
        is_check_qty = self._context.get('is_check_qty', False)

        if is_check_qty:
            purchase_order_select = """
                select 	sum(product_qty) as product_qty,
                        sum(product_qty_available) as product_qty_available,
                        default_code,
                        isfree
                from po_line
                group by default_code, isfree
            """
        else:
            purchase_order_select = """
                select 	fono,
                        prno,
                        poline_id,
                        product_id,
                        product_qty,
                        product_qty_available,
                        default_code,
                        product_tmpl_id,
                        prod_status,
                        isbestdeal,
                        isfree,
                        deliveryfee,
                        discountrate,
                        price_unit,
                        createby,
                        createon,
                        updateby,
                        updateon,
                        transferon
                from po_line
            """

        query_string = """
            with po_line as (
                select
                    '' as fono,
                    popd.prno,
                    popd.poline_id,
                    popd.product_id,
                    popd.product_qty,
                    popd.product_qty_available,
                    popd.default_code,
                    popd.product_tmpl_id,
                    pdtemp.prod_status,
                    (case
                        when popd.type_to_ofm = 'customer' then
                        (case
                            when popd.isbestdeal = true then 'Yes'
                            else 'No'
                        end)
                        else
                        (case
                            when popd.isbestdeal = true then 'True'
                            else 'False'
                        end)
                    end) as isbestdeal,
                    (case
                        when popd.isfree = true then 'Yes'
                        else 'No'
                    end) as isfree,
                    popd.deliveryfee,
                    popd.discountrate,
                    popd.price_unit,
                    popd.createby,
                    popd.createon,
                    popd.updateby,
                    popd.updateon,
                    popd.transferon
                from
                    (
                    select
                        poline.prno,
                        poline.type_to_ofm,
                        poline.poline_id,
                        poline.product_id,
                        poline.product_qty,
                        poline.product_qty_available,
                        pd.default_code,
                        pd.product_tmpl_id,
                        poline.deliveryfee,
                        poline.discountrate,
                        poline.price_unit,
                        poline.isbestdeal,
                        poline.isfree,
                        poline.createby,
                        poline.createon,
                        poline.updateby,
                        poline.updateon,
                        poline.transferon
                    from
                        (
                        select
                            po.name as prno,
                            po.type_to_ofm,
                            poline.id as poline_id,
                            poline.product_id,
                            poline.product_qty,
                            poline.product_qty_available,
                            poline.deliveryfee,
                            poline.discountrate,
                            poline.price_unit,
                            poline.isbestdeal,
                            poline.isfree,
                            poline.createby,
                            poline.createon,
                            poline.updateby,
                            poline.updateon,
                            poline.transferon
                        from
                            (
                            select
                                id,
                                name,
                                type_to_ofm
                            from
                                purchase_order
                            where
                                id = {0} ) as po
                        inner join (
                            select
                                id,
                                order_id,
                                product_id,
                                product_qty::int,
                                coalesce(product_qty_available, 0)::int as product_qty_available,
                                coalesce(delivery_fee_ofm, 0) as deliveryfee,
                                coalesce(discount, 0) as discountrate,
                                coalesce(price_unit, 0) as price_unit,
                                is_best_deal_promotion as isbestdeal,
                                is_free as isfree,
                                create_uid as createby,
                                create_date + interval '7 hours' as createon,
                                write_uid as updateby,
                                write_date + interval '7 hours' as updateon,
                                (current_timestamp + interval '7 hours')::char(23) as transferon
                            from
                                ofm_purchase_order_line
                            where
                                order_id = {1} ) as poline on
                            po.id = poline.order_id ) as poline
                    inner join product_product as pd on
                        poline.product_id = pd.id ) as popd
                inner join product_template as pdtemp on
                    popd.product_tmpl_id = pdtemp.id
            )
            {2}
        """.format(
            purchase_order_id,
            purchase_order_id,
            purchase_order_select
        )

        self.env.cr.execute(query_string)
        query_result = self.env.cr.dictfetchall()

        return query_result

    def get_partner(self, order_id):
        if order_id:
            partner_id = self.env['res.partner']

            if order_id._name == _so_model:
                partner_id = order_id.partner_shipping_id
            elif all([
                order_id._name == _pr_model,
                hasattr(order_id, 'type_to_ofm'),
            ]):
                if any([
                    order_id.type_to_ofm == 'store',
                    order_id.type_to_ofm == 'fulfillment',
                ]):
                    if hasattr(order_id.branch_id, 'partner_id'):
                        partner_id = order_id.branch_id.partner_id
                    else:
                        partner_id = order_id.branch_id.warehouse_id.partner_id
                elif order_id.type_to_ofm == 'customer':
                    partner_id = order_id.sale_order_id.partner_shipping_id

            if partner_id:
                if any([
                    not partner_id.province_id,
                    not partner_id.amphur_id,
                    not partner_id.tambon_id,
                    not partner_id.zip,
                ]):
                    raise except_orm(_('Error!'), _(u"Shipping Address invalid."))
                else:
                    return partner_id
            else:
                raise except_orm(_('Error!'), 'No Shipping Address.')

        else:
            raise except_orm(_('Error!'), 'No Order.')

    def create_log_call_api(self, api_method, api_name, api_url, api_req_header, api_req_data, api_req_response):
        is_log_parameter_input = self.env['ir.config_parameter'].search([('key', '=', 'is_log_parameter_input')]).value

        if is_log_parameter_input == 'True':
            log_str = """
            purchase_order : {0}
            api_method: {1}
            api_url: {2}
            api_req_header: {3}
            api_req_data: {4}
            api_req_response: {5}
            """.format(
                api_name,
                api_method,
                api_url,
                api_req_header,
                api_req_data,
                api_req_response,
            )

            _logger.info(log_str)

    def request_api(self, api_method, api_name, api_req_header, api_req_data):
        is_except_raise = self._context.get('is_except_raise', False)
        api_url = tools.config[api_name]

        if api_method == _api_method_post:
            request_response = requests.post(api_url, json=api_req_data, headers=api_req_header)
        elif api_method == _api_method_get:
            request_response = requests.get(api_url, json=api_req_data, headers=api_req_header)

        self.create_log_call_api(api_method, api_name, api_url, api_req_header, api_req_data, request_response.content)

        if (200 <= request_response.status_code < 300) and request_response.content:
            request_content = json.loads(request_response.content)

            if all([
                not request_content.get('returnCode', False),
                api_name != 'prs_api_url_create_rtv'
            ]):
                raise except_orm(_('Error!'), 'No data return.')
            else:
                is_api_success = False

                if any([
                    api_name == 'prs_api_url_check_qty',
                    api_name == 'sale_api_url_check_qty',
                ]):
                    if 200 <= int(request_content.get('returnCode')) < 300:
                        is_api_success = True
                elif any([
                        api_name == 'prs_api_url_create_so',
                        api_name == 'sale_api_url_create_so',
                ]):
                    if request_content.get('returnCode') == u'Created':
                        is_api_success = True
                elif api_name == 'prs_api_url_create_rtv':
                    is_api_success = True

                if is_api_success:
                    return request_content
                else:
                    return_message = request_content.get('returnMessage', False)

                    if return_message:
                        return_message_exception = return_message.get('exception', False)

                        if return_message_exception:
                            msg_exception = return_message_exception
                        else:
                            msg_exception = 'Don\'t have key exception'
                    else:
                        msg_exception = 'No returnMessage'

                    if request_content.get('returnCode', 0) != '600':
                        msg_exception += '\n\n'
                        msg_exception += json.dumps(request_content, ensure_ascii=False)

                    raise except_orm(_('Error!'), msg_exception)
        else:
            msg_error = str(request_response.status_code)
            msg_error += ': ' + str(request_response.reason)
            msg_error += '\n\n' + str(request_response.content)

            if is_except_raise:
                self.create_log_call_api(api_method, api_name, api_url, api_req_header, api_req_data, msg_error)
            else:
                raise except_orm(_('Error!'), msg_error)

    def call_api_request_token_ofm(self):
        is_except_raise = self._context.get('is_except_raise', False)
        token_req_key = tools.config['prs_api_request_token']
        token_req_url = tools.config['prs_api_url_request_token']
        token_req_header = {
            'Content-Type': 'application/json'
        }

        token_req_data = "\"" + token_req_key + "\""
        token_req_response = requests.post(token_req_url, data=token_req_data, headers=token_req_header)
        self.create_log_call_api(
            _api_method_post,
            'prs_api_request_token',
            token_req_url,
            token_req_header,
            token_req_data,
            token_req_response.content
        )

        if (200 <= token_req_response.status_code < 300) and token_req_response.content:
            api_req_header = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token_req_response.content.replace("\"", "")
            }

            return api_req_header
        else:
            msg_error = str(token_req_response.status_code)
            msg_error += ': ' + str(token_req_response.reason)
            msg_error += '\n' + str(token_req_response.content)

            if is_except_raise:
                self.create_log_call_api(
                    _api_method_post,
                    'prs_api_request_token',
                    token_req_url,
                    token_req_header,
                    token_req_data,
                    msg_error
                )
            else:
                raise except_orm(_('Error!'), msg_error)

    def call_api_shipping(self):
        ship_address = self._context.get('ship_address', {})

        if len(ship_address) > 0:
            api_req_header = self.call_api_request_token_ofm()

            if api_req_header:
                ship_address = {
                    'shipping': ship_address
                }

                self.request_api(_api_method_post, 'sale_api_url_shipping', api_req_header, ship_address)
        else:
            self.create_log_call_api(_api_method_post, 'sale_api_url_shipping', '', '', '', 'No Ship Address')
            
    def prepare_shipping_param(self, api_name, order_id, shipping_address):
        if api_name == _api_check_qty:
            shipping_field = self.get_api_check_qty_shipping_field(order_id._name)
        
        if api_name == _api_create_so:
            shipping_field = self.get_api_create_so_shipping_field(order_id.type_to_ofm)
            
        shipping_param = []

        for shipping_list in shipping_address:
            shipping_val = {}
            for key, val in shipping_list.iteritems():
                if key in shipping_field:
                    shipping_val.update({
                        shipping_field[key]: val,
                    })

            shipping_param.append(shipping_val)

        return shipping_param

    def prepare_product_param(self, api_name, order_id, product_line):
        if api_name == _api_check_qty:
            product_field = self.get_api_check_qty_product_field(order_id._name)
            
        if api_name == _api_create_so:
            product_field = self.get_api_create_so_product_field(order_id.type_to_ofm)
            
        product_param = []

        for product_list in product_line:
            product_val = {}
            for key, val in product_list.iteritems():
                if key in product_field:
                    product_val.update({
                        product_field[key]: val,
                    })

            product_param.append(product_val)

        return product_param

    ## API Check QTY
    def get_api_check_qty_shipping_field(self, model_name):
        shipping_field = {}

        if model_name == _pr_model:
            shipping_field = {
                'shipsubdistrict': 'shipsubdistrict',
                'shipdistrict': 'shipdistrict',
                'shipprovince': 'shipprovince',
                'shippostcode': 'shippostcode',
            }

        if model_name == _so_model:
            shipping_field = {
                'shipsubdistrict': 'SubDistrict',
                'shipdistrict': 'District',
                'shipprovince': 'Province',
                'shippostcode': 'Zipcode',
            }

        return shipping_field

    def get_api_check_qty_product_field(self, model_name):
        product_field = {}

        if model_name == _pr_model:
            product_field = {
                'default_code': 'pid',
                'product_qty': 'orderQty',
                'product_qty_available': 'availableQty',
            }

        if model_name == _so_model:
            product_field = {
                'default_code': 'pid',
                'product_uom_qty': 'orderQty',
            }

        return product_field

    def get_api_check_qty_param(self, order_id):
        check_qty_param = {}
        ctx = dict(self._context)
        shipping_param = []
        product_param = []
        partner_id = self.get_partner(order_id)
        ctx.update({
            'partner_ids': partner_id.ids,
        })

        if order_id._name == _pr_model:
            check_qty_param.update({
                'prodTotamtIncVat': 0,
                'prodlists': [],
            })

            ctx.update({
                'purchase_order_id': order_id.id,
                'is_check_qty': True,
            })

            shipping_address = self.with_context(ctx).get_shipping_address_by_query()
            product_line = self.with_context(ctx).get_purchase_order_line_by_query()

        if order_id._name == _so_model:
            check_qty_param.update({
                'prodlists': [],
            })

            ctx.update({
                'sale_order_id': order_id.id,
            })

            shipping_address = self.with_context(ctx).get_shipping_address_by_query()
            product_line = self.with_context(ctx).get_sale_order_line_by_query()

        if len(shipping_address) > 0:
            shipping_param = self.prepare_shipping_param(_api_check_qty, order_id, shipping_address)

        if len(product_line) > 0:
            product_param = self.prepare_product_param(_api_check_qty, order_id, product_line)

        if all([
            len(shipping_param) > 0,
            len(product_param) > 0,
        ]):
            check_qty_param.update(shipping_param[0])
            check_qty_param['prodlists'] = product_param
        else:
            if len(shipping_param) < 1:
                raise except_orm(_('Error!'), 'No Shipping Address')

            if len(product_param) < 1:
                raise except_orm(_('Error!'), 'No Product')

        return check_qty_param

    def call_api_check_qty_from_ofm(self, order_id):
        if order_id and order_id._name == _pr_model:
            order_line_ids = order_id.ofm_purchase_order_line_ids
            api_url = 'prs_api_url_check_qty'
            api_method = _api_method_post
            sql_table_update = 'ofm_purchase_order_line'
            sql_product_qty = 'product_qty'
        elif order_id and order_id._name == _so_model:
            order_line_ids = order_id.order_line
            api_url = 'sale_api_url_check_qty'
            api_method = _api_method_get
            sql_table_update = 'sale_order_line'
            sql_product_qty = 'product_uom_qty'
        else:
            raise except_orm(_('Error!'), 'No Purchase Order / Sale Order.')

        if not order_line_ids:
            raise except_orm(_('Error!'), 'Please, Add Product.')

        api_req_header = self.call_api_request_token_ofm()
        if api_req_header:
            check_qty_param = self.get_api_check_qty_param(order_id)
            check_qty_response = self.request_api(api_method, api_url, api_req_header, check_qty_param)

            is_delivery_fee_by_item = check_qty_response.get('isDeliveryFeeByItem', False)

            if is_delivery_fee_by_item == 'No':
                is_delivery_fee_by_item = False
            else:
                is_delivery_fee_by_item = True
                
            productLists = check_qty_response.get('productLists', [])

            if len(productLists) > 0:
                if order_id._name == _so_model:
                    order_id.update({
                        'is_delivery_fee_by_item': is_delivery_fee_by_item
                    })

                query_str_update = ""

                for qty in productLists:
                    pid = qty.get('pid', False)
                    product_ids = self.env['product.product'].search([
                        ('default_code', '=', pid)
                    ])

                    if not product_ids:
                        raise except_orm(_('Error!'), "{0} : No Data in Odoo".format(pid))

                    for product_id in product_ids:
                        availableQty = qty.get('availableQty', 0)
                        productStatus = qty.get('productStatus', '')

                        update_line = """
                            update {0}
                            set product_qty_available = {1},
                                product_status_correct = (case when product_status_odoo = '{2}' then true else false end),
                                product_status_ofm = '{3}',
                                is_danger= (case 
                                    when {4} > {5} and product_status_odoo <> 'NonStock' then true
                                    when product_status_odoo <> '{6}' then true 
                                    else false 
                                end)
                            where order_id = {7}
                                and product_id = {8};
                        """.format(
                            sql_table_update,
                            availableQty,
                            productStatus,
                            productStatus,
                            sql_product_qty,
                            availableQty,
                            productStatus,
                            order_id.id,
                            product_id.id
                        )

                        query_str_update = "".join([
                            query_str_update,
                            update_line
                        ])

                self.env.cr.execute(query_str_update)
                self.env.clear()
            else:
                raise except_orm(_('Error!'), "No Product")

    ## API Create SO
    def prepare_api_create_so_pr(self, type_to_ofm, po_id):
        tr_convert = self.env['tr.convert']
        po_id._amount_all_ofm()
        prno = po_id.name
        i_vat_last_product = 0.0

        if not po_id:
            raise except_orm(_('Error!'), 'No Purchase Request.')

        for line in po_id.ofm_purchase_order_line_ids:
            if line.taxes_id:
                i_vat_last_product = line.taxes_id.amount
                break

        totamt = po_id.amount_untaxed_ofm
        discamt = 0
        netamt = po_id.amount_untaxed_ofm
        vatamt = po_id.amount_tax_ofm
        sumamt = po_id.amount_total_ofm
        franchiseCustShippingID = po_id.branch_id.id
        franchiseCustID = po_id.branch_id.id
        documentStatus = po_id.state
        prodTotamtIncVat = po_id.amount_total_ofm
        createby = po_id.create_uid.id
        createon = str(tr_convert.convert_datetime_to_bangkok(po_id.create_date))
        updateby = po_id.write_uid.id
        updateon = str(tr_convert.convert_datetime_to_bangkok(po_id.write_date))
        transferon = str(tr_convert.convert_datetime_to_bangkok(datetime.now(timezone('UTC'))))
        deliverydate = str(tr_convert.convert_datetime_to_bangkok(po_id.date_planned))
        prdate = str(tr_convert.convert_datetime_to_bangkok(po_id.date_order))
        storecode = po_id.branch_id.branch_code

        if any([
            type_to_ofm == 'store',
            type_to_ofm == 'fulfillment',
        ]):
            pr_data = {
                'prno': prno,
                'prchannel': 'manual' if type_to_ofm == 'store' else 'suggest',
                'storecode': storecode,
                'documentno': prno,
                'deliverydate': deliverydate,
                'deliveryfeebyitem': 0,
                'deliveryfeebyorder': 0,
                'discountrate': 0,
                'vatrate': i_vat_last_product,
                'totamt': totamt,
                'discamt': discamt,
                'netamt': netamt,
                'vatamt': vatamt,
                'sumamt': sumamt,
                'createby': createby,
                'createon': createon,
                'updateby': updateby,
                'updateon': updateon,
                'transferon': transferon,
                'franchiseCustShippingID': franchiseCustShippingID,
                'franchiseCustID': franchiseCustID,
                'documentStatus': documentStatus,
                'prodTotamtIncVat': prodTotamtIncVat,
                'shippingremark': po_id.comment_po if po_id.comment_po else '',
            }
        else:
            pr_data = {
                'prno': prno,
                'prdate': prdate,
                'prchannel': 'customer',
                'storecode': storecode,
                'deliverydate': deliverydate,
                'deliveryfeebyitem': po_id.amount_delivery_fee_special,
                'deliveryfeebyorder': po_id.amount_delivery_fee_by_order,
                'discountrate': 0,
                'vatrate': i_vat_last_product,
                'totamt': totamt,
                'discamt': discamt,
                'netamt': netamt,
                'vatamt': vatamt,
                'sumamt': sumamt,
                'shippingremark': po_id.sale_order_id.note if po_id.sale_order_id.note else '',
            }

        return pr_data

    def get_api_create_so_shipping_field(self, type_to_ofm):
        if any([
            type_to_ofm == 'store',
            type_to_ofm == 'fulfillment',
        ]):
            shipping_field = {
                'shipcontactor': 'shipcontactor',
                'shipaddr1': 'shipaddr1',
                'shipaddr2': 'shipaddr2',
                'shipaddr3': 'shipaddr3',
                'shipaddr4': 'shipaddr4',
                'shipsubdistrict': 'shipsubdistrict',
                'shipdistrict': 'shipdistrict',
                'shipprovince': 'shipprovince',
                'shippostcode': 'shippostcode',
                'shipphoneno': 'shipphoneno',
                'contactorname': 'contactorname',
                'contactorphone': 'contactorphone',
                'contactorfax': 'contactorfax',
                'contactoremail': 'contactoremail',
                'contactormobileno': 'contactormobileno',
                'items': '',
            }
        else:
            shipping_field = {
                'shipid': 'shipid',
                'shipodooid': 'shipOdooID',
                'shipaction': 'ShipAction',
                'shipcontactor': 'shipcontactor',
                'shipphoneno': 'shipphoneno',
                'shipaddr1': 'shipaddr1',
                'shipaddr2': 'shipaddr2',
                'shipaddr3': 'shipaddr3',
                'shipaddr4': 'shipaddr4',
                'shipsubdistrict': 'shipsubdistrict',
                'shipdistrict': 'shipdistrict',
                'shipprovince': 'shipprovince',
                'shippostcode': 'shippostcode',
                'contactorname': 'contactorname',
                'contactorphone': 'contactorphone',
                'contactorfax': 'contactorfax',
                'contactoremail': 'contactoremail',
                'contactormobileno': 'contactormobileno',
                'items': '',
            }

        return shipping_field

    def get_api_create_so_product_field(self, type_to_ofm):
        if any([
            type_to_ofm == 'store',
            type_to_ofm == 'fulfillment',
        ]):
            product_field = {
                'fono': 'fono',
                'prno': 'prno',
                'default_code': 'pid',
                'product_qty': 'qty',
                'price_unit': 'unitprice',
                'deliveryfee': 'deliveryfee',
                'discountrate': 'discountrate',
                'createby': 'createby',
                'createon': 'createon',
                'updateby': 'updateby',
                'updateon': 'updateon',
                'transferon': 'transferon',
                'isbestdeal': 'isbestdeal',
                'isfree': 'isFree',
            }
        else:
            product_field = {
                'default_code': 'pid',
                'product_qty': 'qty',
                'price_unit': 'unitprice',
                'deliveryfee': 'deliveryfee',
                'discountrate': 'discountrate',
                'isbestdeal': 'isbestdeal',
                'isfree': 'isFree',
            }

        return product_field

    def get_api_create_so_po_param(self, type_to_ofm, po_id):
        partner_id = self.get_partner(po_id)

        ctx = dict(self._context)
        ctx.update({
            'purchase_order_id': po_id.id,
            'partner_ids': partner_id.ids
        })
        shipping_address = self.with_context(ctx).get_shipping_address_by_query()
        product_line = self.with_context(ctx).get_purchase_order_line_by_query()

        shipping_param = self.prepare_shipping_param(_api_create_so, po_id, shipping_address)
        product_param = self.prepare_product_param(_api_create_so, po_id, product_line)

        if all([
            len(shipping_param) > 0,
            len(product_param) > 0,
        ]):
            po_param = self.prepare_api_create_so_pr(type_to_ofm, po_id)
            po_param.update(shipping_param[0])
            po_param['items'] = product_param

            return po_param
        else:
            raise except_orm(_('Error!'), 'No shipping address or purduct.')

    def call_api_create_so_ofm(self, po_header_id):
        api_req_header = self.call_api_request_token_ofm()

        if api_req_header:
            is_new_pr_header = self._context.get('is_new_pr_header', False)

            if is_new_pr_header:
                purchase_order_ids = po_header_id.ofm_purchase_order_ids.filtered(
                    lambda po_rec: not po_rec.is_sent_ofm
                )
            else:
                order_id = self._context.get('order_id', False)
                purchase_order_ids = order_id if order_id else False

            if not purchase_order_ids:
                raise except_orm(_('Error!'), 'No Purchase Request.')

            for po_id in purchase_order_ids:
                if po_id.state == u'draft':
                    type_to_ofm = po_id.type_to_ofm

                    if type_to_ofm == 'customer':
                        api_name = 'sale_api_url_create_so'
                    else:
                        api_name = 'prs_api_url_create_so'

                    po_param = self.get_api_create_so_po_param(type_to_ofm, po_id)

                    #CHRIS: fixing request for field contactorname
                    if po_id.sale_order_id:
                        so = po_id.sale_order_id
                        is_from_confirm_payment = 'from_action_confirm_payment' in self._context.keys()
                        partner_is_company = so.partner_id.is_company
                        main_contact = so.partner_id.main_contact_person
                        shipping_partner_is_delivery = so.partner_shipping_id.type == 'delivery'
                        is_sale = api_name == 'sale_api_url_create_so'

                        requirements = [
                            is_from_confirm_payment,
                            partner_is_company,
                            is_sale,
                        ]
                        if main_contact:
                            if all(requirements):
                                po_param.update({
                                    'contactorname' : main_contact
                                })
                                if so.partner_id == so.partner_shipping_id:
                                    po_param.update({
                                        'shipcontactor' : main_contact
                                    })
                        else:
                            raise except_orm(_('No Main Contact!'), _('No main contact person has been set for the following partner: %s' % so.partner_id.name))

                    if len(po_param) > 0:
                        self.request_api(_api_method_post, api_name, api_req_header, po_param)
                        po_id.button_sent()
                        self.env.cr.commit()

            po_header_id.get_purchase_request_header_no()
            po_header_id.action_update_send()

    ## API Create RTV
    def prepare_order_line(self, picking_id, rt_order_line, purchase_order):
        tr_convert = self.env['tr.convert']
        invoice_line = []
        po_order_line = {}
        for po_line in purchase_order.order_line:
            po_order_line.update({
                po_line.product_id.id: po_line.price_unit
            })

        for line in rt_order_line:
            line_createon = str(tr_convert.convert_datetime_to_bangkok(line.create_date))
            line_updateon = str(tr_convert.convert_datetime_to_bangkok(line.write_date))
            line_transferon = str(tr_convert.convert_datetime_to_bangkok(datetime.now(timezone('UTC'))))

            if picking_id.rtv_type == 'cn':
                qty = int(line.quantity)
                unitprice = line.price_unit
            elif picking_id.rtv_type == 'change':
                qty = int(line.qty_done)
                unitprice = po_order_line.get(line.product_id.id)

            invoice_line.append({
                'rtno': picking_id.name,
                'pid': line.product_id.default_code,
                'qty': qty,
                'unitprice': unitprice,
                'totalsExVat': 0,
                'totalsIncVat': 0
                # 'createby': line.create_uid.id,
                # 'createon': line_createon,
                # 'updateby': line.write_uid.id,
                # 'updateon': line_updateon,
                # 'transferon': line_transferon,
            })

        return invoice_line

    def prepare_order(self, picking_id, cn_id, rt_order_line, purchase_order):
        tr_convert = self.env['tr.convert']
        create_date = cn_id.create_date if cn_id else picking_id.create_date
        write_date = cn_id.write_date if cn_id else picking_id.write_date

        createon = str(tr_convert.convert_datetime_to_bangkok(create_date))
        updateon = str(tr_convert.convert_datetime_to_bangkok(write_date))
        transferon = str(tr_convert.convert_datetime_to_bangkok(datetime.now(timezone('UTC'))))

        create_rtv_parameter = {
            'rtno': picking_id.name,
            'storecode': picking_id.branch_id.branch_code,
            'invNo': purchase_order.vendor_invoice_no,
            'rtdate': str(tr_convert.convert_datetime_to_bangkok(picking_id.min_date)),
            'rdno': picking_id.origin,
            'rtvType': picking_id.rtv_type,
            # 'createby': purchase_order_id.create_uid.id,
            # 'createon': createon,
            # 'updateby': purchase_order_id.write_uid.id,
            # 'updateon': updateon,
            # 'transferon': transferon,
            'items': rt_order_line
        }

        return create_rtv_parameter

    def call_api_create_rtv(self, picking_id, cn_id):
        purchase_order = self.env['purchase.order'].search([
            ('name', '=', picking_id.group_id.name)
        ])

        api_req_header = self.call_api_request_token_ofm()

        if api_req_header:
            create_rtv_parameter = {}

            if picking_id.rtv_type == 'cn':
                if cn_id and cn_id.state == u'draft':
                    rt_order_line = self.prepare_order_line(picking_id, cn_id.invoice_line_ids, purchase_order)
                    create_rtv_parameter = self.prepare_order(picking_id, cn_id, rt_order_line, purchase_order)
            elif picking_id.rtv_type == 'change':
                rt_order_line = self.prepare_order_line(picking_id, picking_id.pack_operation_product_ids, purchase_order)
                create_rtv_parameter = self.prepare_order(picking_id, cn_id, rt_order_line, purchase_order)

            self.request_api(_api_method_post, 'prs_api_url_create_rtv', api_req_header, create_rtv_parameter)

