# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from StringIO import StringIO
from odoo.exceptions import except_orm
import pandas as pd
from pandas import ExcelFile
import tempfile
import math
from odoo.exceptions import ValidationError, UserError



class ImportCounted(models.TransientModel):
    _name = 'import.counted.wizard'
    _description = "Import counted quatity of product"

    binary_data = fields.Binary(
        string="CSV File",
        required=True,
    )

    filename = fields.Char(
        string="File Name",
        required=False,
    )

    @api.multi
    def action_import_counted(self, data):
        for item in self:
            cycle_count_id = item.env[data['active_model']].browse(data['active_id'])
            file_path = tempfile.gettempdir()+'/file.xlsx'
            dataset = item.binary_data
            f = open(file_path,'wb')
            f.write(dataset.decode('base64'))
            f.close()
            xls = pd.read_excel(file_path, converters={'product_code': str})
            counted_dict = xls.to_dict()
            try:
                check_col = counted_dict['product_code']
            except Exception as e:
                        raise UserError(
                            "Import Unsuccessful!!!!\n\nReason : Column name '%s' is not contain in this file" % e.message)
            
            for running in range(0, len(counted_dict['product_code'])):
                try:
                    product_code = counted_dict['product_code'].values()[running]
                    product_qty = counted_dict['product_qty'].values()[running]
                except Exception as e:
                        raise UserError(
                            "Import Unsuccessful!!!!\n\nReason : Column name '%s' cannot be found." % e.message)
                if not (math.isnan(product_qty)):
                    line = item.env['stock.inventory.cycle.count.line'].search([
                        ('inventory_id', '=', cycle_count_id.id),
                        ('product_code', '=', product_code)
                    ])
                    if line:
                        line.write({
                            'product_qty': product_qty
                        })
                        line.onchange_product_qty()
                    else:
                        raise UserError(
                                    "Import Unsuccessful!!!!\n\nReason : product_code '%s' cannot be found." % product_code)

            cycle_count_id.import_cal_fee()

            
            