# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta
from pytz import timezone
from odoo import api, fields, models, _
from odoo.tools import float_round, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    default_code = fields.Char(
        string='Internal Reference (PID)',
    )

    sku_ofm = fields.Char (
        'sku',
        translate=True,
    )
    name_eng_ofm = fields.Char(
        'Name Eng',
        translate=True,
    )
    dept_ofm = fields.Many2one(
        comodel_name='ofm.product.dept',
        string='Sub Dept OFM',
        translate=True,
        domain="[('dept_parent_id', '!=', False)]"
    )
    parent_dept_ofm = fields.Many2one(
        comodel_name='ofm.product.dept',
        string='Dept OFM',
        translate=True,
        domain="[('dept_parent_id', '=', False)]"
    )
    brand_id = fields.Many2one(
        'product.brand',
        string='Brand',
        required=True,
    )
    cp_cid_ofm = fields.Char(
        'CPC ID',
        translate=True
    )
    own_brand_ofm = fields.Char(
        'OwnBrand',
        translate=True
    )
    prod_status = fields.Char(
        'ProdStatus',
        translate=True
    )
    prod_remark_ofm = fields.Char(
        'ProdRemark',
        translate=True
    )
    is_delivery_fee_ofm = fields.Boolean(
        string='IsDeliveryFee',
        translate=True,
    )
    delivery_fee_ofm = fields.Float(
        string='DeliveryFee',
        translate=True,
    )

    is_best_deal_promotion = fields.Boolean(
        string="Best Deal Promotion",
    )

    is_promotion = fields.Boolean(
        string="Promotion",
        readonly=True,
    )

    updateon = fields.Datetime(
        'UpDateOn'
    )

    transferdate = fields.Datetime(
        'TransferDate'
    )

    date_promotion_start = fields.Datetime(
        string='Promotion Start Date'
    )

    date_promotion_end = fields.Datetime(
        string='Promotion End Date'
    )

    price_normal = fields.Float(
        string='Retail Price',
        digits=dp.get_precision('Normal Product Price'),
    )

    price_promotion = fields.Float(
        string='Promotion Price',
        digits=dp.get_precision('Normal Product Price'),
    )

    product_price_log_ids = fields.One2many(
        comodel_name='product.price.log',
        inverse_name='product_template_id',
        string='Promotion Log',
        readonly=True,
    )

    incoming_qty_pr_sent = fields.Float(
        string='Incoming PR Sent',
        compute='_compute_quantities',
        search='_search_incoming_qty',
        digits=dp.get_precision('Product Unit of Measure')
    )

    product_cost = fields.Float(
        string='Product Cost',
        default=0,
    )

    def get_vat_product_all_company(self):
        vat_product = self.env['ir.config_parameter'].search([
            ('key', '=', 'vat_product')
        ]).value
        account_tax = self.env['account.tax']
        vat_in = account_tax.search([
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', vat_product)
        ]).ids
        vat_out = account_tax.search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', vat_product)
        ]).ids

        return {
            'vat_in': vat_in,
            'vat_out': vat_out
        }

    def map_query_dict_product_template(self, row):
        temp = {
            'name': row[0],
            'active': row[1],
            'type': row[2],
            'sale_ok': row[3],
            'purchase_ok': row[4],
            'invoice_policy': row[5],
            'default_code': row[6],
            'barcode': row[7],
            'uom_id': row[8],
            'uom_po_id': row[9],
            'available_in_pos': row[10],
            'warranty': row[11],
            'sale_delay': row[12],
            'sku_ofm': row[13],
            'nameeng': row[14],
            'cat_id': row[15],
            'cat_name': row[16],
            'sub_catid': row[17],
            'sub_catname': row[18],
            'dept': row[19],
            'dept_name': row[20],
            'sub_dpt': row[21],
            'sub_dptname': row[22],
            'class': row[23],
            'sub_class': row[24],
            'brandid': row[25],
            'brandth': row[26],
            'brandeng': row[27],
            'cpcid': row[28],
            'ownbrand': row[29],
            'prodremark': row[30],
            'prodstatus': row[31],
            'isvat': row[32],
            'isdeliveryfee': row[33],
            'deliveryfee': row[34],
            'isbestdeal': row[35],
            'salepriceexvat': row[36],
            'salepriceincvat': row[37],
            'ispromotion': row[38],
            'promotionpriceexvat': row[39],
            'promotionpriceincvat': row[40],
            'promotionstartdate': row[41],
            'promotionenddate': row[42],
            'createby': row[43],
            'createon': row[44],
            'updateby': row[45],
            'updateon': row[46],
            'transferdate': row[47]
        }
        return temp

    def check_tpye_feild_true_false(self, data):
        status = True
        if data:
            if isinstance(data, bool):
                if data is False:
                    status = False
            elif isinstance(data, (str, unicode)):
                if str(data).lower() == 'false':
                    status = False
        return status

    def map_dict_for_create_product_template(self, template_line):

        product_brand_id = self.env['product.brand'].search([
            ('ofm_brand_id', '=', template_line['brandid']),
        ], limit=1)

        product_cat_id = self.env['product.category'].search([
            ('cat_id', '=', template_line['cat_id']),
            ('sub_cat_id', '=', template_line['sub_catid']),
        ], limit=1)

        product_dept_id = self.env['ofm.product.dept'].search([
            ('ofm_dept_id', '=', template_line['dept']),
            ('ofm_sub_dept_id', '=', template_line['sub_dpt']),
            ('ofm_class_id', '=', template_line['class']),
            ('ofm_sub_class_id', '=', template_line['sub_class']),
        ], limit=1)

        if template_line['ispromotion'].upper() == 'YES':
            promotion_date_start = template_line['promotionstartdate'][:10]
            promotion_date_start = datetime.strptime(promotion_date_start, '%Y-%m-%d').date()
            promotion_date_end = template_line['promotionenddate'][:10]
            promotion_date_end = datetime.strptime(promotion_date_end, '%Y-%m-%d').date()
            date_now = datetime.now(timezone('UTC'))
            tr_convert = self.env['tr.convert']
            date_now = tr_convert.convert_datetime_to_bangkok(date_now).date()

            if promotion_date_start <= date_now <= promotion_date_end:
                price = template_line['promotionpriceincvat']
                ispromotion = True
            else:
                price = template_line['salepriceincvat']
                ispromotion = False
        else:
            price = template_line['salepriceincvat']
            ispromotion = False

        if template_line['isdeliveryfee'].upper() == 'YES':
            isdeliveryfee = True
        else:
            isdeliveryfee = False

        if template_line['isbestdeal'].upper() == 'YES':
            isbestdeal = True
        else:
            isbestdeal = False

        if template_line['isvat'].upper() == 'YES':
            taxes_id = [[6, 0, template_line['vat_out']]]
            supplier_taxes_id = [[6, 0, template_line['vat_in']]]
        else:
            taxes_id = [[6, 0, []]]
            supplier_taxes_id = [[6, 0, []]]

        date_start_promotion_db = datetime.strptime(
            template_line['promotionstartdate'][:19], '%Y-%m-%d %H:%M:%S'
        ) - timedelta(hours=7)

        # date_start_promotion_db = date_start_promotion_db.strftime(
        #     '%Y-%m-%d %H:%M:%S')
        date_start_promotion_db = date_start_promotion_db.isoformat().strip().split("T")
        date_start_promotion_db = "%s %s" % \
                                  (
                                      date_start_promotion_db[0],
                                      date_start_promotion_db[1].strip().split(".")[0]
                                  )

        date_end_promotion_db = datetime.strptime(
            template_line['promotionenddate'][:19], '%Y-%m-%d %H:%M:%S'
        ) - timedelta(hours=7)
        # date_end_promotion_db = date_end_promotion_db.strftime(
        #     '%Y-%m-%d %H:%M:%S')
        date_end_promotion_db = date_end_promotion_db.isoformat().strip().split("T")
        date_end_promotion_db = "%s %s" % \
                                (
                                    date_end_promotion_db[0],
                                    date_end_promotion_db[1].strip().split(".")[0]
                                )

        template_active = self.check_tpye_feild_true_false(template_line['active'])
        sale_ok = self.check_tpye_feild_true_false(template_line['sale_ok'])
        purchase_ok = self.check_tpye_feild_true_false(template_line['purchase_ok'])

        #Check Product on Qty
        if not template_active:
            query_str = """
                        select s_prp.id, 
                                s_prp.default_code, 
                                avp.remain_product_qty
                                --sum(avp.remain_product_qty) as remain_product_qty
                        from (
                            select id, default_code, active
                            from product_product 
                            where active is true
                            and default_code = '{0}'
                        )s_prp
                        inner join (
                            select distinct on (product_id, branch_id)
                                product_id,
                                branch_id,
                                remain_product_qty
                            from average_price
                            order by product_id,branch_id,
                                  id desc
                        ) avp on s_prp.id = avp.product_id 
                                 and avp.remain_product_qty > 0
                    """.format(
                        str(template_line['default_code'])
                    )

            self.env.cr.execute(query_str)
            results = self.env.cr.dictfetchall()

            if results:
                template_active = True
                template_line['transferdate'] = self._context.get(
                    'date_transferdate', template_line['transferdate']
                )
                str_log = ''.join([
                    'update uo product default code',
                    template_line['default_code'],
                    ' Status Product ON Hand Not Active_False : '
                ])
                _logger.info(str_log)

        temp = {
            'name': template_line['name'],
            'categ_id': product_cat_id.id,
            'active': template_active,
            'sale_ok': sale_ok,
            'purchase_ok': purchase_ok,
            'barcode': template_line['barcode'],
            'sku_ofm': template_line['sku_ofm'],
            'list_price': price,
            'lst_price': price,
            'dept_ofm': product_dept_id.id,
            'brand_id': product_brand_id.id,
            'available_in_pos': template_line['available_in_pos'],
            'cp_cid_ofm': template_line['cpcid'],
            'own_brand_ofm': template_line['ownbrand'],
            'prod_status': template_line['prodstatus'],
            'prod_remark_ofm': template_line['prodremark'],
            'is_delivery_fee_ofm': isdeliveryfee,
            'delivery_fee_ofm': template_line['deliveryfee'],
            'is_best_deal_promotion': isbestdeal,
            'is_promotion': ispromotion,
            'type': template_line['type'],
            'updateon': template_line['updateon'],
            'transferdate': template_line['transferdate'],
            'date_promotion_start': date_start_promotion_db,
            'date_promotion_end': date_end_promotion_db,
            'price_normal': template_line['salepriceincvat'],
            'price_promotion': template_line['promotionpriceincvat'],
            'taxes_id': taxes_id,
            'supplier_taxes_id': supplier_taxes_id
        }
        return temp

    def map_dict_for_create_product_price_log(self, vals):

        if vals.get('price_normal', False):
            price_normal = vals.get('price_normal', False)
        else:
            price_normal = vals.get('list_price', False)

        product_price_log_ids = {
            'product_price_log_ids': [
                (
                    0,
                    0,
                    {
                        'price_normal': price_normal,
                        'price_promotion': vals.get('price_promotion', False),
                        'date_promotion_start': vals.get('date_promotion_start', False),
                        'date_promotion_end': vals.get('date_promotion_end', False),
                    }
                )
            ]
        }

        vals.update(product_price_log_ids)

        return vals

    def update_product_master_from_staging(self, default_code_param=False):

        query_str = """
            select 
                id,
                default_code,
                transferdate
            from
                product_template pp
        """

        self.env.cr.execute(query_str)
        query_results = self.env.cr.dictfetchall()

        default_code_list = []
        default_code_values = {}

        for item in query_results:
            product_item = default_code_values.get(item['default_code'], False)
            if not product_item:
                default_code_values.update({
                    item['default_code']: {
                        'id': item['id'],
                        'transferdate': item['transferdate'] and item['transferdate'].split('.')[0] or False
                    }
                })
                default_code_list.append(item['default_code'])

        ofm_sync_data = self.env['ofm.sync.data']
        odoo_startdate = ofm_sync_data.get_date_interface()
        conn = ofm_sync_data.open_connection()

        cur = ofm_sync_data.connect_to_db_staging_ofm(conn)

        query_str = "SELECT *,ascii(name) from tbfranchiseproductmaster"

        if default_code_param:
            query_str += """
                        where default_code = '%s'
                    """ % default_code_param

        rows = ofm_sync_data.query_data_from_db_staging_ofm(cur, query_str)

        product_template_datas = {}

        for row in rows:
            key = row[6]
            row_to_dict = self.map_query_dict_product_template(row)
            transferdate = row_to_dict['transferdate'].split('.')[0]
            if key in default_code_list:
                if transferdate == default_code_values[key]['transferdate']:
                    continue

            if product_template_datas.get(key, False):
                product_template_datas[key].append(row_to_dict)
            else:
                product_template_datas[key] = [row_to_dict]

        ofm_sync_data.close_connection(conn)

        vat_product = self.get_vat_product_all_company()

        round_product = 0
        for product_template_data in product_template_datas:
            round_product = round_product + 1
            if len(product_template_datas[product_template_data]) > 1:
                _logger.info('Product Template Id Have More Than One Record !!!')

            template_line = product_template_datas[product_template_data][0]

            if template_line.get('transferdate', False):
                template_line['transferdate'] = template_line['transferdate'].split('.')[0]

            template_line.update(vat_product)

            default_code_item = default_code_values.get(template_line['default_code'], False)

            if default_code_item:
                date_transferdate = default_code_item['transferdate']
            else:
                date_transferdate = '2009-12-31 12:34:56'

            ctx = dict(self._context)
            ctx.update({
                'date_transferdate': date_transferdate,
            })

            prodct_template_dict = self.with_context(ctx).map_dict_for_create_product_template(template_line)

            str_log = ''.join([
                'update uo product default code',
                template_line['default_code']
            ])

            if default_code_item:

                product_template_id = self.env['product.template'].browse(default_code_item['id'])

                _logger.info(str_log)

                _logger.info(
                    ''.join([
                        'product.template sync default_code: ',
                        template_line['default_code'], '-',
                        ', '.join(
                            [': '.join([str(item[0]), str(item[1])]) for item in template_line.items()]
                        )]
                    )
                )

                if not prodct_template_dict['active']:
                    query_str = """
                        UPDATE stock_warehouse_orderpoint stock_wodp
                        SET active = false
                        from (
                            select id, product_tmpl_id
                            from product_product
                            where product_tmpl_id = {0}
                        )pdp
                        WHERE stock_wodp.active = True
                        AND pdp.id = stock_wodp.product_id
                    """.format(
                        default_code_item['id']
                    )
                    self.env.cr.execute(query_str)
                    log = ''.join([
                        'update Reordering Rules: Product_template id: ',
                        str(default_code_item['id'])
                    ])
                    _logger.info(log)

                state_active = product_template_id.active

                product_template_id.write(prodct_template_dict)
                self.env.cr.commit()

                if state_active is True and prodct_template_dict['active'] is True:
                    product_template_id._compute_default_code()
                    self.env.cr.commit()

            else:
                _logger.info(str_log)

                _logger.info(
                    ''.join([
                        'product.template sync default_code: ',
                        template_line['default_code'], '-',
                        ', '.join(
                            [': '.join([str(item[0]), str(item[1])]) for item in template_line.items()]
                        )
                     ])
                )

                uom_id = self.env['product.uom'].search([
                    ('name', '=', template_line['uom_id'])
                ], limit=1)

                uom_po_id = self.env['product.uom'].search([
                    ('name', '=', template_line['uom_po_id'])
                ], limit=1)

                prodct_template_dict.update({
                    'default_code': template_line['default_code'],
                    'uom_id': uom_id.id,
                    'uom_po_id': uom_po_id.id,
                })

                self.env['product.template'].create(prodct_template_dict)._compute_default_code()

                self.env.cr.commit()

            _logger.info(
                ''.join([
                    'sync product_template_data:',
                    str(round_product), '/', str(len(product_template_datas))
                ])
            )

        if not default_code_param:
            ofm_sync_data.update_interface_control_db_staging_ofm(
                'tbfranchiseproductmaster',
                len(product_template_datas),
                odoo_startdate
            )

    @api.onchange('dept_ofm')
    def onchange_dept_ofm_get_parent_dept_ofm(self):
        self.parent_dept_ofm = False
        self.parent_dept_ofm = self.dept_ofm.dept_parent_id

    def get_parent_dept_ofm_via_vals(self, vals):
        dept_ofm = vals.get('dept_ofm', False)
        if dept_ofm:
            dept_ofm_id = self.env['ofm.product.dept'].browse(dept_ofm)

            vals.update({
                'parent_dept_ofm': dept_ofm_id.dept_parent_id.id
            })

        return vals

    def update_price_product_promotion(self):
        query_str = """
            select 
                id,
                list_price,
                date_promotion_start,
                date_promotion_end,
                price_normal,
                price_promotion,
                coalesce(default_code, 'None') as default_code
            from product_template where 
            date_promotion_start is not null 
            and date_promotion_end is not null
        """

        self.env.cr.execute(query_str)
        results = self.env.cr.dictfetchall()
        tr_convert = self.env['tr.convert']
        date_now = datetime.now()
        date_now = tr_convert.convert_datetime_to_bangkok(date_now)
        i = 0
        length_result = len(results)

        for item in results:
            i += 1
            date_promotion_start = tr_convert.convert_datetime_to_bangkok(item['date_promotion_start'])
            date_promotion_end = tr_convert.convert_datetime_to_bangkok(item['date_promotion_end'])

            if all([
                date_promotion_start <= date_now <= date_promotion_end,
                item['list_price'] != item['price_promotion']
            ]):
                self.browse(item['id']).write({
                    'lst_price': item['price_promotion'],
                    'list_price': item['price_promotion'],
                    'is_promotion': True,
                })
            elif all([
                date_promotion_end < date_now < date_promotion_start,
                item['list_price'] != item['price_normal']
            ]):
                self.browse(item['id']).write({
                    'lst_price': item['price_normal'],
                    'list_price': item['price_normal'],
                    'is_promotion': False,
                })

            self.env.cr.commit()

            str_time_stamp = 'length ', i, ' / ', length_result, ' / ', item['default_code']
            _logger.info(str_time_stamp)

    @api.model
    def create(self, vals):
        if vals.get('price_normal', False):
            price_normal = vals.get('price_normal', False)
        else:
            price_normal = vals.get('list_price', False)
        if price_normal:
            vals = self.map_dict_for_create_product_price_log(vals)

        vals = self.get_parent_dept_ofm_via_vals(vals)

        res = super(ProductTemplate, self).create(vals)

        return res

    @api.multi
    def write(self, vals):
        for rec in self:
            if vals.get('price_normal', False):
                price_normal = vals.get('price_normal', False)
            else:
                price_normal = vals.get('list_price', False)
            if price_normal:
                vals = rec.map_dict_for_create_product_price_log(vals)

            vals = rec.get_parent_dept_ofm_via_vals(vals)

            return super(ProductTemplate, rec).write(vals)


