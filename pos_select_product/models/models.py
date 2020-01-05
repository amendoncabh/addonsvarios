# -*- coding: utf-8 -*-

from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _, tools
import time
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    #    product_ids = fields.Many2many('product.product', domain="[('available_in_pos','=',True)]")

    pos_product_template_id = fields.Many2one(
        'pos_product.template',
        string="Template",
        required=True,
    )


class PosProductTemplate(models.Model):
    _name = 'pos_product.template'
    _order = "sequence, id"

    sequence = fields.Integer(
        'Sequence',
        help="Gives the sequence order when displaying a list of product categories."
    )

    check_active = fields.Boolean(
        string='Active',
        default=True,
    )

    name = fields.Char(
        compute='_get_name',
        string='Name',
        store=True
    )
    template_name = fields.Char(
        'Name'
    )
    product_ids = fields.One2many(
        'pos.product.template.line',
        'template_id',
        'Template Line',
        domain=[],
    )
    company_id = fields.Many2one(
        'res.company',
        string = 'Company'
    )

    @api.multi
    @api.depends('name', 'template_name')
    def _get_name(self):
        for template_product in self:
            template_product.update({
                'name': template_product.template_name
            })

    def map_query_dict_product_branch(self, row):
        temp = {
            'storecode': row[0],
            'default_code': row[1],
            'barcode': row[2],
            'purchaseprice': row[3],
            'transferdate': row[4],
            'maxqty': row[5],
            'minqty': row[6],
            'minpurqty': row[7],
        }

        return temp

    def create_update_template_line(self, template_line, pos_product_template_id, pos_branch_id):

        list_value_for_compare = self._context.get('list_value_for_compare', False)
        if list_value_for_compare:
            default_code_values = list_value_for_compare[0]
        else:
            raise ValidationError(_("None Require context"))

        key = (pos_product_template_id.name, template_line['default_code'])

        default_code_item = default_code_values.get(key, False)

        pos_template_line = self.env['pos.product.template.line']
        product_product = self.env['product.product']

        str_log = 'update uo pos_template_line_id', pos_product_template_id.name, template_line['default_code']

        if default_code_item:

            pos_template_line_id = pos_template_line.browse(default_code_item['template_line_id'])

            _logger.info(str_log)

            _logger.info('pos.product.template default_code: ' + template_line['default_code']
                         + ' pos_template_line_id: ' + pos_product_template_id.name + '-'
                         + ', '.join([': '.join([str(item[0]), str(item[1])]) for item in template_line.items()]))

            pos_template_line_id.write({
                'template_id': pos_product_template_id.id,
                'transferdate': template_line['transferdate'],
            })
            self.env.cr.commit()
        else:

            product_id = product_product.search([
                ('product_tmpl_id.default_code', 'ilike', template_line['default_code']),
            ], limit=1)

            if product_id:
                _logger.info(str_log)

                _logger.info('pos.product.template default_code: ' + template_line['default_code']
                             + ' pos_template_line_id: ' + pos_product_template_id.name + '-'
                             + ', '.join([': '.join([str(item[0]), str(item[1])]) for item in template_line.items()]))

                pos_template_line.create({
                    'product_id': product_id.id,
                    'template_id': pos_product_template_id.id,
                    'transferdate': template_line['transferdate'],
                })
                self.env.cr.commit()
            else:
                str_alert = "Product default code is %s not found" % template_line['default_code']
                _logger.info(str_alert)

    def update_product_branch_from_staging(self, default_code_param=False):

        pos_template = self.env['pos_product.template']
        ofm_sync_data = self.env['ofm.sync.data']
        odoo_startdate = ofm_sync_data.get_date_interface()
        pos_branch = self.env['pos.branch']

        query_str = """
            select 
                pptl.id as template_line_id,
                pt.id as product_tempalte_id,
                pp.id as product_product_id,
                pt.default_code,
                ppt.name as branch_code,
                pptl.transferdate
            from
                pos_product_template_line pptl
                inner join pos_product_template ppt on ppt.id = pptl.template_id
                inner join product_product pp on pp.id = pptl.product_id
                inner join product_template pt on pt.id = pp.product_tmpl_id
        """

        self.env.cr.execute(query_str)
        query_results = self.env.cr.dictfetchall()

        default_code_list = []
        default_code_values = {}

        for item in query_results:
            key = (item['branch_code'], item['default_code'])
            product_item = default_code_values.get(key, False)
            if not product_item:
                default_code_values.update({
                    key: {
                        'template_line_id': item['template_line_id'],
                        'transferdate': item['transferdate'] and item['transferdate'].split('.')[0] or False,
                        'product_tempalte_id': item['product_tempalte_id'],
                        'product_product_id': item['product_product_id'],
                        'branch_code': item['branch_code']
                    }
                })
                default_code_list.append(key)

        query_str = """
                    select 
                        pp.id product_product_id,
                        pt.default_code
                    from
                        product_product pp
                        inner join product_template pt on pt.id = pp.product_tmpl_id
                """

        self.env.cr.execute(query_str)
        query_results = self.env.cr.dictfetchall()

        product_product_values = {}

        for item in query_results:
            key = item['default_code']
            product_item = product_product_values.get(key, False)
            if not product_item:
                product_product_values.update({
                    key: {
                        'product_product_id': item['product_product_id'],
                    }
                })

        conn = ofm_sync_data.open_connection()

        cur = ofm_sync_data.connect_to_db_staging_ofm(conn)

        query_str = """
            SELECT 
                tbfb.storecode,
                tbfp.default_code, 
                tbfp.barcode, 
                tbfb.purchaseprice, 
                max(tbfb.transferdate) as transferdate,
                max(tbfb.maxqty) as maxqty,
                max(tbfb.minqty) as minqty,
                max(tbfb.minpurqty) as minpurqty
            from tbfranchisebranch tbfb
            inner join tbfranchiseproductmaster tbfp on tbfp.default_code = tbfb.pid
        """

        if default_code_param:
            query_str += """
                        where tbfp.default_code = '%s'
                    """ % default_code_param

        query_str += """
            group by tbfb.storecode, tbfp.default_code, tbfp.barcode, tbfb.purchaseprice
        """

        rows = ofm_sync_data.query_data_from_db_staging_ofm(cur, query_str)

        data_products_branch = {}

        for row in rows:
            key = row[0]
            row_to_dict = self.map_query_dict_product_branch(row)
            key2 = (row_to_dict['storecode'], row_to_dict['default_code'])
            transferdate = row_to_dict['transferdate'].split('.')[0]
            if key2 in default_code_list:
                if transferdate == default_code_values[key2]['transferdate']:
                    continue

            if data_products_branch.get(key, False):
                data_products_branch[key].append(row_to_dict)
            else:
                data_products_branch[key] = [row_to_dict]

        ofm_sync_data.close_connection(conn)

        list_value_for_compare = [
            default_code_values,
            product_product_values
        ]

        round_branch = 0

        for data_product_branch in data_products_branch:
            round_branch = round_branch + 1
            pos_product_template_id = pos_template.search([
                ('name', '=', data_product_branch)
            ], limit=1)

            if not pos_product_template_id:
                pos_product_template_id = self.create({
                    'name': data_product_branch,
                    'template_name': data_product_branch
                })

            pos_branch_id = pos_branch.search([
                ('branch_code', '=', data_product_branch),
            ], limit=1)

            if not pos_branch_id:
                str_alert = "POS branch code is %s not found" % data_product_branch
                _logger.info(str_alert)
                continue
            round_product = 0
            for template_line in data_products_branch[pos_branch_id.branch_code]:
                round_product = round_product + 1
                if template_line.get('transferdate', False):
                    template_line['transferdate'] = template_line['transferdate'].split('.')[0]

                self.with_context(
                    list_value_for_compare=list_value_for_compare
                ).create_update_template_line(
                    template_line,
                    pos_product_template_id,
                    pos_branch_id
                )
                _logger.info(
                    ''.join([
                        'sync product_branch:',
                        str(round_branch), '/', str(len(data_products_branch)),
                        ' sync product:',
                        str(round_product), '/', str(len(data_products_branch[pos_branch_id.branch_code]))
                    ])
                )

        ofm_sync_data.update_interface_control_db_staging_ofm(
            'tbfranchisebranch',
            len(data_products_branch),
            odoo_startdate
        )

        return data_products_branch


