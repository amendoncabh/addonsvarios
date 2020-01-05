# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models
from odoo import fields

_logger = logging.getLogger(__name__)


class OFMRequestReverse(models.TransientModel):
    _name = "ofm.request.reverse.reject"

    reason_reject = fields.Char(
        'Reason Reject',
        required=True
    )

    @api.multi
    def action_confirm(self):
        ofm_request_reverse = self.env['ofm.request.reverse']
        for record in self:
            active_id = record._context.get('active_id', False)
            if active_id:
                request_reverse = ofm_request_reverse.browse(active_id)
                request_reverse.update({
                    'reason_reject': record.reason_reject
                })
                request_reverse.action_reject_reverse_picking()
