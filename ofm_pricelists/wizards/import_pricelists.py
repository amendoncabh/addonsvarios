# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from StringIO import StringIO
from odoo.exceptions import except_orm
from pandas import ExcelFile


class ImportPricelists(models.TransientModel):
    _name = 'import.pricelists.wizard'
    _description = "Import Pricelists"

    binary_data = fields.Binary(
        string="CSV File",
        required=True,
    )

    filename = fields.Char(
        string="File Name",
        required=False,
    )

    @api.multi
    def action_import_pricelists(self):
        for item in self:
            active_id = item._context['active_id']
            pricelists_obj = item.env[item._context['active_model']]
            product_obj = item.env['product.product']
            data = StringIO(item.binary_data.decode('base64'))
            xls = ExcelFile(data)
            data = xls.parse(xls.sheet_names[0])
            pricelists_dict = data.to_dict()

            for running in range(0, len(pricelists_dict['PID'])):
                pid = str(pricelists_dict['PID'][running]).zfill(7)
                price_inc_vat = pricelists_dict['Price (Inc. Vat)'][running]
                product_id = product_obj.search([('default_code', '=', pid)]).id

                if not product_id:
                    raise except_orm(_('PID does not exist: %r') % (pid,))
                if not pid or not price_inc_vat:
                    raise except_orm(_('Some PID or Price have empty text.'))

                pricelists_obj.pricelists_line_ids.create({
                    'pricelists_id': active_id,
                    'product_id': product_id,
                    'price_inc_vat': price_inc_vat,
                })

        return {'type': 'ir.actions.act_window_close'}
