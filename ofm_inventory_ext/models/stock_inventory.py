# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.inventory"
    _order = "id desc"

    @api.onchange('name')
    def onchange_location_from_user(self):
        res = {}
        user = self.env.user
        group_id = self.env.ref('base.group_system').id
        if group_id not in user.groups_id.ids:
            user = self.env['res.users'].browse(self.env.user.id)
            ids = [
                user.pos_config.branch_id.warehouse_id.wh_shelf_stock_loc_id.id,
                user.pos_config.stock_location_id.id,
                user.pos_config.stock_location_id.location_id.id,
                user.pos_config.stock_location_id.location_id.location_id.id,
            ]
            domain = [("id", "in", ids), ('usage', 'not in', ['supplier', 'production'])]
        else:
            domain = [('usage', 'not in', ['supplier', 'production'])]
        return {'domain': {'location_id': domain}}

    number = fields.Char(
        string="No.",
        required=False,
        default='Draft',
        readonly=True,
    )

    account_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Stock Journal",
        required=False
    )

    location_id = fields.Many2one(
        required=True,
        default=False,
    )

    company_id = fields.Many2one(
        required=True,
        default=lambda self: self.env.user.company_id,
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        required=True,
        readonly=True,
        index=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user.branch_id,
    )

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.branch_id = None

    @api.onchange('branch_id')
    def _onchange_company_id(self):
        self.location_id = None

    def get_aj_no(self):
        if not all([
            self.branch_id,
            self.branch_id.warehouse_id,
        ]):
            return 'Draft'

        ctx = dict(self._context)
        ctx.update({'res_model': 'stock.inventory'})

        prefix = 'AJ-' + self.branch_id.branch_code + '%(y)s%(month)s'
        aj_no = self.branch_id.with_context(ctx).next_sequence(self.date, prefix, 5) or '/'
        return aj_no

    @api.multi
    def action_done(self):
        ctx = dict(self.env.context)
        ctx.update({
            'branch_id': self.branch_id.id,
        })
        result = super(StockMove, self.with_context(ctx)).action_done()
        self.write({
            'number': self.get_aj_no(),
        })
        return result


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        related="inventory_id.branch_id"
    )

    def _get_move_values(self, qty, location_id, location_dest_id):
        self.ensure_one()
        values = super(InventoryLine, self)._get_move_values(qty, location_id, location_dest_id)
        if not self.branch_id:
            raise ValueError("No branch on stock inventory line")
        values.update({
            'branch_id': self.branch_id.id
        })
        return values