class PosProductTemplateLine(models.Model):
    _name = 'pos.product.template.line'

    @api.one
    def _compute_price_promotion(self):
        if self.product_template_id.price_promotion:
            self.price_promotion = self.product_template_id.price_promotion
    
    @api.one
    def _compute_promotion_start(self):
        if self.product_template_id.date_promotion_start:
            self.promotion_start = self.product_template_id.date_promotion_start

    @api.one
    def _compute_promotion_end(self):
        if self.product_template_id.date_promotion_end:
            self.promotion_end = self.product_template_id.date_promotion_end 
    
    @api.one
    def _compute_dept(self):
        if self.product_template_id.parent_dept_ofm:
            self.dept_ofm = self.product_template_id.parent_dept_ofm

    @api.one
    def _compute_sub_dept(self):
        if self.product_template_id.dept_ofm:
            self.sub_dept_ofm = self.product_template_id.dept_ofm
    
    @api.one
    def _compute_categ(self):
        if self.product_template_id.categ_id:
            self.categ_id = self.product_template_id.categ_id

    @api.one
    def _compute_is_best_deal(self):
        if self.product_template_id.is_best_deal_promotion:
            self.is_best_deal = self.product_template_id.is_best_deal_promotion

    @api.one
    def _compute_remark(self):
        if self.product_template_id.prod_remark_ofm:
            self.remark = self.product_template_id.prod_remark_ofm
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )

    product_template_id = fields.Many2one(
        'product.template',
        related='product_id.product_tmpl_id'
    )

    available_in_pos = fields.Boolean(
        string = 'Available in POS',
        related = 'product_id.available_in_pos',
        readonly = 'True'
    )

    barcode = fields.Char(
        string = 'Barcode',
        related = 'product_id.barcode'
    )

    uom_id = fields.Many2one(
        'product.uom',
        string = 'Unit of Measure',
        related = 'product_template_id.uom_id'
    )

    price_list = fields.Float(
        string = 'Price list',
        related = 'product_template_id.list_price'
    )

    promotion_start = fields.Datetime(
        string = 'Promotion Start',
        compute = '_compute_promotion_start'
    )

    promotion_end = fields.Datetime(
        string = 'Promotion End',
        compute = '_compute_promotion_end'
    )

    categ_id = fields.Many2one(
        'product.category',
        string = 'Product Category',
        compute = '_compute_categ'
    )

    dept_ofm = fields.Many2one(
        'ofm.product.dept',
        string = 'Product Dept',
        compute = '_compute_dept'
    )

    sub_dept_ofm = fields.Many2one(
        'ofm.product.dept',
        string = 'Product Sub Dept',
        compute = '_compute_sub_dept'
    )

    price_promotion = fields.Float(
        string = 'Price Promotion',
        compute = '_compute_price_promotion'
    )

    product_id_int = fields.Integer(
        string="Product ID",
        required=False,
        related='product_id.id',
    )

    is_best_deal = fields.Boolean(
        string = 'is Best Deal',
        compute = '_compute_is_best_deal'
    )

    remark = fields.Char(
        string = 'Remark',
        compute = '_compute_remark'
    )

    default_code = fields.Char(
        related='product_id.default_code',
        string='Internal Reference (PID)',
        readonly=True
    )

    template_id = fields.Many2one(
        'pos_product.template',
        string='Template Name',
        readonly=True,
        ondelete="cascade",
    )

    updateon = fields.Datetime(
        'UpDateOn'
    )

    transferdate = fields.Datetime(
        'TransferDate'
    )

    