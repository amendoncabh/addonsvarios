from odoo import models, api


class IrRule(models.Model):
    _inherit = "ir.rule"

    @api.model
    def delete_rule_sale_order_see_all(self):
        sale_order_see_all_rule_ref = self.env.ref('sale.sale_order_see_all', False)

        if sale_order_see_all_rule_ref is not None:
            sale_order_see_all_rule_id = self.env['ir.rule'].search([
                ('id', '=', sale_order_see_all_rule_ref.id)
            ])

            if sale_order_see_all_rule_id:
                sale_order_see_all_rule_id.unlink()

        sale_order_line_see_all_rule_ref = self.env.ref('sale.sale_order_line_see_all', False)

        if sale_order_line_see_all_rule_ref is not None:
            sale_order_line_see_all_rule_id = self.env['ir.rule'].search([
                ('id', '=', sale_order_line_see_all_rule_ref.id)
            ])

            if sale_order_line_see_all_rule_id:
                sale_order_line_see_all_rule_id.unlink()

        sale_order_personal_rule_ref = self.env.ref('sale.sale_order_personal_rule', False)

        if sale_order_personal_rule_ref is not None:
            sale_order_personal_rule_ref_id = self.env['ir.rule'].search([
                ('id', '=', sale_order_personal_rule_ref.id)
            ])

            if sale_order_personal_rule_ref_id:
                sale_order_personal_rule_ref_id.unlink()

        sale_order_line_personal_rule_ref = self.env.ref('sale.sale_order_line_personal_rule', False)

        if sale_order_line_personal_rule_ref is not None:
            sale_order_line_personal_rule_ref_id = self.env['ir.rule'].search([
                ('id', '=', sale_order_line_personal_rule_ref.id)
            ])

            if sale_order_line_personal_rule_ref_id:
                sale_order_line_personal_rule_ref_id.unlink()