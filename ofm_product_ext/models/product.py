# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = "product.category"
    _order = "cat_id, sub_cat_id, id"

    sequence = fields.Integer(
        help="Gives the sequence order when displaying a list of product categories.",
        default=0,
    )

    cat_id = fields.Char(
        'Cat ID OFM',
        required=True,
        translate=True
    )

    sub_cat_id = fields.Char(
        'SubCat ID OFM',
        required=True,
        translate=True
    )

    updateon = fields.Datetime(
        'UpDateOn'
    )

    transferdate = fields.Datetime(
        'TransferDate'
    )

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            list_name = []
            if record.cat_id:
                list_name.append(record.cat_id)
            if record.sub_cat_id:
                list_name.append(record.sub_cat_id)
            list_name.append(record.name)

            result.append((record.id, ', '.join(list_name)))
        return result

    def update_product_category_master_from_staging(self):
        ofm_sync_data = self.env['ofm.sync.data']
        odoo_startdate = ofm_sync_data.get_date_interface()

        conn = ofm_sync_data.open_connection()

        cur = ofm_sync_data.connect_to_db_staging_ofm(conn)

        query_str = "SELECT cat_id, cat_name from tbfranchisecategory group by cat_id, cat_name"

        rows = ofm_sync_data.query_data_from_db_staging_ofm(cur, query_str)

        cat_datas = {}

        sub_cat_datas = {}

        for row in rows:
            key = row[0]
            if cat_datas.get(key, False):
                cat_datas[key].append({
                    'cat_id': row[0],
                    'cat_name': row[1],
                })
            else:
                cat_datas[key] = [{
                    'cat_id': row[0],
                    'cat_name': row[1],
                }]

        query_str = """
            SELECT sub_catid, sub_catname, updateon, cat_id, cat_name, transferdate
            from tbfranchisecategory 
        """

        rows = ofm_sync_data.query_data_from_db_staging_ofm(cur, query_str)
        amount_category = 0

        for row in rows:
            key = row[0]
            if sub_cat_datas.get(key, False):
                sub_cat_datas[key].append({
                    'sub_catid': row[0],
                    'sub_catname': row[1],
                    'updateon': row[2],
                    'cat_id': row[3],
                    'cat_name': row[4],
                    'transferdate': row[5],
                })
            else:
                sub_cat_datas[key] = [{
                    'sub_catid': row[0],
                    'sub_catname': row[1],
                    'updateon': row[2],
                    'cat_id': row[3],
                    'cat_name': row[4],
                    'transferdate': row[5],
                }]

        for cat_data in cat_datas:
            for template_line in cat_datas[cat_data]:
                if template_line.get('transferdate', False):
                    template_line['transferdate'] = template_line['transferdate'].split('.')[0]

                product_category_id = self.env['product.category'].search([
                    ('cat_id', '=', cat_data),
                    ('sub_cat_id', '=', str(999))
                ], limit=1)
                if product_category_id:
                    product_category_id.write({
                        'name': template_line['cat_name'],
                    })
                else:
                    product_category_all = self.env.ref('product.product_category_all')
                    self.env['product.category'].create({
                        'cat_id': template_line['cat_id'],
                        'sub_cat_id': '999',
                        'name': template_line['cat_name'],
                        'parent_id': product_category_all.id,
                        'property_cost_method': 'average',
                        'property_valuation': 'real_time',
                    })

                self.env.cr.commit()

        for sub_cat_data in sub_cat_datas:
            for template_line in sub_cat_datas[sub_cat_data]:
                if template_line.get('transferdate', False):
                    template_line['transferdate'] = template_line['transferdate'].split('.')[0]

                product_category_id = self.env['product.category'].search([
                    ('sub_cat_id', '=', str(template_line['sub_catid'])),
                    ('cat_id', '=', str(template_line['cat_id'])),
                ], limit=1)

                product_category_parent_id = self.env['product.category'].search([
                    ('cat_id', '=', str(template_line['cat_id'])),
                    ('sub_cat_id', '=', str(999)),
                ], limit=1)

                if product_category_id:
                    if product_category_id.transferdate != template_line['transferdate']:
                        _logger.info(
                            ''.join([
                                'product.category sync category_id: ',
                                template_line['cat_id'], '-',
                                ', '.join([
                                    ': '.join([
                                        str(item[0]), str(item[1])
                                    ]) for item in template_line.items()
                                ])
                            ])
                        )
                        product_category_id.write({
                            'name': template_line['sub_catname'],
                            'parent_id': product_category_parent_id.id,
                            'property_cost_method': 'average',
                            'property_valuation': 'real_time',
                            'updateon': template_line['updateon'],
                            'transferdate': template_line['transferdate'],
                        })
                        amount_category += 1
                else:
                    _logger.info(
                        ''.join([
                            'product.category sync category_id: ',
                            template_line['cat_id'], '-',
                            ', '.join([
                                ': '.join([
                                    str(item[0]), str(item[1])
                                ]) for item in template_line.items()
                            ])
                        ])
                    )

                    self.env['product.category'].create({
                        'cat_id': template_line['cat_id'],
                        'sub_cat_id': template_line['sub_catid'],
                        'name': template_line['sub_catname'],
                        'parent_id': product_category_parent_id.id,
                        'property_cost_method': 'average',
                        'property_valuation': 'real_time',
                        'updateon': template_line['updateon'],
                        'transferdate': template_line['transferdate'],
                    })
                    amount_category += 1

                self.env.cr.commit()

        ofm_sync_data.update_interface_control_db_staging_ofm(
            'tbfranchisecategory',
            amount_category,
            odoo_startdate
        )

        ofm_sync_data.close_connection(conn)