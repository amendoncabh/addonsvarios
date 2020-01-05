# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class ResCurrency(models.Model):

    _inherit = "res.currency"

    rounding = fields.Float(
        'Rounding Factor',
        digits=(12, 12)
    )

    @api.multi
    def round(self, amount):
        """Return ``amount`` rounded  according to ``self``'s rounding rules.

           :param float amount: the amount to round
           :return: rounded float
        """
        # TODO: Need to check why it calls round() from sale.py, _amount_all() with *No* ID after below commits,
        # https://github.com/odoo/odoo/commit/36ee1ad813204dcb91e9f5f20d746dff6f080ac2
        # https://github.com/odoo/odoo/commit/0b6058c585d7d9a57bd7581b8211f20fca3ec3f7
        # Removing self.ensure_one() will make few test cases to break of modules event_sale, sale_mrp and stock_dropshipping.
        # self.ensure_one()
        return tools.float_round(amount, precision_rounding=self.env.ref('pos_customize.trinity_currency').rounding)
