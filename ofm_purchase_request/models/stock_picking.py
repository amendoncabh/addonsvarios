# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from pytz import timezone

from odoo import api, models, _
from odoo.exceptions import except_orm

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def do_transfer(self):
        for rec in self:
            for pack_operation_product_id in rec.pack_operation_product_ids:
                if pack_operation_product_id.qty_real < pack_operation_product_id.qty_done:
                    raise except_orm(_('Error!'), 'Qty Done > Qty To Do')
        super(StockPicking, self).do_transfer()
        for record in self:
            picking_group_ids = record.get_picking_by_group()
            picking_current_ids = picking_group_ids.get('picking_current_ids', False)
            po_id = record.env['purchase.order'].search([
                ('name', '=', record.group_id.name)
            ])
            is_add_rd_after_vendor_reference = False

            if picking_current_ids:
                if len(picking_current_ids) > 1:
                    is_add_rd_after_vendor_reference = True

            if record.usage_src_location == 'supplier' and record.usage_dest_location == 'internal':
                if po_id:
                    ctx = dict(record._context)
                    ctx.update({
                        'picking_id_current': record.id,
                        'picking_name_current': record.name,
                        'is_add_rd_after_vendor_reference': is_add_rd_after_vendor_reference
                    })
                    po_id.with_context(ctx).create_vender_bill()

            elif record.usage_src_location == 'internal' and record.usage_dest_location == 'supplier':
                cn_id = record.env['account.invoice'].search([
                    ('picking_id', '=', record.id)
                ])
                type_purchase_ofm = cn_id.type_purchase_ofm
                if type_purchase_ofm:
                    if cn_id.reference:
                        reference = cn_id.reference
                    else:
                        reference = po_id.vendor_invoice_no

                    reference = reference if reference else ''
                    reference += '_'
                    reference += record.name

                    cn_id.update({
                        'reference': reference
                    })

                    if not cn_id.vendor_invoice_date:
                        cn_id.update({
                            'vendor_invoice_date': po_id.vendor_invoice_date
                        })

                    tr_call_api = record.env['tr.call.api']

                    if not record._context.get('is_not_sent_cn', False):
                        if record.rtv_type == 'cn':
                            if cn_id:
                                tr_call_api.call_api_create_rtv(record, cn_id)
                            else:
                                raise except_orm(_('Error!'), 'Do not have CN')
                        else:
                            cn_id.unlink()
                            tr_call_api.call_api_create_rtv(record, False)

        return True

    def prepare_order_line(self, rt_order_line, purchase_order):
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

            if self.rtv_type == 'cn':
                qty = int(line.quantity)
                unitprice = line.price_unit
            elif self.rtv_type == 'change':
                qty = int(line.qty_done)
                unitprice = po_order_line.get(line.product_id.id)

            invoice_line.append({
                'rtno': self.name,
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