class ProductBrand(models.Model):
    _name = "product.brand"
    _order = 'ofm_brand_id, id'
    _rec_name = 'brand_eng'

    sequence = fields.Integer(
        default=0,
    )
    ofm_brand_id = fields.Char(
        string='OFM ID',
    )
    brand_th = fields.Char(
        string='Brand Thai',
    )
    brand_eng = fields.Char(
        string='Brand English',
    )
    updateon = fields.Datetime(
        'UpDateOn'
    )

    transferdate = fields.Datetime(
        'TransferDate'
    )

    def map_query_dict_product_brand(self, row):
        temp = {
            'brandid': row[0],
            'brandth': row[1],
            'brandeng': row[2],
            'transferdate': row[3],
        }

        return temp

    def map_dict_for_create_product_brand(self, template_line):

        temp = {
            'brand_th': template_line['brandth'],
            'brand_eng': template_line['brandeng'],
            'transferdate': template_line['transferdate'],
        }

        return temp

    def update_product_brand_master_from_staging(self):
        ofm_sync_data = self.env['ofm.sync.data']

        conn = ofm_sync_data.open_connection()

        cur = ofm_sync_data.connect_to_db_staging_ofm(conn)

        query_str = """
            select brandid, brandth, brandeng, max(transferdate)
            from tbfranchiseproductmaster 
            group by brandid, brandth, brandeng 
            order by max(transferdate),brandid
        """

        rows = ofm_sync_data.query_data_from_db_staging_ofm(cur, query_str)

        brand_datas = {}

        for row in rows:
            key = row[0]
            row_to_dict = self.map_query_dict_product_brand(row)
            if brand_datas.get(key, False):
                brand_datas[key].append(row_to_dict)
            else:
                brand_datas[key] = [row_to_dict]

        for brand_data in brand_datas:
            if len(brand_datas[brand_data]) > 1:
                _logger.info('Brand Id Have More Than One Record !!!')
            template_line = brand_datas[brand_data][0]

            if template_line.get('transferdate', False):
                template_line['transferdate'] = template_line['transferdate'].split('.')[0]

            product_brand_id = self.search([
                ('ofm_brand_id', '=', template_line['brandid']),
            ], limit=1)

            product_brand_dict = self.map_dict_for_create_product_brand(template_line)

            str_log = ''.join([
                'update uo product brandid ',
                str(template_line['brandid'])
            ])

            if product_brand_id:
                if product_brand_id.transferdate != template_line['transferdate']:
                    _logger.info(str_log)

                    _logger.info(
                        ''.join([
                            'product.brand sync brand_id: ',
                            str(template_line['brandid']),
                            '-',
                            ', '.join(
                                [': '.join([str(item[0]), str(item[1])]) for item in template_line.items()]
                            )
                        ])
                    )

                    product_brand_id.write(product_brand_dict)

            else:
                _logger.info(str_log)

                _logger.info(
                    ''.join([
                        'product.brand sync brand_id: ',
                        str(template_line['brandid']),
                        '-',
                        ', '.join(
                            [': '.join([str(item[0]), str(item[1])]) for item in template_line.items()]
                        )
                    ])
                )

                product_brand_dict.update({
                    'ofm_brand_id': template_line['brandid'],
                })
                product_brand_id.create(product_brand_dict)

            self.env.cr.commit()

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            list_name = []
            if record.ofm_brand_id:
                list_name.append(record.ofm_brand_id)
            if record.brand_eng:
                list_name.append(record.brand_eng)
            else:
                list_name.append(record.brand_th)

            result.append((record.id, ', '.join(list_name)))

        return result


