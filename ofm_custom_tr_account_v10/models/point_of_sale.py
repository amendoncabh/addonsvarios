# -*- coding: utf-8 -*-
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_account_move_dict(self, dt, ref, journal_id, company_id):
        date_tz_user = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(dt))
        date_tz_user = fields.Date.to_string(date_tz_user)
        branch_id = self._context.get('branch_id', False)
        return {
            'branch_id': branch_id,
            'ref': ref,
            'journal_id': journal_id,
            'date': date_tz_user
        }

    def _create_account_move(self, dt, ref, journal_id, company_id):
        value = self._prepare_account_move_dict(dt, ref, journal_id, company_id)
        return self.env['account.move'].sudo().create(value)