# -*- coding: utf-8 -*-

import re
from datetime import datetime

from odoo import api
from odoo import fields
from odoo import models, exceptions
from odoo.exceptions import except_orm
from odoo.tools.translate import _


class PosBranch(models.Model):
    _name = 'pos.branch'
    _order = "branch_code, id"
    _rec_name = 'branch_name'

    @api.model
    def _default_company_id(self):
        company = self.env.user.company_id.id
        return company

    @api.model
    def _default_sequence(self):
        self.env.cr.execute('select sequence from pos_branch order by sequence desc limit 1')
        sequence_returned = self.env.cr.fetchone()
        if sequence_returned:
            sequence_returned = sequence_returned[0] + 1
        else:
            sequence_returned = 0
        return sequence_returned

    @api.multi
    @api.depends('name', 'branch_name')
    def _get_name(self):
        for branch in self:
            branch.update({'name': branch.branch_name})

    def _default_nationality_id(self):
        return self.env.ref('base.th')

    nationality_id = fields.Many2one(
        'res.country',
        string='Nationality',
        default=_default_nationality_id,
        required=True,
    )

    name = fields.Char(
        compute='_get_name',
        string='Name',
        store=True
    )
    branch_name = fields.Char(
        string='Branch Name',
        required=True
    )
    ofin_code = fields.Char(
        string="Ofin Short Code",
        size=2,
    )
    street = fields.Char(
        'Address',
        related='partner_id.street',
        store=True,
        required=True
    )
    street2 = fields.Char(
        'Road',
        related='partner_id.street2',
        store=True,
        required=False
    )
    alley = fields.Char(
        string='Alley',
        related='partner_id.alley',
        store=True,
    )
    moo = fields.Char(
        string='Moo',
        related='partner_id.moo',
        store=True,
    )
    tambon_id = fields.Many2one(
        'tambon',
        related='partner_id.tambon_id',
        store=True,
        string='Tambon/Khwaeng',
        track_visibility='always',
        required=True,
    )
    amphur_id = fields.Many2one(
        'amphur',
        related='partner_id.amphur_id',
        store=True,
        string='Amphur/Khet',
        track_visibility='always',
        required=True,
    )
    province_id = fields.Many2one(
        'province',
        related='partner_id.province_id',
        store=True,
        string='Province',
        track_visibility='always',
        required=True,
    )
    zip_id = fields.Many2one(
        'zip',
        related='partner_id.zip_id',
        store=True,
        string='Zip',
        track_visibility='always',
        required=True,
    )
    zip = fields.Char(
        'Zip',
        size=24,
        change_default=True,
        required=False
    )
    city = fields.Char(
        'City',
        required=False
    )
    state_id = fields.Many2one(
        "res.country.state",
        related='partner_id.state_id',
        store=True,
        string='State',
        ondelete='restrict',
        required=False
    )
    country_id = fields.Many2one(
        'res.country',
        related='partner_id.country_id',
        store=True,
        string='Country',
        ondelete='restrict',
        required=False
    )
    email = fields.Char(
        'Email',
        related='partner_id.email',
        store=True,
    )
    phone = fields.Char(
        'Phone',
        related='partner_id.phone',
        store=True,
    )
    branch_id = fields.Char(
        'Branch ID',
        related='partner_id.shop_id',
        store=True,
        required=True,
        size=5,
    )
    branch_code = fields.Char(
        'Store Code',
        required=True,
        size=6,
    )
    pos_company_id = fields.Many2one(
        'res.company',
        'Company',
        default=_default_company_id,
        select=1,
        required=True,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        readonly=True,
    )
    sequence_tax_invoice_id = fields.Many2one(
        'ir.sequence',
        'Sequence Tax Invoice',
        copy=False
    )
    sequence_pos_picking_id = fields.Many2one(
        'ir.sequence',
        'Sequence Pos Picking',
        copy=False
    )
    warehouse_code = fields.Char(
        related='warehouse_id.code',
        string="Warehouse Code",
    )
    sequence = fields.Integer(
        'Sequence',
        default=_default_sequence,
        help="Gives the sequence order when displaying a list of product categories."
    )
    pos_config_product_template_id = fields.Many2one(
        'pos_product.template',
        'Pos Config Product Template',
        domain=[('check_active', '=', True)],
        copy=False,
    )
    requisition_product_template_ids = fields.Many2many(
        'pos_product.template',
        'requisition_product_template_rel',
        'rb_id',
        'template_id',
        'Requisition Branch Product Template',
        domain=[('check_active', '=', True)],
        copy=False,
    )
    cash_limit = fields.Float(
        string='Cash Limit',
    )

    branch_product_ids = fields.Many2many(
        'product.product',
        'branch_product_rel',
        'branch_id',
        'product_id',
        'Branch Product',
        domain=[('active', '=', True)],
        copy=False,
    )

    manager_user_ids = fields.Many2many(
        'res.users',
        'pos_branch_res_users_rel',
        'branch_id',
        'user_id',
        'POS Manager',
        copy=False,
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        readonly=True
    )

    @api.multi
    def name_get(self):
        return [(rec.id, "(%s %s)" % (rec.branch_name, rec.branch_code,)) for rec in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=160):
        company_id = self._context.get('company_id', False)
        if company_id:
            recs = self.search(
                [
                    ('pos_company_id', '=', company_id)
                ] + args,
                limit=limit
            )
            if name:
                name = name.upper()
                recs = recs.filtered(
                    lambda x: name in x.name.upper()
                )
            return recs.name_get()
        return super(PosBranch, self).name_search(name, args, operator, limit)

    @api.multi
    @api.depends('name', 'branch_name')
    def name_get(self):
        result = super(PosBranch, self).name_get()
        for branch_id in self:
            branch_id._get_name()
        return result

    @api.multi
    def _get_vals_product(self, vals):
        requisition_product_template_ids = vals.get('requisition_product_template_ids', False)
        product_product_ids = []

        if requisition_product_template_ids:
            product_template_obj = self.env['pos.product.template.line'].search(
                [('template_id', 'in', requisition_product_template_ids[0][2])]
            )

            for line in product_template_obj:
                product_product_ids.extend(line.product_id.ids)

            product_product_ids = list(set(product_product_ids))

            if product_product_ids:
                vals['branch_product_ids'] = [(6, 0, product_product_ids)]

        return vals

    def _check_code_repeat(self, branch_code):
        vat_repeat = self.search([
            ('id', '!=', self.id),
            ('branch_code', '=', branch_code),
        ])
        if vat_repeat:
            raise except_orm(_('Error!'), _(" Individual Store Code Can't Repeat "))

    @api.multi
    def action_create_partner_id(self):
        for record in self:
            is_create_company = record._context.get('is_create_company')
            if all([
                not record.partner_id,
                not is_create_company
            ]):
                res_partner = record.env['res.partner']
                fields = [
                    'street',
                    'street2',
                    'alley',
                    'moo',
                    'tambon_id',
                    'amphur_id',
                    'province_id',
                    'zip_id',
                    'city',
                    'state_id',
                    'country_id',
                    'email',
                    'phone',
                ]
                prepare_create_partner = {}

                prepare_create_partner.update({
                    'name': ' '.join([
                        record.pos_company_id.name,
                        record.name
                    ]),
                    'branch_id': record.id,
                    'company_type': 'company',
                    'shop_id': record.branch_id,
                    'vat': record.pos_company_id.partner_id.vat
                })

                for field in fields:
                    if record._fields.get(field).type == 'many2one':
                        prepare_create_partner.update({
                            field: record[field].id
                        })
                    elif record._fields.get(field).type not in ['one2many', 'many2many']:
                        prepare_create_partner.update({
                            field: record[field]
                        })
                partner_id = res_partner.create(prepare_create_partner)
                record.update({
                    'partner_id': partner_id.id
                })

    @api.model
    def create(self, vals):
        stock_warehouse = self.env['stock.warehouse']
        branch_id = vals.get('branch_id', False)
        branch_code = vals.get('branch_code', False)
        zip_id = vals.get('zip_id', False)

        if zip_id:
            vals['zip'] = self.env['zip'].search([
                ('id', '=', zip_id)
            ]).name

        if branch_id:
            vals['branch_id'] = branch_id.zfill(5)

        if branch_code:
            vals['branch_code'] = branch_code.zfill(6)

        self._check_code_repeat(vals['branch_code'])

        if vals.get('flag_create_company', False):
            stock_warehouse.check_access_rights('write')
            stock_warehouse.browse(vals['warehouse_id']).sudo(
                self.env.user.id
            ).write({
                'name': vals['branch_name'],
                'code': vals['branch_code'][-5:],
                'company_id': vals['pos_company_id'],
            })
        else:
            # mutli-company rules prevents creating warehouse and sub-locations
            stock_warehouse.check_access_rights('create')
            warehouse_id = stock_warehouse.sudo(
                self.env.user.id
            ).with_context({
                'branch_code': vals['branch_code']
            }).create({
                'name': vals['branch_name'],
                'code': vals['branch_code'][-5:],
                'company_id': vals['pos_company_id']
            }).id

            vals.update({
                'warehouse_id': warehouse_id
            })

        vals = self._get_vals_product(vals)

        res = super(PosBranch, self).create(vals)

        if vals.get('warehouse_id', False):
            picking_type_ids = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', vals.get('warehouse_id', False))
            ])
            for picking_type in picking_type_ids:
                picking_type.update({
                    'branch_id': res.id,
                })

        self.clear_caches()

        res.action_create_partner_id()

        return res

    def write(self, vals):
        for rec in self:
            branch_id = vals.get('branch_id', False)
            branch_code = vals.get('branch_code', False)
            zip_id = vals.get('zip_id', False)

            if zip_id:
                vals['zip'] = rec.env['zip'].search([
                    ('id', '=', zip_id)
                ]).name

            if branch_id:
                vals['branch_id'] = branch_id.zfill(5)

            if branch_code:
                branch_code = vals['branch_code'] = branch_code.zfill(6)

            if 'branch_code' in vals and vals.get('branch_code') or rec.branch_code:
                if 'branch_code' in vals and vals.get('branch_code'):
                    branch_code = vals.get('branch_code')
                elif rec.branch_code:
                    branch_code = rec.branch_code or False

            rec._check_code_repeat(branch_code)

            vals = rec._get_vals_product(vals)

            res = super(PosBranch, rec).write(vals)

            if len(rec.requisition_product_template_ids) == 0:
                vals['branch_product_ids'] = [(6, 0, [])]

                super(PosBranch, rec).write(vals)

            rec.clear_caches()

            return res

    @api.multi
    def onchange_state(self, state_id):
        if state_id:
            state = self.env['res.country.state'].browse(state_id)
            return {'value': {'country_id': state.country_id.id}}
        return {'value': {}}

    @api.multi
    def check_branch_code(self):
        if not self.branch_code:
            raise except_orm(_('Error!'), _(u" Please Set Store Code "))
        else:
            return True

    @api.multi
    def next_sequence(self, order_date=None, prefix=False, padding=0, not_sequence_id=True):
        if self.check_branch_code():
            branch_code = self.branch_code

        branch_sequence = self.branch_id
        branch_id = self.id

        if branch_code and branch_sequence:
            seq = self.env['pos.session.sequence'].search([
                ('branch_code', '=', branch_code),
                ('res_model', '=', self._context.get('res_model', 'pos.branch')),
            ], limit=1)
            if not seq:
                seq = self.create_sequence(branch_code, branch_id, padding, prefix)
        else:
            raise except_orm(_('Error!'), _('Can Not Create Because Not Have Sequence Or Not Set Branch'))

        if not_sequence_id:
            if not order_date:
                order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                return seq.sequence_id.with_context({'date': order_date}).next_by_id()
            else:
                return seq.sequence_id.with_context({'date': order_date}).next_by_id()
        else:
            return seq.sequence_id

    @api.multi
    def create_sequence(self, branch_code, branch_id, padding, prefix):
        ofm_seq_template = self.env.ref('pos_customize.ofm_seq_template').sudo().copy()
        code = '{}.{}.{}'.format(self._context.get('res_model', 'pos.branch'), branch_code, branch_id)
        name = '{}.{}.{}'.format(self._context.get('res_model', 'pos.branch'), branch_code, branch_id)

        if not padding:
            padding = ofm_seq_template.padding

        if not prefix:
            prefix = str(ofm_seq_template.prefix)

        ofm_seq_template.write({
            'code': code,
            'name': name,
            'padding': padding,
            'prefix': prefix,
        })
        # TODO:
        # Add into sequence table
        return self.env['pos.session.sequence'].create({
            'size': branch_code,
            'res_model': self._context.get('res_model', 'pos.branch'),
            'branch_id': branch_id,
            'branch_code': branch_code,
            'sequence_id': ofm_seq_template.id,
        })

    @api.multi
    @api.constrains('branch_id')
    def _check_allow_only_number(self):
        pattern = "^[0-9]*$"

        for record in self:
            if re.match(pattern, record.branch_id):
                is_number = True
            else:
                is_number = False

            if is_number is False:
                raise exceptions.ValidationError(
                    _("Branch ID must number only."))
