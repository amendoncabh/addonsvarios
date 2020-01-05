# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo import api, fields, models, _
from datetime import datetime

class CycleCountByDeptReport(models.TransientModel):
    _name = 'internal.use.report'

    company_id = fields.Many2one(
        'res.company',
        string = 'Company',
        required = True
    )
    branch_id = fields.Many2one(
        'pos.branch',
        string = 'Branch',
        domain="[('pos_company_id', '=', company_id)]",
        required = True
    )
    parent_dept_ofm = fields.Many2one(
        comodel_name='ofm.product.dept',
        string='Dept OFM',
        domain=[
            ('dept_parent_id', '=', False),
        ],
        translate=True,
    )
    sub_dept_ids = fields.Many2many(
        'ofm.product.dept',
        string = 'Product Sub Dept',
        domain=[
            ('dept_parent_id', '!=', False),
        ],
        translate=True,
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Product'
    )
    start_date = fields.Date(
        string = 'Start Date',
        default = fields.Datetime.now()
    )
    end_date = fields.Date(
        string = 'End Date',
        default = fields.Datetime.now()
    )
    type = fields.Selection([
        ('xls', 'Excel'),
        ('pdf', 'PDF')
    ],
    default = 'pdf'
    )

    @api.multi
    def action_print(self, data):
        self.ensure_one()
        records = []
        report_name = "internal.use.report.pdf.jasper" if self.type == 'pdf' else "internal.use.report.xls.jasper"

        # Send parameter to print
        params = {
            'start_date': self.start_date,
            'end_date': self.end_date
        }
        if self.company_id:
            params.update({'company_id': str(self.company_id.id)})
        if self.branch_id:
            params.update({'branch_id': str(self.branch_id.id)})
        if self.sub_dept_ids:
            sub_dept = [l.ofm_sub_dept_id for l in self.sub_dept_ids]
            params.update({'sub_dept_ids': ','.join(map(str, sub_dept))})
        if self.product_ids:
            params.update({'product_ids': ','.join(map(str, self.product_ids.ids))})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }

        return res
    
    @api.onchange('branch_id','company_id','parent_dept_ofm')
    def set_dept_ofm(self):
        self.sub_dept_ids = False
        query_parent_dept_ofm = ''

        if all([
            self.parent_dept_ofm,
            not self.sub_dept_ids,
        ]):
            query_parent_dept_ofm = """
                and dept_parent_id = %s
            """ % self.parent_dept_ofm.id

        query_string = """
            select min(id) as id
            from ofm_product_dept
            where dept_parent_id is not null
            %s
            group by name
        """ % query_parent_dept_ofm

        self.env.cr.execute(query_string)
        result_model = self.env.cr.dictfetchall()

        sub_dept_ids = []

        for result in result_model:
            sub_dept_ids.append(result['id'])

        dept_ofm_domain = [
            ('dept_parent_id', '!=', False),
            ('id', 'in', sub_dept_ids)
        ]

        return {
            'domain': {
                'sub_dept_ids': dept_ofm_domain
            },
        }
