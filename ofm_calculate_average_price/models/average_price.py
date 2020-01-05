# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AveragePrice(models.Model):
    _name = 'average.price'
    _description = "Average Price"

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        required=False,
        index=False
    )

    pos_id = fields.Many2one(
        comodel_name="pos.order",
        string="POS ID",
        required=False,
        index=False
    )

    po_id = fields.Many2one(
        comodel_name="purchase.order",
        string="PO ID",
        required=False,
        index=False
    )

    so_id = fields.Many2one(
        comodel_name="sale.order",
        string="SO ID",
        required=False,
        index=False
    )

    sa_id = fields.Many2one(
        comodel_name="stock.inventory",
        string="SA ID",
        required=False,
        index=False
    )

    int_id = fields.Many2one(
        comodel_name="ofm.stock.internal.move",
        string="INT ID",
        required=False,
        index=False
    )

    stock_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Stock Location",
        required=False,
        index=False
    )

    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Ref Document No",
        required=False,
        index=False
    )

    move_id = fields.Many2one(
        comodel_name="stock.move",
        string="Move ID",
        required=False,
        index=False
    )

    move_type = fields.Char(
        string="Move Type",
        required=False,
    )

    doc_no = fields.Char(
        string="Document No",
        required=False,
        compute='_get_document_no'
    )

    move_date = fields.Datetime(
        string="Move Date",
        required=False,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product Name",
        required=False,
        index=False
    )

    product_uom_id = fields.Many2one(
        comodel_name="product.uom",
        string="Product UOM",
        required=False,
        index=False
    )

    product_uom_qty = fields.Integer(
        string="QTY",
        required=False,
    )

    move_amount = fields.Float(
        string="Move Amount",
        required=False,
    )

    price = fields.Float(
        string="Price",
        required=False,
    )

    remain_product_qty = fields.Integer(
        string="Remain Product QTY",
        required=False,
    )

    remain_product_amount = fields.Float(
        string="Remain Product Amount",
        required=False,
    )

    product_average_price = fields.Float(
        string="Product Average Price",
        required=False,
    )

    cost = fields.Float(
        string="Cost",
        required=False,
    )

    @api.multi
    def _get_document_no(self):
        for record in self:
            if record.pos_id:
                if record.pos_id.invoice_id:
                    record.doc_no = record.pos_id.invoice_id.number
                else:
                    record.doc_no = record.pos_id.inv_no
            elif record.po_id:
                if record.po_id.invoice_ids:
                    if record.move_type == 'PO':
                        for item in record.po_id.invoice_ids:
                            if item.type == 'in_invoice':
                                record.doc_no = item.number
                                break
                    else:
                        for item in record.po_id.invoice_ids:
                            if item.type == 'in_refund':
                                record.doc_no = item.number
                                break
            elif record.so_id:
                if record.so_id.invoice_ids:
                    if record.move_type == 'SO':
                        for item in record.so_id.invoice_ids:
                            if item.type == 'out_invoice':
                                if item.number:
                                    record.doc_no = item.number
                                    break
                                else:
                                    record.doc_no = record.so_id.name
                                    break
                    else:
                        for item in record.so_id.invoice_ids:
                            if item.type == 'out_refund':
                                record.doc_no = item.number
                                break
                else:
                    record.doc_no = record.so_id.name
            elif record.sa_id:
                record.doc_no = record.sa_id.number
            elif record.int_id:
                record.doc_no = record.int_id.name
