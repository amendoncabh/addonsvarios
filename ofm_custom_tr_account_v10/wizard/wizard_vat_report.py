# -*- coding: utf-8 -*-
import base64
import locale
import sys
from cStringIO import StringIO
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api

reload(sys)
sys.setdefaultencoding('utf8')
try:
    import xlwt
except ImportError:
    xlwt = None


class WizardVatReport(models.TransientModel):
    _inherit = "wizard.vat.report"

    def _default_branch(self):
        branch_id = self._context.get('branch_id', False)
        if branch_id:
            return branch_id
        return self.env.user.branch_id

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        require=True,
        default=_default_branch
    )

    @api.onchange('company_id')
    def _onchange_compnay_id(self):
        if self.company_id and self.branch_id:
            self.branch_id = False

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.branch_id:
            self.company_id = self.branch_id.pos_company_id.id

    @api.multi
    def print_report_pdf(self, data):
        branch_id = self.branch_id.id
        res = super(WizardVatReport, self).print_report_pdf(data)
        res['datas']['parameters'].update({
            'branch_id': str(branch_id)
        })
        return res