class ProductUoM(models.Model):
    _inherit = 'product.uom'

    def map_query_dict_product_uom(self, row):
        temp = {
            'uom_id': row[0],
        }
        return temp

    def map_dict_for_create_product_uom(self, template_line):

        uom_unit = self.env.ref('product.product_uom_categ_unit')

        temp = {
            'category_id': uom_unit.id,
            'name': template_line['uom_id'],
        }

        return temp

    def update_product_uom_master_from_staging(self):
        ofm_sync_data = self.env['ofm.sync.data']

        conn = ofm_sync_data.open_connection()

        cur = ofm_sync_data.connect_to_db_staging_ofm(conn)

        query_str = """
            select *
            from (
                select 
                uom_id as uom_id 
                from tbfranchiseproductmaster 
                group by uom_id
                union
                select uom_po_id as uom_id 
                from tbfranchiseproductmaster 
                group by uom_po_id
            ) temp
            group by uom_id
            order by uom_id
        """

        rows = ofm_sync_data.query_data_from_db_staging_ofm(cur, query_str)

        uom_datas = {}

        for row in rows:
            key = row[0]
            row_to_dict = self.map_query_dict_product_uom(row)
            if uom_datas.get(key, False):
                uom_datas[key].append(row_to_dict)
            else:
                uom_datas[key] = [row_to_dict]

        for uom_data in uom_datas:
            if len(uom_datas[uom_data]) > 1:
                _logger.info('Uom Id Have More Than One Record !!!')
            template_line = uom_datas[uom_data][0]

            if template_line.get('transferdate', False):
                template_line['transferdate'] = template_line['transferdate'].split('.')[0]

            product_uom_id = self.search([
                ('name', '=', template_line['uom_id']),
            ], limit=1)

            product_uom_dict = self.map_dict_for_create_product_uom(template_line)

            str_log = 'update uo product uom_id', template_line['uom_id']
            _logger.info(str_log)

            if not product_uom_id:
                self.env['product.uom'].create(product_uom_dict)

            self.env.cr.commit()


