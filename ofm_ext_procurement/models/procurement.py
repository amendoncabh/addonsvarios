# -*- coding: utf-8 -*-

from collections import defaultdict
from psycopg2 import OperationalError

from odoo import api, fields, models, registry, _
from odoo.exceptions import except_orm
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    def _default_branch(self):
        return self.env.user.branch_id

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        default=_default_branch,
    )

    def _get_stock_move_values(self):
        res = super(ProcurementOrder, self)._get_stock_move_values()
        res.update({
            'branch_id': self.branch_id.id,
        })
        return res
