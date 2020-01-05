from odoo import api, models, fields
from odoo.exceptions import except_orm
from odoo.tools.translate import _


class PurchaseOrderWizard(models.TransientModel):
    _name = 'purchase.order.wizard'

    message_alert = fields.Char(
        string='Message Alert',
        readonly=True
    )

    @api.multi
    def button_confirm(self):
        for rec in self:
            purchase_order_id = self.env[rec._context.get('active_model')].browse(rec._context.get('active_id'))
            ofm_purchase_order_header_id = purchase_order_id.call_action_send_pr_header()

            if len(ofm_purchase_order_header_id.ofm_purchase_order_ids.ids) > 1:
                return ofm_purchase_order_header_id.action_view_pr_po()


class PurchaseOrderProductIncorrectWizard(models.TransientModel):
    _name = 'purchase.order.product.incorrect.wizard'

    order_id = fields.Integer(
        string='Purchase Order ID',
    )

    ofm_order_line_no_stock_col = fields.One2many(
        comodel_name='ofm.purchase.order.line',
        string='No Stock COL',
        compute='compute_get_no_stock_col',
    )

    ofm_order_line_no_stock_col_delete = fields.One2many(
        comodel_name='ofm.purchase.order.line',
        string='No Stock COL',
        compute='compute_get_no_stock_col',
    )

    ofm_order_line_product_status_not_match = fields.One2many(
        comodel_name='ofm.purchase.order.line',
        string='Status Not Match COL',
        compute='compute_get_product_status_not_match',
    )

    ofm_order_line_product_status_not_match_delete = fields.One2many(
        comodel_name='ofm.purchase.order.line',
        string='Status Not Match COL',
        compute='compute_get_product_status_not_match',
    )

    ofm_order_line_product_more_than_stock = fields.One2many(
        comodel_name='ofm.purchase.order.line',
        string='QTY More than Stock COL',
        compute='compute_get_product_more_than_stock',
        readonly=False,
    )

    product_incorrect_edit_qty_ids = fields.One2many(
        comodel_name='purchase.order.product.incorrect.edit.qty.wizard',
        inverse_name='product_incorrect_id',
        string='Product Incorrect Edit Qty Ids'
    )

    is_hide_confirm = fields.Boolean(
        string='is Show Confirm',
        default=True,
        compute='compute_check_hide_confirm',
    )

    is_delete_no_stock = fields.Boolean(
        string='Delete',
        default=False,
    )

    is_delete_not_match = fields.Boolean(
        string='Delete',
        default=False,
    )

    is_change_product_qty = fields.Boolean(
        string='Change Product Qty',
        default=False,
    )

    def get_ofm_order_lines_product_incorrect(self):
        if self.order_id:
            condition_product = ''
            if self._context.get('is_no_stock', False):
                condition_product = """
                    and coalesce(product_qty_available, 0) = 0
                    and coalesce(product_status_correct, False) = True
                """
            elif self._context.get('is_not_match', False):
                condition_product = """
                    and coalesce(product_status_correct, False) = False
                """
            elif self._context.get('is_more_than_stock', False):
                condition_product = """
                    and product_qty > product_qty_available
                    and coalesce(product_qty_available, 0) > 0
                    and coalesce(product_status_correct, False) = True
                """

            query_string = """
                                select id
                                from ofm_purchase_order_line
                                where order_id = %s
                                    %s
                            """ % (self.order_id, condition_product)

            self.env.cr.execute(query_string)
            query_result = self.env.cr.dictfetchall()

            ofm_order_line_ids = []

            for item in query_result:
                ofm_order_line_ids.append(item['id'])

            if len(ofm_order_line_ids) > 0:
                ofm_order_line_ids = self.env['ofm.purchase.order.line'].search([
                    ('id', 'in', ofm_order_line_ids)
                ])
            else:
                ofm_order_line_ids = False

            return ofm_order_line_ids
        else:
            return False

    @api.multi
    @api.depends('order_id')
    def compute_get_no_stock_col(self):
        for rec in self:
            if rec:
                context = dict(rec._context)
                context.update({
                    'is_no_stock': True,
                })

                rec.ofm_order_line_no_stock_col = rec.with_context(context).get_ofm_order_lines_product_incorrect()

    @api.multi
    @api.depends('order_id')
    def compute_get_product_status_not_match(self):
        for rec in self:
            if rec:
                context = dict(rec._context)
                context.update({
                    'is_not_match': True,
                })

                rec.ofm_order_line_product_status_not_match = rec.with_context(context).get_ofm_order_lines_product_incorrect()

    @api.multi
    @api.depends('order_id')
    def compute_get_product_more_than_stock(self):
        for rec in self:
            if rec:
                context = dict(rec._context)
                context.update({
                    'is_more_than_stock': True,
                })

                rec.ofm_order_line_product_more_than_stock = rec.with_context(
                    context).get_ofm_order_lines_product_incorrect()

    @api.multi
    @api.depends('is_delete_no_stock', 'is_delete_not_match', 'is_change_product_qty')
    def compute_check_hide_confirm(self):
        for rec in self:
            is_hide_confirm = True

            if any([
                all([
                    rec.is_delete_no_stock,
                    rec.ofm_order_line_no_stock_col,
                ]),
                all([
                    rec.is_delete_not_match,
                    rec.ofm_order_line_product_status_not_match,
                ]),
                rec.is_change_product_qty,
            ]):
                is_hide_confirm = False

            rec.is_hide_confirm = is_hide_confirm

    @api.onchange('ofm_order_line_product_more_than_stock')
    def onchange_product_more_than_stock(self):
        self.is_change_product_qty = True

    @api.multi
    def button_confirm(self):
        for rec in self:
            if rec.is_delete_no_stock:
                rec.ofm_order_line_no_stock_col.unlink()

            if rec.is_delete_not_match:
                rec.ofm_order_line_product_status_not_match.unlink()

            if rec.is_change_product_qty:
                for edit_qty_id in rec.product_incorrect_edit_qty_ids:
                    ofm_order_line_id = rec.env['ofm.purchase.order.line'].browse(edit_qty_id.ofm_order_line_id)
                    ofm_order_line_id.update({
                        'product_qty': edit_qty_id.product_qty
                    })
                    ofm_order_line_id.onchange_calculate_amount()

            order_id = rec.env['purchase.order'].browse(rec.order_id)
            order_id.onchange_is_hide_product_incorrect()
            order_id._amount_all_ofm()


class PurchaseOrderProductIncorrectEditQtyWizard(models.TransientModel):
    _name = 'purchase.order.product.incorrect.edit.qty.wizard'

    product_incorrect_id = fields.Many2one(
        comodel_name='purchase.order.product.incorrect.wizard',
        string='Product Incorrect ID'
    )

    ofm_order_line_id = fields.Integer(
        string='OFM Order Line ID'
    )

    product_qty = fields.Float(
        string='Product Qty'
    )