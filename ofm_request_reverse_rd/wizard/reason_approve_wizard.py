# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil import relativedelta
from odoo.exceptions import except_orm
import json
import time
import sets

from collections import OrderedDict
import odoo
from odoo import fields, osv
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo import SUPERUSER_ID, api, models
import odoo.addons.decimal_precision as dp
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OFMRequestReverse(models.TransientModel):
    _name = "ofm.request.reverse.approve"

    rtv_type = fields.Selection(
        selection=[
            # ('change', 'Re-Delivery'),
            ('cn', 'Credit Note')
        ],
        string='RTV Type',
        required='True',
        default='cn'
    )

    @api.multi
    def action_confirm(self):
        ofm_request_reverse = self.env['ofm.request.reverse']
        for record in self:
            active_id = record._context.get('active_id', False)
            if active_id:
                request_reverse = ofm_request_reverse.browse(active_id)
                request_reverse.update({
                    'rtv_type': record.rtv_type
                })
                request_reverse.action_approve_reverse_picking()


