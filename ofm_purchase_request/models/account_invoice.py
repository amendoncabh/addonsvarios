# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import except_orm
from odoo.tools import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    hide_action_get_cn = fields.Boolean(
        string='Hide Action Get CN',
        compute='_compute_invisible_get_cn',
        readonly=True,
    )

    hide_field_vendor_cn = fields.Boolean(
        string='Hide Field Vendor CN',
        compute='_compute_invisible_field_vendor_cn',
        readonly=True,
    )

    vendor_cn_reference = fields.Char(
        string='Vendor CN',
        readonly=1,
    )
    vendor_cn_date = fields.Datetime(
        string='Vendor CN Date',
        readonly=1,
    )

    def _prepare_invoice_line_from_po_line(self, line):
        data = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)

        move_id = line.move_ids.filtered(
            lambda rec: rec.picking_id.id == self._context.get('picking_id_current', False)
        ).id

        data.update({
            'move_id': move_id
        })

        return data

    @api.multi
    @api.depends('state')
    def _compute_invisible_field_vendor_cn(self):
        for rec in self:
            if rec.type == 'in_refund' \
                    and rec.type_purchase_ofm:
                rec.hide_field_vendor_cn = False
            else:
                rec.hide_field_vendor_cn = True

    @api.multi
    @api.depends('state')
    def _compute_invisible_get_cn(self):
        for rec in self:
            if all([
                rec.state == 'draft',
                rec.type_purchase_ofm,
                rec.type == 'in_refund',
                not rec.vendor_cn_reference
            ]):
                rec.hide_action_get_cn = False
            else:
                rec.hide_action_get_cn = True

    def get_cn_form_staging_by_cron(self):
        rtv_ids = self.search([
            ('state', '=', 'draft'),
            ('vendor_cn_reference', '=', False),
            ('type_purchase_ofm', '=', True)
        ])

        ctx = dict(self._context)
        ctx.update({
            'is_get_by_cron': True
        })

        for rtv_id in rtv_ids:
            try:
                _logger.info("account_invoice_reference : " + rtv_id.reference)
                rtv_id.with_context(ctx).action_get_cn_from_staging()
            except Exception as e:
                _logger.error("account_invoice_reference : " + rtv_id.reference + e.message)

    @api.multi
    def action_get_cn_from_staging(self):
        for rec in self:
            is_get_by_cron = rec._context.get('is_get_by_cron', False)

            if rec.state == 'draft':
                purchase_order_id = False

                for po_invoice_line_id in rec.invoice_line_ids:
                    if po_invoice_line_id.purchase_id:
                        purchase_order_id = po_invoice_line_id.purchase_id
                        break

                if purchase_order_id:
                    cn_result = purchase_order_id.get_cn_from_staging()
                    cn_header = cn_result.get('inv_header', {})
                    cn_detail = cn_result.get('inv_detail', {})
                else:
                    if not is_get_by_cron:
                        raise except_orm(_('Error!'), 'No Purchase Order.')
                    else:
                        _logger.error('No Purchase Order.')

                if all([
                    len(cn_header) > 0,
                    len(cn_detail) > 0,
                ]):
                    is_detail_match = True

                    if not rec._context.get('is_not_sent_cn', False):
                        cn_product_ofm = {}

                        for cn_detail_id in cn_detail:
                            cn_product_id = cn_detail_id[2].get('product_id', False)
                            cn_product_qty = cn_detail_id[2].get('product_qty', False)
                            cn_product_ofm.update({
                                cn_product_id: cn_product_qty,
                            })

                        if all([
                            len(rec.invoice_line_ids.ids) > 0,
                            len(cn_product_ofm) > 0,
                            len(rec.invoice_line_ids.ids) == len(cn_product_ofm),
                        ]):
                            for invoice_line_id in rec.invoice_line_ids:
                                invoice_product_id = invoice_line_id.product_id.id
                                invoice_product_qty = invoice_line_id.quantity

                                cn_product_ofm_qty = cn_product_ofm.get(invoice_product_id, False)

                                if cn_product_ofm_qty:
                                    if invoice_product_qty != cn_product_ofm_qty:
                                        is_detail_match = False
                                        break
                                else:
                                    is_detail_match = False
                                    break
                        else:
                            is_detail_match = False

                    if is_detail_match:
                        rec.update({
                            'vendor_cn_reference': cn_header.get('vendor_invoice_no', False),
                            'vendor_cn_date': cn_header.get('vendor_invoice_date', False),
                        })

                        purchase_order_id.update({
                            'vendor_cn_reference': cn_header.get('vendor_invoice_no', False),
                            'vendor_cn_date': cn_header.get('vendor_invoice_date', False),
                        })

                        rec.action_invoice_open()
                    else:
                        if not is_get_by_cron:
                            raise except_orm(_('Error!'), 'Product in RTV not match product in Credit Note COL.')
                        else:
                            _logger.error('Product in RTV not match product in Credit Note COL.')
                else:
                    if not is_get_by_cron:
                        raise except_orm(_('Error!'), 'No Credit Note.')
                    else:
                        _logger.error('No Credit Note.')

        return True
