# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import except_orm
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    account_move_id = fields.Many2one(
        comodel_name="account.move",
        compute='_get_move_id',
        string="Stock Journal",
        required=False,
        store=True,
    )

    picking_type_code = fields.Selection(
        string="",
        required=False,
        related='picking_type_id.code'
    )

    return_reason_id = fields.Many2one(
        comodel_name="return.reason",
        string="Reason",
        required=False,
    )

    usage_src_location = fields.Selection(
        string='Source Location Type',
        related='location_id.usage',
        readonly=True
    )
    usage_dest_location = fields.Selection(
        string='Destination Location Type',
        related='location_dest_id.usage',
        readonly=True
    )
    date_done = fields.Datetime(
        'Date Done',
        copy=False,
        help="Completion Date of Transfer",
        required=True,
        default=fields.Datetime.now
    )

    @api.multi
    @api.depends('state')
    def _get_move_id(self):
        for picking in self:
            account_move_ids = self.env['account.move'].search([('ref', '=', picking.name)])
            if account_move_ids:
                picking.account_move_id = account_move_ids[0].id

    @api.multi
    def print_goods_receive_note(self):
        return self.env['report'].get_action(self, 'receive.doc.report.jasper')

    @api.multi
    def action_update_stock_move_date_to_now(self):
        date_time = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        for record in self:
            record.move_lines.write({
                'date': date_time,
            })
        self.write({
            'date': date_time,
        })

    @api.multi
    def create_cn(self, sp_obj):
        account_inv_refund_obj = sp_obj.env['account.invoice.refund']
        ctx = dict(account_inv_refund_obj._context)
        po_inv_ids = []
        inv_line_ids = []
        inv_id = False
        type_purchase_ofm = False

        for stock_move in sp_obj.move_lines:
            for origin_stock_move in stock_move.origin_returned_move_id:
                for po_line in origin_stock_move.purchase_line_id:
                    for inv_line in po_line.invoice_lines:
                        po_inv_ids.append({'invoice_id': inv_line.id,
                                           'qty': stock_move.product_qty,
                                           'move_line_id': stock_move.id})
                        inv_id = inv_line.invoice_id.id
                        type_purchase_ofm = inv_line.invoice_id.type_purchase_ofm

        if sp_obj.sale_id and sp_obj.picking_type_id.code == 'incoming':
            ctx[u'active_ids'] = sp_obj.sale_id.invoice_ids.search([('origin', '=', sp_obj.sale_id.name)]).id
        elif inv_id and sp_obj.picking_type_id.code == 'outgoing':
            ctx[u'active_ids'] = inv_id
        elif sp_obj.sale_id and sp_obj.picking_type_id.code == 'outgoing':
            ctx[u'active_ids'] = sp_obj.sale_id.invoice_ids.search([('origin', '=', sp_obj.sale_id.name)]).id
        else:
            return False

        deposit_return_reason_id = self._context.get('return_reason_id', False)
        if deposit_return_reason_id:
            account_inv_refund_obj = account_inv_refund_obj.with_context(ctx).create({
                'return_reason_id': deposit_return_reason_id
            })
        else:
            account_inv_refund_obj = account_inv_refund_obj.with_context(ctx).create({
                'return_reason_id': sp_obj.return_reason_id.id
            })

        cn_info_obj = account_inv_refund_obj.invoice_refund()
        cn_obj = sp_obj.env['account.invoice'].search([('id', '=', cn_info_obj['new_cn_id'])])

        if self._context.get('skip_modify_cn', True):
            if sp_obj.sale_id:
                for stock_move in sp_obj.move_lines:
                    sale_line_id = stock_move.procurement_id.sale_line_id
                    cn_lines = cn_obj.invoice_line_ids.filtered(
                        lambda r: r.origin_inv_line_id == sale_line_id.invoice_lines.id
                    )
                    for cn_line in cn_lines:
                        inv_line_ids.append(cn_line.id)
                        cn_line.update({
                            'quantity': stock_move.product_uom_qty
                        })
            elif inv_id:
                for po_inv_id in po_inv_ids:
                    cn_lines = cn_obj.invoice_line_ids.filtered(
                        lambda r: r.origin_inv_line_id == po_inv_id['invoice_id']
                    )
                    for cn_line in cn_lines:

                        inv_line_ids.append(cn_line.id)
                        cn_line.update({
                            'quantity': po_inv_id['qty'],
                            'move_id': po_inv_id['move_line_id']
                        })
                        refund_account = cn_line.product_id.product_tmpl_id.categ_id.expense_refund_account
                        if refund_account:
                            cn_line.update({
                                'account_id': refund_account.id
                            })
                        else:
                            msg_error = """
                            Please Set Expense Refund Account in This Product Category '%s'
                            """ % cn_line.product_id.product_tmpl_id.categ_id.name
                            raise except_orm(_('Error!'), _(msg_error))
                        break
            cn_obj.update({
                'invoice_line_ids': [(6, 0, inv_line_ids)],
            })

        cn_obj.update({
            'picking_id': sp_obj.id,
            'type_purchase_ofm': type_purchase_ofm,
            'branch_id': self.branch_id.id,
            'so_id': sp_obj.sale_id.id if sp_obj.sale_id else False,
        })

        is_not_invoice_open_auto = self._context.get('is_not_invoice_open_auto', True)
        if is_not_invoice_open_auto == False:
            if self._context.get('is_replace_origin', True):
                cn_obj.update({
                    'origin': sp_obj.sale_id.name,
                })
            # Update CN State=paid and origin=so_name
            active_id = self._context.get('active_id', False)
            active_model = self._context.get('active_model', False)
            if active_id and active_model == 'account.deposit':
                cn_obj.update({
                    'deposit_ids': [(6, 0, [self._context.get('active_id', False)])],
                })

        cn_obj._onchange_invoice_line_ids()
        cn_obj._compute_amount()

        if cn_obj.so_id and is_not_invoice_open_auto:
            cn_obj.action_invoice_open()
            # in-store --> manual reconcile
            # drop ship --> auto reconcile when payment type = credit term and SI (parent invoice) state is not paid
            if all([
                cn_obj.so_id.type_sale_ofm,
                cn_obj.parent_invoice_id,
                cn_obj.parent_invoice_id.state == 'open',
                cn_obj.so_id.sale_payment_type == 'credit'
            ]):
                cn_obj.reconcile_refund()
        return cn_obj

    def create_invoice(self, sp_obj):
        so_obj = self.env['sale.order'].search(
            [
                ('name', '=', sp_obj.origin),
                ('invoice_status', '<>', 'invoiced')
            ]
        )

        if so_obj:
            sale_adv_payment_obj = sp_obj.env['sale.advance.payment.inv']
            ctx = dict(sale_adv_payment_obj._context)

            ctx[u'active_ids'] = sp_obj.sale_id.ids
            sale_adv_payment_obj = sale_adv_payment_obj.with_context(ctx).create({
                'advance_payment_method': 'all'
            })

            sale_adv_payment_obj.create_invoices()
            invoice_ids = self.env['account.invoice'].search([('so_id', 'in', sp_obj.sale_id.ids)], limit=1)
            is_not_invoice_open_auto = self._context.get('is_not_invoice_open_auto', True)
            if invoice_ids:
                if is_not_invoice_open_auto:
                    invoice_ids.action_invoice_open()
                return invoice_ids

    def _create_extra_moves(self):
        super(StockPicking, self)._create_extra_moves()
        return None

    @api.onchange('date_done')
    def _onchange_date_done(self):

        max_previous_month = self.env['stock.config.settings'].search([], order="id desc", limit=1).max_previous_month
        now_month = int(datetime.strftime(datetime.now(), "%m"))
        now_year = int(datetime.strftime(datetime.now(), "%Y"))
        check_month = now_month - max_previous_month
        date_done = datetime.strptime(self.date_done, "%Y-%m-%d %H:%M:%S")

        if check_month <= 0:
            month = check_month + 12
            year = now_year - 1
        else:
            month = check_month
            year = now_year

        if self.date_done:
            date_done_month = int(datetime.strftime(date_done, "%m"))
            date_done_year = int(datetime.strftime(date_done, "%Y"))

            datetoday = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")

            if self.date_done > str(datetoday) or \
                    year > date_done_year or (year == date_done_year and month > date_done_month):
                self.date_done = str(datetoday)

    def check_move_lines_amount(self, vals):
        vals_move_lines = vals.get('move_lines', False)
        if vals_move_lines:
            vals_move_lines_amount = 0
            for move_line_id in vals_move_lines:
                if move_line_id[0] == 2:
                    vals_move_lines_amount += 1
                else:
                    vals_move_lines_amount -= 1

            if vals_move_lines_amount == len(self.move_lines.ids):
                raise except_orm(_('Error!'), _("Cannot be saved because no product."))

        return vals

    @api.multi
    def do_transfer(self):
        for rec in self:
            rec.action_update_stock_move_date_to_now()
            res = super(StockPicking, rec).do_transfer()

            rec.update({
                'date_done': datetime.now(),
            })

            return res

    @api.multi
    def write(self, vals):
        for rec in self:
            rec.check_move_lines_amount(vals)

            res = super(StockPicking, self).write(vals)

            return res


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    branch_id = fields.Many2one(
        comodel_name='pos.branch',
        compute='get_branch',
        store=True
    )

    @api.depends('warehouse_id')
    @api.multi
    def get_branch(self):
        for item in self:
            item.branch_id = item.env['pos.branch'].search([
                ('warehouse_id', '=', item.warehouse_id.id)
            ]).id

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if 'branch_id' in self.env.context:
            branch = self.env['pos.branch'].browse(self.env.context.get('branch_id'))
            picking_type_list = self.search(
                [
                    ('warehouse_id', '=', branch.warehouse_id.id)
                ] + args,
                limit=limit
            )
            if name:
                name = name.upper()
                picking_type_list = picking_type_list.filtered(
                    lambda x: name in x.name.upper()
                )
            return picking_type_list.sudo().name_get()
        return super(PickingType, self).name_search(name, args, operator, limit)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _default_group_id(self):
        res = super(StockMove, self)._default_group_id()

        if not res:
            group_id = self._context.get('group_id', False)

            if group_id:
                return group_id
            else:
                return False

    group_id = fields.Many2one(
        comodel_name='procurement.group',
        string='Procurement Group',
        default=_default_group_id
    )


