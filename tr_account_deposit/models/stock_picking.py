# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import except_orm

class StockPicking(models.Model):
    """Stock Picking"""
    _inherit = "stock.picking"

    def create_invoice(self, sp_obj):
        invoice_ids = super(StockPicking, self).create_invoice(sp_obj)
        if invoice_ids and len(invoice_ids):
            for invoice_id in invoice_ids:
                so_id = invoice_id.so_id
                if all([
                    invoice_id.state == 'open',
                    so_id,
                    so_id.sale_payment_type == 'credit',
                    len(so_id.credit_note_ids)
                ]):
                    for credit_note_id in so_id.credit_note_ids:
                        credit_note_id.update({
                            'parent_invoice_id': invoice_id.id
                        })
                        credit_note_id.reconcile_refund()
        return invoice_ids
