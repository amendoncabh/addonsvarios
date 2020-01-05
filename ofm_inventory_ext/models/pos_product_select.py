# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PosProductTemplate(models.Model):
    _inherit = 'pos_product.template'

    def map_dict_for_create_warehouse_orderpoint(self, template_line):
        res = {
            'product_min_qty': template_line['minqty'],
            'product_max_qty': template_line['maxqty'],
            'transferdate': template_line['transferdate']
        }
        return res

    def create_update_template_line(self, template_line, pos_product_template_id, pos_branch_id):
        super(PosProductTemplate, self).create_update_template_line(
            template_line,
            pos_product_template_id,
            pos_branch_id
        )

        list_value_for_compare = self._context.get('list_value_for_compare', False)
        if list_value_for_compare:
            product_product_values = list_value_for_compare[1]
        else:
            raise ValidationError(_("None Require context"))

        warehouse_orderpoint = self.env['stock.warehouse.orderpoint']
        product_product = self.env['product.product']

        product_product_item = product_product_values.get(
            template_line['default_code'],
            False
        )

        if product_product_item:

            product_id = product_product.browse(
                product_product_item['product_product_id']
            )

            warehouse_orderpoint_id = warehouse_orderpoint.search([
                ('product_id', '=', product_id.id),
                ('branch_id', '=', pos_branch_id.id),
            ], limit=1)

            warehouse_orderpoint_dict = self.map_dict_for_create_warehouse_orderpoint(
                template_line
            )

            str_log = ''.join([
                'update on stock.warehouse.orderpoint',
                product_id.product_tmpl_id.name,
                template_line['default_code']
            ])

            if product_id:
                if warehouse_orderpoint_id:
                    if warehouse_orderpoint_id.transferdate != template_line['transferdate']:
                        _logger.info(str_log)
                        warehouse_orderpoint_id.write(
                            warehouse_orderpoint_dict
                        )
                        self.env.cr.commit()
                else:
                    if pos_branch_id:
                        _logger.info(str_log)
                        warehouse_orderpoint_dict.update({
                            'warehouse_id': pos_branch_id.warehouse_id.id,
                            'location_id': pos_branch_id.warehouse_id.lot_stock_id.id,
                            'product_id': product_id.id,
                            'branch_id': pos_branch_id.id,
                            'company_id': pos_branch_id.pos_company_id.id,
                        })

                        warehouse_orderpoint.create(warehouse_orderpoint_dict)

                        self.env.cr.commit()

