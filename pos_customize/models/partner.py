# -*- coding: utf-8 -*-

from odoo import api
from odoo import fields
from odoo import models
from odoo.exceptions import except_orm
from odoo.tools.translate import _


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    customer = fields.Boolean(
        'Is a Customer',
        help="Check this box if this contact is a customer.",
        track_visibility='onchange',
    )
    vip = fields.Selection(
        string='VIP',
        selection=[
            ('yes', 'Yes'),
            ('no', 'No')
        ],
        default='no',
        track_visibility='onchange',
    )
    shop_id = fields.Char(
        string='Branch ID',
        track_visibility='onchange',
        size=5,
    )
    total_address = fields.Char(
        compute='_compute_address',
        track_visibility='onchange',
    )
    ignore_repeat = fields.Boolean(
        'Check Repeat Tax Or Branch Code',
        default=True,
        track_visibility='onchange',
    )
    admin_edit_only = fields.Boolean(
        'Admin Edit Only',
        default=False,
        track_visibility='onchange',
    )
    name = fields.Char(
        track_visibility='onchange'
    )
    date = fields.Date(
        track_visibility='onchange'
    )
    title = fields.Many2one(
        track_visibility='onchange'
    )
    parent_id = fields.Many2one(
        track_visibility='onchange'
    )
    ref = fields.Char(
        track_visibility='onchange'
    )
    lang = fields.Selection(
        track_visibility='onchange'
    )
    tz = fields.Selection(
        track_visibility='onchange'
    )
    user_id = fields.Many2one(
        track_visibility='onchange'
    )
    website = fields.Char(
        track_visibility='onchange'
    )
    comment = fields.Text(
        track_visibility='onchange'
    )
    credit_limit = fields.Float(
        track_visibility='onchange'
    )
    barcode = fields.Char(
        track_visibility='onchange'
    )
    active = fields.Boolean(
        track_visibility='onchange'
    )
    customer = fields.Boolean(
        track_visibility='onchange'
    )
    supplier = fields.Boolean(
        track_visibility='onchange'
    )
    employee = fields.Boolean(
        track_visibility='onchange'
    )
    function = fields.Char(
        track_visibility='onchange'
    )
    type = fields.Selection(
        track_visibility='onchange'
    )
    street = fields.Char(
        string='Address',
        track_visibility='onchange',
    )
    street2 = fields.Char(
        string='Road',
        track_visibility='onchange',
    )
    zip = fields.Char(
        track_visibility='onchange'
    )
    city = fields.Char(
        track_visibility='onchange'
    )
    state_id = fields.Many2one(
        track_visibility='onchange'
    )
    country_id = fields.Many2one(
        track_visibility='onchange'
    )
    email = fields.Char(
        track_visibility='onchange'
    )
    phone = fields.Char(
        track_visibility='onchange',
        digit=10,
        size = 10,
    )
    fax = fields.Char(
        track_visibility='onchange',
        digit=10,
    )
    mobile = fields.Char(
        track_visibility='onchange',
        digit=10,
        size=10,
    )
    birthdate = fields.Char(
        track_visibility='onchange'
    )
    is_company = fields.Boolean(
        track_visibility='onchange'
    )
    company_type = fields.Selection(
        track_visibility='onchange'
    )
    use_parent_address = fields.Boolean(
        track_visibility='onchange'
    )
    company_id = fields.Many2one(
        track_visibility='onchange'
    )
    vat = fields.Char(
        track_visibility='onchange',
        size=13,
    )
    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        required=True,
    )
     
    @api.model
    def create(self, vals):
        vals = self._check_shop_id_digit(vals)

        vat = vals.get('vat', False)
        company_id = vals.get('company_id', False)
        branch = vals.get('shop_id', False)
        fields_restrict_dup = [
            vat,
            company_id,
        ]
        if all(fields_restrict_dup):
            params = {
                'vat': vat,
                'branch': branch,
                'company_id': company_id,
                'name': vals.get('name', False),
            }   
            non_dup = self._check_vat_repeat(params)
        return super(ResPartner, self).create(vals)

    @api.multi
    def write(self, vals):
        for record in self:
            user = record.env.user
            group_id = record.env.ref('base.group_system').id

            if record.admin_edit_only is True and group_id not in user.groups_id.ids:
                    raise except_orm(_('Error!'), _('Can not edit partner,Please contact administrator'))

            vals = self._check_shop_id_digit(vals)

            vat = ''

            if 'company_id' in vals and vals.get('company_id') or record.company_id:
                if 'company_id' in vals and vals.get('company_id'):
                    company_id = vals.get('company_id', False)
                elif record.company_id:
                    company_id = record.company_id.id or False
            else:
                company_id = record.env.user.company_id.id

            if 'vat' in vals and vals.get('vat') or record.vat:
                if 'vat' in vals and vals.get('vat'):
                    vat = vals.get('vat', False)
                elif record.vat:
                    vat = record.vat or False

            if ('vat' in vals and vals.get('vat')) or ('shop_id' in vals and vals.get('shop_id')): 
                params = {
                    'vat': vat,
                    'branch': vals.get('shop_id', False),
                    'company_id': company_id,
                }   
                non_dup = record._check_vat_repeat(params)
            return super(ResPartner, record).write(vals)

    @api.multi
    def _check_vat_repeat(self, condition_fields):

        #branch in this case doesnt pertain to any relation it is just info
        domain = [
            ('vat', '=', condition_fields.get('vat')),
            ('company_id', '=', condition_fields.get('company_id')),
            ('id', '!=', self.id)
        ]
        
        if self.parent_id.id:
            domain.append(('parent_id', '!=', self.parent_id.id))
            domain.append(('id', '!=', self.parent_id.id))
        
        branch = condition_fields.get('branch')
        if branch:
            domain.append(('shop_id', '=', branch))

        vat_repeat = self.search(domain)

        if(vat_repeat):
            raise except_orm(_('Error!'), _(" Tax ID Can't Repeat "))
        else:
            return True

    @api.model
    def _check_shop_id_digit(self, vals):
        if 'shop_id' in vals and vals.get('shop_id'):
            shop_id = vals.get('shop_id', False)
            if shop_id.isdigit():
                if len(shop_id) <= 5:
                    shop_id = shop_id.zfill(5)
                    vals['shop_id'] = shop_id
                else:
                    shop_id = shop_id[-5:]
                    vals['shop_id'] = shop_id
            else:
                raise except_orm(_('Error!'), _(" Can't save because shop ID has more than 5 digits "))

        return vals

    @api.multi
    def _check_vat_digit(self):
        for record in self:
            partner = record
            if partner.vat:
                if len(partner.vat) != 13:
                    return False
        return True

    _constraints = [(_check_vat_digit, 'Tax ID must be 13-digits', ["vat"])] 

    @api.depends('street', 'street2','city','state_id','zip')
    def _compute_address(self):
        for record in self:
            street = record.street or ""
            street2 = record.street2 or ""
            city = record.city or ""
            state = record.state_id.name or ""
            zip = record.zip or ""

            record.total_address = street + " " + street2 + "\n" + city + " " + state + " " + zip