class OfmDept(models.Model):
    _name = "ofm.product.dept"
    _order = 'ofm_dept_id, ofm_sub_dept_id, ofm_class_id, ofm_sub_class_id, id'

    name = fields.Char(
        string="Name",
    )
    ofm_dept_id = fields.Char(
        string='OFM Dept ID',
    )
    ofm_sub_dept_id = fields.Char(
        string='OFM Sub Dept ID',
    )
    ofm_class_id = fields.Char(
        string='OFM class ID',
    )
    ofm_sub_class_id = fields.Char(
        string='OFM sub class ID',
    )
    dept_parent_id = fields.Many2one(
        'ofm.product.dept',
        string='OFM Dept Parent ID',
    )
    updateon = fields.Datetime(
        'UpDateOn'
    )

    transferdate = fields.Datetime(
        'TransferDate'
    )

    @api.multi
    def name_get(self):
        record_list = []
        for record in self:
            # name = [record.name]
            # if record.ofm_dept_id:
            #     name.append('Dept ID: '+record.ofm_dept_id)
            # if record.ofm_sub_dept_id:
            #     name.append('Sub Dept ID: ' + record.ofm_sub_dept_id)
            # if record.ofm_class_id:
            #     name.append('Class ID: ' + record.ofm_class_id)
            # if record.ofm_sub_class_id:
            #     name.append('Sub Class ID: ' + record.ofm_sub_class_id)
            # record_list.append((record.id, '\n'.join(name)))
            name = []
            if record.ofm_dept_id:
                name.append(record.ofm_dept_id)
            if record.dept_parent_id:
                if record.ofm_sub_dept_id:
                    name.append(record.ofm_sub_dept_id)
                if record.ofm_class_id:
                    name.append(record.ofm_class_id)
                if record.ofm_sub_class_id:
                    name.append(record.ofm_sub_class_id)
            if record.name:
                name.append(record.name)
            record_list.append((record.id, ', '.join(name)))

        return record_list

    def map_query_dict_dept(self, row):
        temp = {
            'dept': row[0],
            'dept_name': row[1],
        }
        return temp

    def map_query_dict_sub_dept(self, row):
        temp = {
            'dept': row[0],
            'sub_dpt': row[2],
            'sub_dptname': row[3],
            'class': row[4],
            'sub_class': row[5],
            'updateon': row[8],
            'transferdate': row[10],
        }
        return temp

    def map_dict_for_create_dept(self, template_line):
        temp = {
            'name': template_line['dept_name'],
            'ofm_sub_dept_id': '9999',
        }
        return temp

    def map_dict_for_create_sub_dept(self, template_line):

        product_dept_id = self.env['ofm.product.dept'].search([
            ('ofm_dept_id', '=', str(template_line['dept'])),
            ('ofm_sub_dept_id', '=', str(9999))
        ], limit=1)

        temp = {
            'name': str(template_line['sub_dptname']),
            'dept_parent_id': product_dept_id.id,
            'updateon': str(template_line['updateon']),
            'transferdate': str(template_line['transferdate']),
        }

        return temp

    def update_product_dept_master_from_staging(self):
        ofm_sync_data = self.env['ofm.sync.data']
        odoo_startdate = ofm_sync_data.get_date_interface()
        conn = ofm_sync_data.open_connection()

        cur = ofm_sync_data.connect_to_db_staging_ofm(conn)

        dept_datas = {}

        sub_dept_datas = {}

        amount_dept = 0

        query_str = """
            select dept,dept_name 
            from tbfranchisedeptmaster 
            group by dept,dept_name
            order by dept
        """

        rows = ofm_sync_data.query_data_from_db_staging_ofm(cur, query_str)

        for row in rows:
            key = row[0]
            row_to_dict = self.map_query_dict_dept(row)
            if dept_datas.get(key, False):
                dept_datas[key].append(row_to_dict)
            else:
                dept_datas[key] = [row_to_dict]

        query_str = """
            select * 
            from tbfranchisedeptmaster 
            order by dept,sub_dpt,class,sub_class
        """

        rows = ofm_sync_data.query_data_from_db_staging_ofm(cur, query_str)

        for row in rows:
            key = (row[0], row[2], row[4], row[5])
            row_to_dict = self.map_query_dict_sub_dept(row)
            if sub_dept_datas.get(key, False):
                sub_dept_datas[key].append(row_to_dict)
            else:
                sub_dept_datas[key] = [row_to_dict]

        for dept_data in dept_datas:
            if len(dept_datas[dept_data]) > 1:
                _logger.info('Dept Id Have More Than One Record !!!')
            template_line = dept_datas[dept_data][0]

            if template_line.get('transferdate', False):
                template_line['transferdate'] = template_line['transferdate'].split('.')[0]

            product_dept_id = self.env['ofm.product.dept'].search([
                ('ofm_dept_id', '=', dept_data),
                ('ofm_sub_dept_id', '=', str(9999))
            ], limit=1)

            dept_dict = self.map_dict_for_create_dept(template_line)

            if product_dept_id:
                product_dept_id.write(dept_dict)
            else:
                dept_dict.update({
                    'ofm_dept_id': template_line['dept'],
                })
                self.env['ofm.product.dept'].create(dept_dict)

            self.env.cr.commit()

        for sub_dept_data in sub_dept_datas:

            if len(sub_dept_datas[sub_dept_data]) > 1:
                _logger.info('Sup Dept Id Have More Than One Record !!!')
            template_line = sub_dept_datas[sub_dept_data][0]

            if template_line.get('transferdate', False):
                template_line['transferdate'] = template_line['transferdate'].split('.')[0]

            product_sub_dept_id = self.env['ofm.product.dept'].search([
                ('ofm_dept_id', '=', str(template_line['dept'])),
                ('ofm_sub_dept_id', '=', str(template_line['sub_dpt'])),
                ('ofm_class_id', '=', str(template_line['class'])),
                ('ofm_sub_class_id', '=', str(template_line['sub_class'])),

            ], limit=1)

            product_sub_dept_dict = self.map_dict_for_create_sub_dept(template_line)

            str_log = ''.join([
                'update uo product product_sub_dept_id ',
                template_line['dept'],
                template_line['sub_dpt'],
                template_line['class'],
                template_line['sub_class']
            ])

            if product_sub_dept_id:
                if product_sub_dept_id.transferdate != template_line['transferdate']:
                    _logger.info(str_log)
                    _logger.info(
                        ''.join([
                            'ofm.product.dept sync dept: ',
                            template_line['dept'] + ' sub_dpt: ' + template_line['sub_dpt'],
                            '-',
                            ', '.join(
                                [': '.join([str(item[0]), str(item[1])]) for item in template_line.items()])
                            ])
                        )
                    product_sub_dept_id.write(product_sub_dept_dict)

                    amount_dept += 1
            else:
                _logger.info(str_log)
                _logger.info(
                    ''.join([
                        'ofm.product.dept sync dept: ',
                        template_line['dept'],
                        ' sub_dpt: ',
                        template_line['sub_dpt'],
                        '-',
                        ', '.join(
                            [': '.join([str(item[0]), str(item[1])]) for item in template_line.items()])
                    ])
                )
                product_sub_dept_dict.update({
                    'ofm_dept_id': str(template_line['dept']),
                    'ofm_sub_dept_id': str(template_line['sub_dpt']),
                    'ofm_class_id': str(template_line['class']),
                    'ofm_sub_class_id': str(template_line['sub_class']),
                })
                self.env['ofm.product.dept'].create(product_sub_dept_dict)

                amount_dept += 1

            self.env.cr.commit()

        ofm_sync_data.update_interface_control_db_staging_ofm(
            'tbfranchisedeptmaster',
            amount_dept,
            odoo_startdate
        )

        ofm_sync_data.close_connection(conn)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    _sql_constraints = [
        ('barcode_uniq', 'Check(1=1)', _("A barcode can only be assigned to one product !")),
    ]

    default_code = fields.Char(
        string='Internal Reference (PID)',
    )

    incoming_qty_pr_sent = fields.Float(
        string='Incoming PR Sent',
        compute='_compute_quantities',
        search='_search_incoming_qty',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Quantity of products that are planned to arrive.\n"
             "In a context with a single Stock Location, this includes "
             "goods arriving to this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods arriving to the Stock Location of this Warehouse, or "
             "any of its children.\n"
             "Otherwise, this includes goods arriving to any Stock "
             "Location with 'internal' type."
    )

    template_ids = fields.Many2many(
        'pos_product.template',
        'pos_product_template_line',
        'product_id',
        'template_id',
        string='POS Product Template',
        readonly=True,
    )

    @api.multi
    def _select_seller(self, partner_id=False, quantity=0.0, date=None, uom_id=False):
        company_id = self._context.get('company_id', False)
        branch_id = self._context.get('branch_id', False)

        self.ensure_one()
        if date is None:
            date = fields.Date.today()

        res = self.env['product.supplierinfo']
        for seller in self.seller_ids:
            # Set quantity in UoM of seller
            quantity_uom_seller = quantity
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                quantity_uom_seller = uom_id._compute_quantity(quantity_uom_seller, seller.product_uom)

            if company_id and seller.company_id.id != company_id:
                continue
            if branch_id and seller.branch_id.id != branch_id:
                continue
            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if partner_id and seller.name not in [partner_id, partner_id.parent_id]:
                continue
            # if quantity_uom_seller < seller.min_qty:
            #     continue
            if seller.product_id and seller.product_id != self:
                continue

            res |= seller
            break
        return res

    def find_product_price(self, partner_id=None, company_id=None, branch_id=None):
        product_id = self._context.get('product_id', False)
        if product_id and not self.id:
            product = self.browse(product_id)
        else:
            product = self

        if not product.id or not company_id or not branch_id:
            return

        if not partner_id:
            partner_id = self.env['res.partner'].search([('vat', '=', self.env['ir.config_parameter'].get_param('prs_default_vendor'))])

        seller = product.with_context({
            'company_id': company_id,
            'branch_id': branch_id
        })._select_seller(partner_id)

        if seller:
            return seller.price
        else:
            return 0

    def find_product_price_in_dropship(self):
        product_id = self._context.get('product_id', False)
        if product_id and not self.id:
            product = self.browse(product_id)
        else:
            product = self

        if not product.id:
            return

        product_price_dropship = self.env['product.price.dropship'].search([
            ('product_product_id', '=', product.id),
        ])
        if product_price_dropship:
            return product_price_dropship.purchasepriceexvat
        else:
            return 0

    def find_purchase_price_with_dropship(self, partner_id, company_id, branch_id):
        product_id = self._context.get('product_id', False)
        if product_id and not self.id:
            product = self.browse(product_id)
        else:
            product = self

        if not product.id:
            return

        if not partner_id:
            partner_id = self.env['res.partner'].search([('vat', '=', self.env['ir.config_parameter'].get_param('prs_default_vendor'))])

        price = self.find_product_price(partner_id, company_id, branch_id)
        if price > 0:
            return price
        else:
            price = self.find_product_price_in_dropship()
            if price > 0:
                return price
            else:
                return 0

    def get_product_from_model_line(self, model, model_line):
        model_line_ids = []
        product_ids = []

        for item in model_line:
            if model:
                if model == self._name:
                    model_line_ids.append(item[1])
                else:
                    if item[0] == 4:
                        model_line_ids.append(item[1])
                    elif item[0] == 2:
                        continue
                    else:
                        product_id = item[2].get('product_id', False)
                        if product_id:
                            product_ids.append(product_id)

        if len(model_line_ids) > 0:
            if model == self._name:
                for model_line_id in model_line_ids:
                    product_ids.append(model_line_id)

                return product_ids
            else:
                model_db = model.replace('.', '_')
                query_model_line_ids = ''

                for model_line_id in model_line_ids:
                    query_model_line_ids += str(model_line_id)
                    query_model_line_ids += ','

                query_model_line_ids = query_model_line_ids[:-1]

                query_str_model = """
                    select id,
                        product_id
                    from %s
                    where id in (%s)
                """ % (model_db, query_model_line_ids)

                self.env.cr.execute(query_str_model)
                result_model = self.env.cr.dictfetchall()

                for result_item in result_model:
                    product_id = result_item.get('product_id', False)

                    if product_id:
                        product_ids.append(product_id)

        return product_ids

    def get_where_product_template(self):
        return ''

    def get_search_model_exclude_barcode(self):
        model_exclude_barcode = [
            'pricelists',
            'pricelists.line',
            'ofm.purchase.order.line',
        ]

        return model_exclude_barcode

    def get_search_model_include_prod_status(self):
        model_include_prod_status = [
            'ofm.purchase.order.line',
        ]

        return model_include_prod_status

    def get_product_by_query(self, name, product_include, product_exclude):
        branch_id = self.env.context.get('branch_id', False)
        search_model = self.env.context.get('search_model', False)

        name = name.lower()

        if branch_id:
            query_branch = 'where id = {0}'.format(branch_id)
        else:
            query_branch = ''

        if search_model not in self.get_search_model_exclude_barcode():
            query_barcode = """or pp.barcode like '%{0}%'""".format(name)
        else:
            query_barcode = ''

        product_include_ids = ','.join(map(str, product_include))
        product_exclude_ids = ','.join(map(str, product_exclude))

        if all([
            len(product_include) > 0,
            len(product_exclude) > 0,
        ]):
            query_where_product_product = """
                    and id in ({0})
                    and id not in ({1})
            """.format(product_include_ids, product_exclude_ids)
        elif all([
            len(product_include) > 0,
            len(product_exclude) < 1,
        ]):
            query_where_product_product = """
                and id in ({0})
            """.format(product_include_ids)
        elif all([
            len(product_include) < 1,
            len(product_exclude) > 0,
        ]):
            query_where_product_product = """
                and id not in ({0})
            """.format(product_exclude_ids)
        else:
            query_where_product_product = ''

        query_tb_product = """
            select id,
                lower(default_code) as default_code,
                lower(barcode) as barcode,
                product_tmpl_id
            from product_product
            where active = true
            {0}
        """.format(query_where_product_product)

        query_where_product_template = self.get_where_product_template()

        query_tb_product_template = """
            select id,
                lower(name) as name
            from product_template
            where active = true
            {0}
        """.format(query_where_product_template)

        if branch_id:
            query_str = """
                select pp.product_product_id
                from (
                    select pos_pt.product_product_id,
                        pp.default_code,
                        pp.barcode,
                        pp.product_tmpl_id
                    from (
                        select pos_ptline.product_id as product_product_id
                        from(
                            select pos_pt.id,
                                pos_pt.template_name
                            from pos_product_template as pos_pt
                            inner join (
                                select id,
                                    branch_code
                                from pos_branch
                                {0}
                            ) as pos_branch
                            on pos_pt.template_name = pos_branch.branch_code
                        ) as pos_pt
                        inner join pos_product_template_line as pos_ptline
                        on pos_pt.id = pos_ptline.template_id
                    ) as pos_pt
                    inner join ({1}) as pp
                    on pos_pt.product_product_id = pp.id
                ) as pp
                inner join ({2}) as pt
                on pp.product_tmpl_id = pt.id
                where pp.default_code like '%{3}%'
                    or pt.name like '%{4}%'
                    {5}
            """.format(
                query_branch,
                query_tb_product,
                query_tb_product_template,
                name,
                name,
                query_barcode
            )
        else:
            query_str = """
                select pp.id as product_product_id
                from ({0}) as pp
                inner join ({1}) as pt
                on pp.product_tmpl_id = pt.id
                where pp.default_code like '%{2}%'
                    or pt.name like '%{3}%'
                    {4}
            """.format(
                query_tb_product,
                query_tb_product_template,
                name,
                name,
                query_barcode
            )

        self.env.cr.execute(query_str)
        result_model = self.env.cr.dictfetchall()

        product_ids = []

        for result_item in result_model:
            product_id = result_item.get('product_product_id', False)

            if product_id:
                product_ids.append(product_id)

        return product_ids

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        branch_id = self.env.context.get('branch_id', False)
        search_model = self.env.context.get('search_model', False)

        if any([
            branch_id,
            search_model,
        ]):
            exclude_model = self._context.get('exclude_model', False)
            exclude_order_line = self.env.context.get('exclude_order_line', False)
            product_include_model = self.env.context.get('product_include_model', False)
            product_include_ids = self.env.context.get('product_include_ids', False)

            if all([
                exclude_model,
                exclude_order_line,
            ]):
                exclude_ids = self.get_product_from_model_line(exclude_model, exclude_order_line)
            else:
                exclude_ids = []

            if all([
                product_include_model,
                product_include_ids,
            ]):
                include_ids = self.get_product_from_model_line(product_include_model, product_include_ids)
            else:
                include_ids = []

            name_search = self._context.get('name_search', '')

            product_where_ids = self.get_product_by_query(name_search, include_ids, exclude_ids)

            if len(product_where_ids) > 0:
                args += [('id', 'in', product_where_ids)]
            else:
                args = [('id', '=', 0)]

        return super(ProductProduct, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=160):
        branch_id = self.env.context.get('branch_id', False)
        search_model = self.env.context.get('search_model', False)

        if any([
            branch_id,
            search_model,
        ]):
            ctx = dict(self._context)
            ctx.update({
                'name_search': name,
            })

            product_ids = self.with_context(ctx).search([

                ] + args,
                limit=limit
            )

            return product_ids.sudo().name_get()

        elif all([
            search_model,
            any([
                search_model == 'pricelists',
                search_model == 'pricelists.line',
            ]),
        ]):
            product_ids = self.search([
                '|',
                ('name', 'ilike', name),
                ('default_code', 'ilike', name)
            ] + args,
            limit=limit
            )

            return product_ids.sudo().name_get()

        return super(ProductProduct, self).name_search(name, args, operator, limit)

    @api.multi
    def action_sync_data_product(self):
        for record in self:
            record.product_tmpl_id.update_product_master_from_staging(
                record.product_tmpl_id.default_code
            )

    @api.multi
    def action_sync_data_template_product(self):
        for record in self:
            pos_product_template = record.env['pos_product.template']
            pos_product_template.update_product_branch_from_staging(
                record.product_tmpl_id.default_code
            )

    @api.depends('stock_quant_ids', 'stock_move_ids')
    def _compute_quantities(self):
        super(ProductProduct, self)._compute_quantities()
        compute_quantities_dict = self._compute_quantities_dict(self._context.get('lot_id'),
                                                                self._context.get('owner_id'),
                                                                self._context.get('package_id'),
                                                                self._context.get('from_date'),
                                                                self._context.get('to_date'))
        for product in self:
            if self._context.get('branch_id', False):
                product.incoming_qty_pr_sent = compute_quantities_dict[product.id]['incoming_qty_pr_sent']

    @api.multi
    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        res = super(ProductProduct, self)._compute_quantities_dict(lot_id, owner_id, package_id, from_date, to_date)

        if self._context.get('branch_id', False):
            purchase_order_ids = self.env['purchase.order'].search([
                ('state', '=', 'sent'),
                ('branch_id', '=', self._context.get('branch_id'))
            ])

            for product in self.with_context(prefetch_fields=False):
                incoming_qty_pr_sent = 0
                for purchase_order_id in purchase_order_ids:
                    purchase_order_line_ids = purchase_order_id.ofm_purchase_order_line_ids
                    purchase_order_product_ids = purchase_order_line_ids.filtered(lambda rec: rec.product_id.id == product.id)

                    for purchase_order_product_id in purchase_order_product_ids:
                        incoming_qty_pr_sent += purchase_order_product_id.product_qty

                res[product.id].update({
                    'incoming_qty_pr_sent': incoming_qty_pr_sent
                })

                res[product.id]['virtual_available'] = float_round(
                    res[product.id]['qty_available'] +
                    ((res[product.id]['incoming_qty'] + incoming_qty_pr_sent) -
                     res[product.id]['outgoing_qty']),
                    precision_rounding=product.uom_id.rounding
                )

        return res

    @api.onchange('dept_ofm')
    def onchange_dept_ofm_get_parent_dept_ofm(self):
        self.parent_dept_ofm = False
        self.parent_dept_ofm = self.dept_ofm.dept_parent_id

    def read_price_by_product_ids(self, product_ids, branch_id, pp_col, pt_col):
        # pp_table_rel is product_product
        # pt_table_rel is product_template
        pp_table_rel = "pp"
        pt_table_rel = "pt"

        extra_query = ""
        if pp_col and len(pp_col):
            extra_query = "," + ",".join([pp_table_rel + "." + item for item in pp_col])

        if pt_col and len(pt_col):
            extra_query = "," + ",".join([pt_table_rel + "." + item for item in pt_col])

        if not all([
            product_ids,
            len(product_ids),
            branch_id,
        ]):
            return []

        if len(product_ids) == 1:
            product_ids.append(product_ids[0])

        query_str = """
            WITH temp_pricelists (
                pricelists_id,
                is_except_branch,
                pricelists_sequence,
                pricelists_start_date,
                pricelists_end_date
                ) AS
                (
                    select id as pricelists_id,
                    is_except_branch as is_except_branch,
                    sequence as pricelists_sequence,
                    start_date as pricelists_start_date,
                    end_date as pricelists_start_date
                    from pricelists
                    where Now() BETWEEN start_date AND end_date
                    and active is true
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
                ),
                temp_product(
                    product_id,
                    price_inc_vat
                ) as
                (
                select distinct on (pll.product_id)
                    pll.product_id,
                    pll.price_inc_vat
                from (
                    select tpl.pricelists_id,
                        tpl.pricelists_sequence
                    from temp_pricelists tpl
                    left join temp_pricelists_branch_rel bpr on tpl.pricelists_id = bpr.pricelists_id
                    where (
                        case when bpr.pos_branch_id is not null
                            -- parameter --
                            then pos_branch_id = {branch_id}
                            else bpr.pricelists_id is null 
                        end
                    )
                    and is_except_branch is false 
            
                    union all 
            
                    select tpl.pricelists_id,
                        tpl.pricelists_sequence
                    from temp_pricelists tpl
                    left join (
                            select *
                            from temp_pricelists_branch_rel
                            -- parameter --
                            where pos_branch_id = {branch_id}
                        ) bpr on tpl.pricelists_id = bpr.pricelists_id
                    where (
                        case when bpr.pricelists_id is not null 
                            then false
                            else true
                        end
                    )
                    and is_except_branch is true
                    ) prl
                inner join pricelists_line pll on prl.pricelists_id = pll.pricelists_id
                order by pll.product_id,
                        --prl.pricelists_sequence,
                        pll.id desc
                )
            
            select {pp_table_rel}.id,
                case when tpd.price_inc_vat is not null 
                    then 
                        tpd.price_inc_vat
                    else
                        case when pt.price_normal is null
                            then
                                {pt_table_rel}.list_price
                            when {pt_table_rel}.price_promotion > 0 and now() between
                            {pt_table_rel}.date_promotion_start::timestamp and {pt_table_rel}.date_promotion_end::timestamp
                            then 
                                {pt_table_rel}.price_promotion 
                            else 
                                {pt_table_rel}.price_normal
                        end
                end as price,
                {pt_table_rel}.date_promotion_start::timestamp,
                {pt_table_rel}.date_promotion_end::timestamp,
                case when now() < pt.date_promotion_start::timestamp
                    then pt.date_promotion_start::timestamp
                    when now() < pt.date_promotion_end::timestamp
                    then pt.date_promotion_end::timestamp
                end as next_interval,
                {pt_table_rel}.price_promotion,
                {pt_table_rel}.price_normal{extra_query}
            from product_product {pp_table_rel}
            left join temp_product as tpd on {pp_table_rel}.id = tpd.product_id
            left join product_template as {pt_table_rel} on {pp_table_rel}.product_tmpl_id = {pt_table_rel}.id
            where {pp_table_rel}.id in {product_ids}
            order by {pp_table_rel}.id asc
        """.format(
            pp_table_rel=pp_table_rel,
            pt_table_rel=pt_table_rel,
            branch_id=branch_id,
            product_ids=tuple(product_ids),
            extra_query=extra_query
        )
        # print query_str
        self._cr.execute(query_str)
        products = self._cr.dictfetchall()
        if products:
            return products
        else:
            return []

    def read_customer_tax_ids_by_product_ids(self, product_ids):
        if not all([
            product_ids,
            len(product_ids),
        ]):
            return []

        query_str = """
            select
                pp.id as id,
                string_agg(ptl.tax_id::text, ',') as taxes_id
            from
                product_taxes_rel ptl
            inner join product_product pp on
                ptl.prod_id = pp.product_tmpl_id
            where
                pp.id in {product_ids}
            group by pp.id
            order by pp.id
        """.format(
            product_ids=tuple(product_ids),
        )
        # print query_str
        self._cr.execute(query_str)
        products = self._cr.dictfetchall()
        if products:
            product_dict = {}
            for product in products:
                product_dict[product['id']] = eval('[' + product['taxes_id'] + ']')
            del products
            return product_dict
        else:
            return []


