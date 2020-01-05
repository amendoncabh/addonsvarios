# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo import api, fields, models, _
from odoo import SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)

class AccountAccountTemplate(models.Model):
    _inherit = "account.account.template"

    chart_template_id = fields.Many2one(
        'account.chart.template',
        string='Chart Template',
        required=True,
        help="This optional field allow you to link an account template to a specific chart template that may differ from the one its root parent belongs to. This allow you "
                                             "to define chart templates that extend another and complete it with few new accounts (You don't need to define the whole structure that is common to both several times)."
    )

