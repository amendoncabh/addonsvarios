# -*- coding: utf-8 -*-

from odoo import api, fields, models
from openerp.exceptions import UserError


class PointTemplate(models.Model):
    _name = 'point.template'
    _order = 'id desc'

    name = fields.Char(
        string="Name",
    )

    branch_ids = fields.Many2many(
        'pos.branch',
        "point_template_branch",
        string = "Branch",
    )

    point_template_line_ids = fields.One2many(
        'point.template.line',
        'point_template_id',
        string = "Point Template Line ID",
        help = """These are all the point template lines 
        related to this point template""",
    )

    exchange_rate = fields.Float(
        string = 'Exchange Rate',
        help = """The exchange rate for conversion from points to THB"""
    )

    @api.onchange('exchange_rate')
    def onchange_exchange_rate(self):
        exchange_rate = self.exchange_rate
        if exchange_rate < 0:
            reset_value_source = self.point_template_line_ids
            if isinstance(reset_value_source[0].id, int):
                self.exchange_rate = reset_value_source[0].exchange_rate
            else:
                self.exchange_rate = 0
            self.env.user.notify_warning(
                "Warning",
                "Value should be greater than zero.",
            )            
        else:
            point_template_lines = self.point_template_line_ids
            if point_template_lines:
                for line in point_template_lines:
                    amount = line.points * exchange_rate
                    line.exchange_rate = exchange_rate
                    line.amount = amount


class PointTemplateLine(models.Model):
    _name = 'point.template.line'
    _order = 'points asc'

    point_template_id = fields.Many2one(
        'point.template',
        string = "Point Template ID",
        ondelete = "cascade",
        readonly = True,
    )

    points = fields.Integer(
        string = 'Points',
    )

    exchange_rate = fields.Float(
        string = 'Exchange Rate',
        compute="compute_amount", 
        store=True,
    )

    amount = fields.Float(
        string = 'Amount',
        compute="compute_amount", 
        store=True,
        help="""Currency equivalent calculated from points"""
    )

    @api.depends('points')
    @api.multi
    def compute_amount(self):
        for record in self:
            if record.points < 0:
                record.points = 0
                self.env.user.notify_warning(
                    "Warning",
                    "Value should be greater than zero.",
                ) 
            else:
                record.exchange_rate = record.point_template_id.exchange_rate
                record.amount = record.points * record.point_template_id.exchange_rate