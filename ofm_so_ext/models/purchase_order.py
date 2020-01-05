# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.exceptions import except_orm, UserError
from odoo import fields, models, _, api
from odoo.tools import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sales Order No.',
        readonly=True
    )

    amount_delivery_fee_special = fields.Monetary(
        string='Amount Delivery Fee Special',
        track_visibility='always',
    )

    amount_delivery_fee_by_order = fields.Monetary(
        string='Amount Delivery Fee By Order',
        track_visibility='always',
    )

    is_hide_action_get_invoice_for_sale = fields.Boolean(
        string='Hide Action Get Invoice for Sale',
        reaonly=True,
        defualt=True,
        compute='compute_hide_action_get_invoice_for_sale',
    )

    @api.multi
    @api.depends('state')
    def compute_hide_action_get_invoice_for_sale(self):
        for rec in self:
            is_hide_action_get_invoice_for_sale = True

            if any([
                all([
                    rec.state == 'completed',
                    rec.type_to_ofm == 'customer',
                ]),
                all([
                    rec.state == 'purchase',
                    rec.type_to_ofm == 'customer',
                    not rec.vendor_cn_reference,
                ])
            ]):
                is_hide_action_get_invoice_for_sale = False

            rec.is_hide_action_get_invoice_for_sale = is_hide_action_get_invoice_for_sale

    def get_purchase_order_header(self, sale_order_id):
        default_vendor = self.env['ir.config_parameter'].search([('key', '=', 'prs_default_vendor')]).value
        partner_id = self.partner_id.search([('vat', '=', default_vendor)]).id
        picking_type_id = self.get_picking_type(sale_order_id.company_id.id, sale_order_id.branch_id.id)
        picking_type_id = picking_type_id.id if picking_type_id else False

        purchase_order_header = {
            'state': 'draft',
            'type_purchase_ofm': True,
            'type_to_ofm': 'customer',
            'partner_id': partner_id,
            'date_order': datetime.now(),
            'company_id': sale_order_id.company_id.id,
            'branch_id': sale_order_id.branch_id.id,
            'sale_order_id': sale_order_id.id,
            'amount_delivery_fee_special': sale_order_id.amount_delivery_fee_special,
            'amount_delivery_fee_by_order': sale_order_id.amount_delivery_fee_by_order,
            'picking_type_id': picking_type_id,
        }

        return purchase_order_header

    def get_purchase_order_detail(self, sale_order_id):
        ofm_purchase_order_line = []

        for order_line_id in sale_order_id.order_line:
            if (order_line_id.product_id.type != 'service') and \
                    (not order_line_id.is_line_discount_delivery_promotion):
                taxes = order_line_id.product_id.supplier_taxes_id
                taxes_id = taxes
                if taxes_id:
                    taxes_id = taxes_id.filtered(lambda x: x.company_id.id == sale_order_id.company_id.id)

                ofm_purchase_order_line.append([
                    0,
                    False,
                    {
                        'account_analytic_id': False,
                        'date_planned': datetime.now(),
                        'name': order_line_id.product_id.name,
                        'price_unit': 0,
                        'product_id': order_line_id.product_id.id,
                        'product_qty': order_line_id.product_uom_qty,
                        'product_uom': order_line_id.product_uom.id,
                        'taxes_id': [[6, False, taxes_id.ids]],
                        'state': 'draft',
                        'delivery_fee_ofm': order_line_id.delivery_fee_ofm,
                        'is_best_deal_promotion': order_line_id.is_best_deal_promotion,
                        'is_promotion': order_line_id.promotion,
                        'is_free': order_line_id.promotion,
                    }
                ])

        return ofm_purchase_order_line

    def get_cn_from_staging_for_sale(self):
        cn_result = self.get_cn_from_staging()
        cn_header = cn_result.get('inv_header', {})
        cn_detail = cn_result.get('inv_detail', {})

        if all([
            len(cn_header) > 0,
            len(cn_detail) > 0,
        ]):
            rd_origin_id = self.picking_ids.filtered(
                lambda picking_rec: picking_rec.state == 'done'
                and not picking_rec.get_picking_type_return()
                and picking_rec.reverse_invisible is False
                and picking_rec.origin == self.name
            )

            if rd_origin_id:
                rt_id = self.create_return_picking_by_auto_action(
                    rd_origin_id,
                    cn_detail
                )

                if rt_id:
                    rt_account_inv_id = self.action_validate_invoice_open(rt_id)
                else:
                    rt_account_inv_id = False

                return {
                    'rt_id': rt_id,
                    'rt_account_inv_id': rt_account_inv_id,
                    'cn_header': cn_header,
                    'cn_detail': cn_detail,
                }
        else:
            return False

    def create_purchase_order_by_sale_order(self):
        sale_order_id = self._context.get('sale_order_id', False)

        if sale_order_id:
            purchase_order_header = self.get_purchase_order_header(sale_order_id)
            purchase_order_detail = self.get_purchase_order_detail(sale_order_id)

            if all([
                len(purchase_order_header) > 0,
                len(purchase_order_detail) > 0,
            ]):
                purchase_order_header.update({
                    'ofm_purchase_order_line_ids': purchase_order_detail,
                })

                po_id = self.create(purchase_order_header)

                for order_line_id in po_id.ofm_purchase_order_line_ids:
                    order_line_id._onchange_quantity()

                    if order_line_id.is_promotion:
                        order_line_id.update({
                            'price_unit': 0,
                            'is_free': True,
                        })
                    elif order_line_id.price_unit <= 0:
                        order_line_id.update({
                            'price_unit': order_line_id.product_id.find_product_price_in_dropship(),
                            'is_free': False,
                        })

                    order_line_id.onchange_product_status_name_abb()
                    order_line_id.onchange_product_uom_show()
                    order_line_id.onchange_price_unit_show()
                    order_line_id.onchange_date_planned_show()
                    order_line_id.onchange_calculate_amount()

                po_id._compute_date_planned()
                po_id.onchange_get_order_line_date_plan()
                po_id._amount_all_ofm()

                return po_id
            else:
                raise except_orm(_('Error!'), _(u"No data for create Purchase Request"))

    def create_return_picking_by_auto_action(self, picking_origin_id, ofm_cn_detail):

        ctx = dict(self._context)
        ctx.update({
            'active_id': picking_origin_id.id,
            'active_model': picking_origin_id._name,
            'is_force_assign': True,
        })

        if picking_origin_id.sale_id:
            sale_id = picking_origin_id.sale_id

            account_invoice = self.env['account.invoice']
            stock_picking = self.env['stock.picking']

            return_reason_value = self.env['ir.config_parameter'].search([
                ('key', '=', 'so_auto_return_reason'),
            ]).value

            domain = [
                ('name', '=', return_reason_value),
                ('model', '=', 'purchase.order'),
            ]
            return_reason_id = self.env['return.reason'].search(domain, limit=1)
            order_lines = []
            for line in ofm_cn_detail:
                line_id = sale_id.order_line.filtered(
                    lambda x: line[2]['product_id'] == x.product_id.id
                )
                if line_id:
                    order_lines.append({
                        'qty': line[2]['product_qty'],
                        'id': line_id.id
                    })
                free_line_id = sale_id.order_line.filtered(
                    lambda x: line[2]['product_id'] == x.free_product_id.id
                )
                if free_line_id:
                    order_lines.append({
                        'qty': line[2]['product_qty'] * -1,
                        'id': free_line_id.id
                    })

            ctx.update({
                'order_id': sale_id.id,
                'return_reason_id': return_reason_id.id,
                'return_approver_id': 1,
                'return_approve_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'order_lines': order_lines,
                'call_request_reverse': False
            })

            return_picking_id = sale_id.with_context(ctx).return_so_from_ui()

            return_picking_id = stock_picking.browse(
                return_picking_id['return_picking_id']
            )

        else:
            return_picking_id = self.env['stock.return.picking'].with_context(ctx).create_return_picking_from_dict(
                picking_origin_id,
                ofm_cn_detail
            )

            return_picking_id.action_confirm()
            ofm_request_reverse_id = return_picking_id.with_context(ctx).action_request_reverse()
            ofm_request_reverse_id.update({
                'rtv_type': 'cn'
            })
            ofm_request_reverse_id.action_approve_reverse_picking()
            self.action_confirm_stock_immediate_transfer(return_picking_id)

        return return_picking_id

    def create_bsr_from_action_auto_bsr(self, ofm_cn_detail):
        so_id = self.sale_order_id

        if so_id:
            bdl_origin_id = so_id.picking_ids.filtered(
                lambda bdl_rec: bdl_rec.state == 'done'
                and not bdl_rec.get_picking_type_return()
                and bdl_rec.origin == so_id.name
            )

            if bdl_origin_id:
                bsr_id = self.create_return_picking_by_auto_action(
                    bdl_origin_id,
                    ofm_cn_detail
                )

                return bsr_id

        return False

    def action_confirm_stock_immediate_transfer(self, picking_id):
        stock_immediate_transfer_id = self.env['stock.immediate.transfer'].action_confirm_stock_immediate_transfer(
            picking_id
        )
        return stock_immediate_transfer_id

    def action_validate_invoice_open(self, picking_id):
        account_inv_obj = self.env['account.invoice']
        account_inv_id = account_inv_obj.search([
            ('picking_id', '=', picking_id.id),
            ('state', '=', 'draft'),
        ])

        if account_inv_id:
            account_inv_id._compute_invisible_get_cn()

            if account_inv_id.hide_action_get_cn:
                account_inv_id.action_invoice_open()
            else:
                account_inv_id.action_get_cn_from_staging()

            return account_inv_id

    def create_so_cn_from_different(self, so_id, so_invoice_id, diff_dict):
        if not so_invoice_id:
            so_invoice_id = self.env['account.invoice'].search(
                [('so_id', '=', so_id.id), ('origin', '=', so_id.name)])
        return_reason_value = self.env['ir.config_parameter'].get_param('so_auto_return_reason')
        return_reason_id = self.env['return.reason'].search([
            ('name', '=', return_reason_value),
            ('model', '=', 'purchase.order'),
        ])

        account_inv_refund_obj = self.env['account.invoice.refund'].create({
            'return_reason_id': return_reason_id.id,
        })

        cn_info_obj = account_inv_refund_obj.with_context({
            'active_ids': so_invoice_id.id
        }).invoice_refund()
        cn_obj = self.env['account.invoice'].search([('id', '=', cn_info_obj['new_cn_id'])])

        so_id.modify_cn_from_dict(cn_obj, diff_dict)
        cn_obj.action_invoice_open()

        if cn_obj.state == 'open' and so_id.sale_payment_type != 'credit':
            self.env['account.payment'].create_payment_from_account_invoice(cn_obj)

    def check_different_between_so_and_dict(self, so_id, so_invoice_id, dict_product):
        # check different from so
        diff_dict = dict()
        discount_product = self.env['pos.config'].search([
            ('branch_id', '=', self.branch_id.id)
        ], limit=1).promotion_discount_product_id
        for line in so_id.order_line:
            # filter out the delivery fee
            if line.is_type_delivery_by_order or line.is_type_delivery_special:
                continue
            diff = 0
            product_id = line.product_id.id
            sign = 1
            if line.product_id.id == discount_product.id:
                product_id = line.free_product_id.id
                sign = -1

            if product_id in dict_product:
                if line.product_uom_qty != dict_product[product_id]:
                    diff = abs(line.product_uom_qty) - abs(dict_product[product_id])
            else:
                diff = line.product_uom_qty

            if diff != 0:
                if not (line.invoice_lines and line.invoice_lines.id):
                    raise UserError(_('There is no invoice line'))
                diff_dict[line.invoice_lines.id] = {
                    'line': line,
                    'qty': diff * sign,
                }

        # bdl_id because bdl_id is not done yet
        # if len(so_id.deposit_ids) and diff_dict and len(diff_dict):
        if diff_dict and len(diff_dict):
            self.create_so_cn_from_different(so_id, so_invoice_id, diff_dict)

    def action_auto_validate_bdl_si_from_get_invoice(self):
        if self.type_to_ofm == 'customer':
            account_inv_obj = self.env['account.invoice']

            so_id = self.sale_order_id
            if so_id:
                if so_id.deposit_ids:
                    deposit_id = so_id.deposit_ids.filtered(
                        lambda deposit_id_rec: deposit_id_rec.state != 'cancel'
                    )
                    if deposit_id.state not in ('open', 'paid', 'cancel'):
                        deposit_id.deposit_open()
                        deposit_id.env.cr.commit()

            #Validate RD State Available for create invoice and change state invoice
            po_rd_picking_id = self.picking_ids.filtered(
                lambda picking_rec: picking_rec.state == 'assigned'
                and not picking_rec.get_picking_type_return()
            )

            if po_rd_picking_id:
                po_rd_picking_id.action_update_stock_move_date_to_now()
                self.action_confirm_stock_immediate_transfer(po_rd_picking_id)
                po_account_inv_id = self.action_validate_invoice_open(po_rd_picking_id)

            #Validate BDL, before validate BDL check must be check invoice of purchase order

            if so_id:
                purchase_order_ids = so_id.purchase_order_ids.filtered(
                    lambda pr: pr.state not in ['cancel']
                )

                amount_purchase_order = len(purchase_order_ids.ids)
                count_purchase_order_have_invoice = 0

                dict_product = dict()
                for purchase_order_id in purchase_order_ids:
                    if purchase_order_id.invoice_ids:
                        count_purchase_order_have_invoice += 1
                    # get all product qty from po line
                    for line in purchase_order_id.order_line:
                        if line.product_id.id in dict_product:
                            dict_product[line.product_id.id] += line.product_qty
                        else:
                            dict_product[line.product_id.id] = line.product_qty

                if amount_purchase_order == count_purchase_order_have_invoice:
                    so_invoice_id = self.env['account.invoice']

                    bdl_id = so_id.picking_ids.filtered(
                        lambda picking_rec: picking_rec.state in ['confirmed', 'assigned', 'partially_available']
                        and not picking_rec.get_picking_type_return()
                    )

                    if bdl_id:
                        #Check state:'confirmed' to assigned For Create pack_operation_product_ids
                        if not bdl_id.pack_operation_product_ids or bdl_id.state in ['confirmed', 'partially_available']:
                            bdl_id.force_assign()

                        # edit To Do:product_qty to Qty Move: qty_real on stock operate
                        is_need_edit = False
                        for pack_id in bdl_id.pack_operation_product_ids:
                            product_qty = dict_product.get(pack_id.product_id.id, 0)
                            if product_qty:
                                if product_qty != pack_id.product_qty or product_qty != pack_id.qty_real:
                                    is_need_edit = True
                            else:
                                is_need_edit = True

                        if is_need_edit:
                            bdl_id_state = bdl_id.state
                            bdl_id.write({'state': 'confirmed'})
                            for pack_id in bdl_id.pack_operation_product_ids:
                                product_qty = dict_product.get(pack_id.product_id.id, 0)
                                if product_qty:
                                    if product_qty != pack_id.product_qty or product_qty != pack_id.qty_real:
                                        pack_id.write({
                                            'product_qty': product_qty,
                                            'qty_real': product_qty,
                                        })
                                        move_ids = pack_id.linked_move_operation_ids.mapped('move_id')
                                        move_ids.write({
                                            'product_uom_qty': product_qty,
                                        })
                                else:
                                    move_ids = pack_id.linked_move_operation_ids.mapped('move_id')
                                    move_ids.write({'state': 'draft'})
                                    move_ids.unlink()
                                    pack_id.unlink()

                            bdl_id.write({'state': bdl_id_state})
                        bdl_id.action_update_stock_move_date_to_now()
                        stock_immediate_transfer_id = self.action_confirm_stock_immediate_transfer(bdl_id)
                        if stock_immediate_transfer_id:
                            bdl_id.action_update_stock_move_date_to_now()
                            so_invoice_id = self.action_validate_invoice_open(bdl_id)

                        if is_need_edit:
                            self.check_different_between_so_and_dict(so_id, so_invoice_id, dict_product)

                    else:
                        bdl_id = so_id.picking_ids.filtered(
                            lambda picking_rec: picking_rec.state == 'done'
                        )
                        if bdl_id:
                            so_invoice_id = self.action_validate_invoice_open(bdl_id)

                    return so_invoice_id

        return False

    def action_auto_validate_bsr_cn_from_get_invoice(self, result_get_cn):
        if self.type_to_ofm == 'customer':
            rt_id = result_get_cn.get('rt_id', False)
            rt_account_inv_id = result_get_cn.get('rt_account_inv_id', False)
            ofm_cn_detail = result_get_cn.get('cn_detail', False)

            if all([
                rt_id,
                rt_account_inv_id,
            ]):
                bsr_id = self.create_bsr_from_action_auto_bsr(ofm_cn_detail)

                if bsr_id:
                    bsr_account_inv_id = self.action_validate_invoice_open(bsr_id)
                else:
                    bsr_account_inv_id = False

            return bsr_account_inv_id

    @api.model
    def get_purchase_dropship_for_get_invoice_by_cron(self):
        order_ids = self.search(
            [
                ('sale_order_id', '!=', False),
                ('state', 'in', ('completed', 'purchase'))
            ]
        )

        ctx = dict(self._context)
        ctx.update({
            'is_get_by_cron': True,
            'tracking_disable': True,
        })

        for order_id in order_ids:
            try:
                _logger.info("purchase_order : " + order_id.name)
                ctx.update({
                    'force_company': order_id.company_id.id,
                    'company_id': order_id.company_id.id,
                })
                order_id.with_context(ctx).action_get_invoice_from_staging_for_sale()
            except Exception as e:
                _logger.error("purchase_order : " + order_id.name + e.message)

    @api.multi
    def action_get_invoice_from_staging_for_sale(self):
        for rec in self:
            if rec.type_to_ofm == 'customer':
                ctx = dict(rec._context)
                ctx.update({
                    'is_not_sent_cn': True,
                    'tracking_disable': True,
                })

                result_get_cn = None

                so_id = rec.sale_order_id
                if so_id:
                    if so_id.deposit_ids:
                        deposit_id = so_id.deposit_ids.filtered(
                            lambda deposit_id_rec: deposit_id_rec.state != 'cancel'
                        )
                        if deposit_id.state not in ('open', 'paid', 'cancel'):
                            deposit_id.deposit_open()
                            deposit_id.env.cr.commit()

                if not rec.vendor_invoice_no:
                    #Get Invoice
                    rec.with_context(ctx).action_get_invoice_from_staging()

                if rec.vendor_invoice_no:
                    #Validate BDL
                    rec.action_auto_validate_bdl_si_from_get_invoice()

                    #Check CN
                    result_get_cn = rec.with_context(ctx).get_cn_from_staging_for_sale()

                    #Validate BSR
                    if result_get_cn:
                        rec.with_context(ctx).action_auto_validate_bsr_cn_from_get_invoice(result_get_cn)

                if result_get_cn:
                    rtv_id = result_get_cn.get('rt_account_inv_id', False)
                    rt_id = result_get_cn.get('rt_id', False)

                    if rtv_id:
                        if rtv_id.move_name and 'RTV-' in rtv_id.number:
                            rtv_id.update({
                                'reference': rtv_id.reference.replace('RT-', 'ART-'),
                                'number': rtv_id.number.replace('RTV-', 'R-'),
                                'tax_number': rtv_id.tax_number.replace('RTV-', 'R-'),
                            })

                    if rt_id:
                        if rt_id.name and 'RT-' in rt_id.name:
                            rt_id.update({
                                'name': rt_id.name.replace('RT-', 'ART-')
                            })

                    rec.env.cr.commit()
            else:
                return False

            return True

    @api.multi
    def action_cancel_from_sale(self):
        for rec in self:
            rec.button_cancel()

            for invoice_id in rec.invoice_ids:
                invoice_id.action_invoice_cancel()

            for picking_id in rec.picking_ids:
                picking_id.action_cancel()


class PurchaseOrderLine(models.Model):
    _inherit = 'ofm.purchase.order.line'

    is_promotion = fields.Boolean(
        string='Is Promotion',
        readonly=True,
        default=False,
    )

    is_free = fields.Boolean(
        string='IsFree',
        readonly=True,
        default=False,
    )


