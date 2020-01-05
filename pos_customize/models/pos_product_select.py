# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PosProductTemplate(models.Model):
    _inherit = 'pos_product.template'

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        required=False,
        compute='compute_branch_id',
    )

    @api.multi
    def compute_branch_id(self):
        for record in self:
            if not all([
                record.id,
            ]):
                continue

            template_id = self.env['pos.config'].search([('pos_product_template_id', '=', record.id)], limit=1)
            if template_id and len(template_id):
                record.branch_id = template_id.branch_id
            else:
                continue

    @api.multi
    def _update_branch_product(self, type):
        product_product_ids = []

        branch_obj = self.env['pos.branch'].search([('requisition_product_template_ids', '=', self.id)])

        for line in branch_obj:
            if type == "write":
                product_template_obj = self.env['pos.product.template.line'].search(
                    [('template_id', 'in', line.requisition_product_template_ids.ids)]
                )
            elif type == "unlink":
                product_template_obj = self.env['pos.product.template.line'].search(
                    [('template_id', 'in', line.requisition_product_template_ids.ids),
                     ('template_id', '<>', self.id)]
                )

            for line2 in product_template_obj:
                product_product_ids.extend(line2.product_id.ids)

            product_product_ids = list(set(product_product_ids))

            line.branch_product_ids = [(6, 0, [])]
            line.branch_product_ids = product_product_ids

        self.clear_caches()

    @api.multi
    def write(self, vals):
        res = super(PosProductTemplate, self).write(vals)

        self._update_branch_product("write")

        return res

    @api.multi
    def unlink(self):
        self._update_branch_product("unlink")

        res = super(PosProductTemplate, self).unlink()

        return res

    def map_dict_for_create_product_supplierinfo(self, template_line, pos_branch_id, vendor_id):
        temp = {
            'branch_id': pos_branch_id.id,
            'transferdate': template_line['transferdate'],
            'min_qty': template_line['minpurqty'],
            'price': template_line['purchaseprice'],
            'name': vendor_id.id,
            'delay': 1,
        }

        return temp

    def create_update_template_line(self, template_line, pos_product_template_id, pos_branch_id):
        super(PosProductTemplate, self).create_update_template_line(
            template_line,
            pos_product_template_id,
            pos_branch_id
        )

        list_value_for_compare = self._context.get('list_value_for_compare', False)
        if list_value_for_compare:
            product_product_values = list_value_for_compare[1]
        else:
            raise ValidationError(_("None Require context"))

        res_partner = self.env['res.partner']
        product_supplierinfo = self.env['product.supplierinfo']
        product_product = self.env['product.product']

        product_product_item = product_product_values.get(
            template_line['default_code'],
            False
        )

        if product_product_item:

            product_id = product_product.browse(
                product_product_item['product_product_id']
            )

            vendor_id = res_partner.search([
                ('supplier', '=', True),
                ('vat', '=', '0107551000134')
            ], limit=1)

            product_supplierinfo_id = product_supplierinfo.search([
                ('product_tmpl_id', '=', product_id.product_tmpl_id.id),
                ('company_id', '=', pos_branch_id.pos_company_id.id),
                ('name', '=', vendor_id.id),
                ('branch_id', '=', pos_branch_id.id),
            ], limit=1)

            product_supplierinfo_dict = self.map_dict_for_create_product_supplierinfo(
                template_line, pos_branch_id, vendor_id
            )

            str_log = ''.join([
                'update on product_supplierinfo',
                product_id.product_tmpl_id.name,
                template_line['default_code']
            ])

            if product_supplierinfo_id:
                if product_supplierinfo_id.transferdate != template_line['transferdate']:
                    _logger.info(str_log)
                    product_supplierinfo_id.write(
                        product_supplierinfo_dict
                    )
                    self.env.cr.commit()
            else:
                if pos_branch_id:
                    _logger.info(str_log)
                    product_supplierinfo_dict.update({
                        'product_tmpl_id': product_id.product_tmpl_id.id,
                        'company_id': pos_branch_id.pos_company_id.id,
                    })

                    product_supplierinfo.create(product_supplierinfo_dict)

                    self.env.cr.commit()


class PosProductTemplateLine(models.Model):
    _inherit = 'pos.product.template.line'

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        related='template_id.branch_id',
        string="Branch",
        required=False,
    )

    price = fields.Float(
        string="Price",
        required=False,
        default=0,
        compute='compute_price_by_branch_ids',
    )

    @api.multi
    def compute_price_by_branch_ids(self):
        branch_ids = []
        product_ids = []
        dict_by_product_id = {}

        for record in self:
            if record.branch_id and record.branch_id.id not in branch_ids:
                branch_ids.append(record.branch_id.id)
            product_ids.append(record.product_id_int)

        if not all([
            branch_ids,
            len(branch_ids)
        ]):
            return

        for branch_id in branch_ids:
            dict_by_product_id[branch_id] = {}
            prices = self.env['product.product'].read_price_by_product_ids(product_ids, branch_id, False, False)
            for price in prices:
                dict_by_product_id[branch_id][price['id']] = price['price']

        for record in self:
            if all([
                record.branch_id,
                record.branch_id.id in dict_by_product_id,
            ]):
                record.price = dict_by_product_id[record.branch_id.id][record.product_id.id]
            else:
                record.price = 0

        del dict_by_product_id, prices


class SuppliferInfo(models.Model):
    _inherit = "product.supplierinfo"

    def _default_branch(self):
        return self.env.user.branch_id

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        required=True,
        default=_default_branch,
    )

    updateon = fields.Datetime(
        'UpDateOn'
    )

    transferdate = fields.Datetime(
        'TransferDate'
    )
