# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import time
import json
from ast import literal_eval
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"


    def get_product_product_fields_from_js(self):
        return []


    def get_product_template_fields_from_js(self):
        return ['prod_status']

    @api.model
    def inquiry_product_detail(self, data):
        product_ids = data.get('product_ids', False)
        branch_id = data.get('branch_id', False)
        if not all([
            product_ids,
            len(product_ids),
            branch_id,
        ]):
            return False

        products = self.read_price_by_product_ids(
            product_ids=product_ids,
            branch_id=branch_id,
            pp_col=self.get_product_product_fields_from_js(),
            pt_col=self.get_product_template_fields_from_js()
        )

        taxes_by_id = self.read_customer_tax_ids_by_product_ids(product_ids)

        next_interval = False
        for product in products:
            taxes_id = taxes_by_id.get(product['id'], False)
            if taxes_id and len(taxes_id):
                product['taxes_id'] = taxes_id
            if product['next_interval'] and not next_interval:
                next_interval = product['next_interval']

        pricelist_next_interval = self.find_next_interval_of_price_list(branch_id)

        if not next_interval:
            if pricelist_next_interval:
                next_interval = pricelist_next_interval
        elif next_interval and pricelist_next_interval:
            if datetime.strptime(pricelist_next_interval, DATETIME_FORMAT) < datetime.strptime(next_interval, DATETIME_FORMAT):
                next_interval = pricelist_next_interval

        if len(products) > 0:
            return {
                'products': products,
                'next_interval': next_interval,
            }
        else:
            return False

    def find_next_interval_of_price_list(self, branch_id):
        if not branch_id:
            return False
        query_str = """
            WITH temp_pricelists (
                pricelists_id,
                is_except_branch,
                pricelists_sequence,
                next_interval
            ) AS
            (
                select id as pricelists_id,
                is_except_branch as is_except_branch,
                sequence as pricelists_sequence,
                case when Now() < start_date
                    then start_date
                    when Now() < end_date
                    then end_date
                end as next_interval
                from pricelists
                where active is true
            ),
            
            temp_pricelists_branch_rel (
                pricelists_id,
                pos_branch_id
            ) AS
            (
                select pbpr.pricelists_id as pricelists_id,
                pbpr.pos_branch_id as pos_branch_id
                from pos_branch_pricelists_rel pbpr
                inner join temp_pricelists tpl on pbpr.pricelists_id = tpl.pricelists_id
            )
            
            select
                min(query.next_interval) as next_interval
            from (
                select tpl.pricelists_id,
                    tpl.pricelists_sequence,
                    tpl.next_interval
                from temp_pricelists tpl
                left join temp_pricelists_branch_rel bpr on tpl.pricelists_id = bpr.pricelists_id
                where tpl.next_interval is not null and (
                    case when bpr.pos_branch_id is not null
                        -- parameter --
                        then pos_branch_id = {branch_id}
                        else bpr.pricelists_id is null 
                    end
                )
                and is_except_branch is false 
                
                union all 
                
                select tpl.pricelists_id,
                    tpl.pricelists_sequence,
                    tpl.next_interval
                from temp_pricelists tpl
                left join (
                        select *
                        from temp_pricelists_branch_rel
                        -- parameter --
                        where pos_branch_id = {branch_id}
                    ) bpr on tpl.pricelists_id = bpr.pricelists_id
                where tpl.next_interval is not null and (
                    case when bpr.pricelists_id is not null 
                        then false
                        else true
                    end
                )
                and is_except_branch is true
            ) query
        """.format(
            branch_id=branch_id
        )
        # print query_str
        self._cr.execute(query_str)
        next_interval = self._cr.dictfetchall()
        if next_interval and len(next_interval):
            return next_interval[0]['next_interval']
        else:
            return False