class ProductLog(models.Model):
    _name = 'product.price.log'
    _order = 'id desc'

    product_template_id = fields.Many2one(
        comodel_name='product.template',
        string='Promotion Template'
    )

    price_normal = fields.Float(
        string='Retail Price'
    )

    price_promotion = fields.Float(
        string='Promotion Price'
    )

    date_promotion_start = fields.Datetime(
        string='Start Promotion Date'
    )

    date_promotion_end = fields.Datetime(
        string='End Promotion Date'
    )


class ProductPriceDropshipTemp(models.Model):
    _name = 'product.price.dropship.temp'

    default_code = fields.Char(
        string='Internal Reference (PID)',
        readonly=True
    )

    purchasepriceexvat = fields.Float(
        string='Purchase Price',
        digits=dp.get_precision('Product Price'),
        readonly=True,
    )

    transferdate = fields.Datetime(
        string='Transfer Date',
        readonly=True,
    )


class ProductPriceDropship(models.Model):
    _name = 'product.price.dropship'

    default_code = fields.Char(
        string='Internal Reference (PID)',
        readonly=True
    )

    product_product_id = fields.Integer(
        string='Product Product ID',
        readonly=True,
    )

    product_template_id = fields.Integer(
        string='Product Product ID',
        readonly=True,
    )

    purchasepriceexvat = fields.Float(
        string='Purchase Price',
        digits=dp.get_precision('Product Price'),
        readonly=True,
    )

    transferdate = fields.Datetime(
        string='Transfer Date',
        readonly=True,
    )

    is_dropship_active = fields.Boolean(
        string="Dropship Active",
        default=True,
    )

    prod_status = fields.Char(
        'ProdStatus',
    )

    def get_product_price_from_col(self):
        ofm_sync_data = self.env['ofm.sync.data']
        conn = ofm_sync_data.open_connection()
        cur = ofm_sync_data.connect_to_db_staging_ofm_to_dict(conn)

        try:
            query_str = """
                select pid as default_code,
                    purchasepriceexvat,
                    (transferdate - interval '7 hours')::timestamp as transferdate
                from tbfranchise_dropship
            """

            product_price_dropship = ofm_sync_data.query_data_from_db_staging_ofm_to_dict(cur, query_str)

            if len(product_price_dropship) > 0:
                query_insert = 'truncate product_price_dropship_temp; '

                for product_price_id in product_price_dropship:
                    query_insert += """
                        insert into product_price_dropship_temp (default_code, purchasepriceexvat, transferdate)
                        values('{0}', {1}, '{2}'); 
                    """.format(
                        product_price_id.get('default_code'),
                        product_price_id.get('purchasepriceexvat'),
                        product_price_id.get('transferdate')
                    )

                self.env.cr.execute(query_insert)
                self.env.cr.commit()
                return True
            else:
                return False
        except Exception, e:
            _logger.error(e)

            return False
        finally:
            ofm_sync_data.close_connection(conn)

    def compare_product_price_dropship(self):
        query_string = """
            WITH with_product_price_dropship as (
                select ppd.id,
                    coalesce(ppdtemp.default_code, ppd.default_code) as default_code,
                    coalesce(ppdtemp.purchasepriceexvat, ppd.purchasepriceexvat) as purchasepriceexvat,
                    coalesce(ppdtemp.transferdate, ppd.transferdate) as transferdate,
                    ppd.product_product_id,
                    ppd.product_template_id,
                    (case when ppd.default_code is null then true else false end) as is_create,
                    (case when ppdtemp.default_code is null then true else false end) as is_delete,
                    (case when ppd.transferdate < ppdtemp.transferdate then true else false end) as is_update
                from product_price_dropship as ppd
                full outer join product_price_dropship_temp as ppdtemp
                on ppd.default_code = ppdtemp.default_code
            ),
            with_insert as (
                insert into product_price_dropship (
                    create_uid, 
                    purchasepriceexvat, 
                    product_product_id, 
                    write_uid, 
                    transferdate, 
                    product_template_id, 
                    write_date, 
                    create_date, 
                    default_code
                )
                select {0},
                    pdd.purchasepriceexvat,
                    pd.id as product_product_id,
                    {1},
                    pdd.transferdate,
                    pd.product_tmpl_id as product_template_id,
                    current_timestamp::timestamp,
                    current_timestamp::timestamp,
                    pdd.default_code
                from (
                    select default_code,
                        purchasepriceexvat,
                        transferdate
                    from with_product_price_dropship
                    where is_create = true
                ) as pdd
                inner join product_product as pd
                on pdd.default_code = pd.default_code and pd.active = true
                returning id as id_insert
            ),
            with_update as (
                update product_price_dropship
                set purchasepriceexvat = wppd.purchasepriceexvat,
                    transferdate = wppd.transferdate,
                    write_uid = {2},
                    write_date = current_timestamp::timestamp
                from with_product_price_dropship as wppd
                where wppd.is_update = true and product_price_dropship.id = wppd.id
                returning product_price_dropship.id as id_update
            ),
            with_delete as (
                delete from product_price_dropship
                where default_code in (select default_code from with_product_price_dropship where is_delete = true)
                returning id as id_delete
            )
            
            select
                (select count(1) from with_product_price_dropship where is_create = true) as amount_create,
                (select count(1) from with_product_price_dropship where is_update = true) as amount_update,
                (select count(1) from with_product_price_dropship where is_delete = true) as amount_delete;
        """.format(
            self.env.user.id,
            self.env.user.id,
            self.env.user.id
        )

        self.env.cr.execute(query_string)
        query_result = self.env.cr.dictfetchall()
        self.env.cr.execute('truncate product_price_dropship_temp;')
        self.env.cr.commit()

        query_result = query_result[0] if len(query_result) > 0 else {}

        return query_result

    def update_product_price_from_col(self):
        ofm_sync_data = self.env['ofm.sync.data']
        odoo_startdate = ofm_sync_data.get_date_interface()
        product_price = self.get_product_price_from_col()

        if product_price:
            product_price_result = self.compare_product_price_dropship()
            amount_create = product_price_result.get('amount_create', 0)
            amount_update = product_price_result.get('amount_update', 0)
            amount_delete = product_price_result.get('amount_delete', 0)

            _logger.info(
                'Sync tbfranchise_dropship: Create {0}, Update {1}, Delete {2}'.format(
                    amount_create,
                    amount_update,
                    amount_delete
                )
            )

            ofm_sync_data.update_interface_control_db_staging_ofm(
                'tbfranchise_dropship',
                amount_create + amount_update,
                odoo_startdate
            )










