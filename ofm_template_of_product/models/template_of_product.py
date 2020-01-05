# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class TemplateOfProduct(models.Model):
    _name = "template.of.product"
    _description = "Template of Product"

    name = fields.Char(
        string = 'Name'
    )
    company_id = fields.Many2one(
        'res.company',
        string = 'Company',
        required = True
    )
    dept_ids = fields.One2many(
        'template.of.product.line',
        'template_id',
        string = 'Dept'
    )


class TemplateOfProductLine(models.Model):
    _name = "template.of.product.line"
    _description = "Template of Product Line"

    template_id = fields.Many2one(
        'template.of.product',
        string = 'Template',
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
    dept_id = fields.Many2one(
        'ofm.product.dept',
        string = "Sub Dept",
        domain="[('dept_parent_id', '!=', False)]",
        required = True
    )
    brand_id = fields.Many2one(
        'product.brand',
        'Brand'
    )

    @api.onchange('parent_dept_ofm')
    def set_dept_ofm(self):
        self.dept_id = False

        query_parent_dept_ofm = ''

        if all([
            self.parent_dept_ofm,
            not self.dept_id,
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
                'dept_id': dept_ofm_domain
            },
        }