# -*- coding: utf-8 -*-

import threading

from odoo import fields
from odoo import models
from odoo import tools, api
from odoo.modules.module import get_module_resource


class PosCompany(models.Model):
    _name = 'pos.company'
    
    company_name = fields.Char(string='Company Name')
    street = fields.Char('Address')
    street2 = fields.Char('Road')
    zip = fields.Char('Zip', size=24, change_default=True)
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", 'State', ondelete='restrict')
    country_id = fields.Many2one('res.country', 'Country', ondelete='restrict')
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    tax_id = fields.Char('Tax ID')
    
    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary("Image",
                          help="This field holds the image used as avatar for this contact, limited to 1024x1024px",
                          default=lambda self: self._get_default_image(False, True))
    image_medium = fields.Binary("Medium-sized image",
                                 help="Medium-sized image of this contact. It is automatically "\
                                 "resized as a 128x128px image, with aspect ratio preserved. "\
                                 "Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized image",
                                help="Small-sized image of this contact. It is automatically "\
                                "resized as a 64x64px image, with aspect ratio preserved. "\
                                "Use this field anywhere a small image is required.")

    _defaults = {
        'image': False,
    }
                                        
    @api.model
    def _get_default_image(self, is_company, colorize=False):
        if getattr(threading.currentThread(), 'testing', False) or self.env.context.get('install_mode'):
            return False

        if self.env.context.get('partner_type') == 'delivery':
            img_path = get_module_resource('base', 'static/src/img', 'truck.png')
        elif self.env.context.get('partner_type') == 'invoice':
            img_path = get_module_resource('base', 'static/src/img', 'money.png')
        else:
            img_path = get_module_resource(
                                                           'base', 'static/src/img', 'company_image.png' if is_company else 'avatar.png')
        with open(img_path, 'rb') as f:
            image = f.read()

        # colorize user avatars
        if not is_company and colorize:
            image = tools.image_colorize(image)

        return tools.image_resize_image_big(image.encode('base64'))                                    
    
#    company_name = fields.Char(string='Company Name')
    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, rec.company_name))
        return res
    
    @api.multi
    def onchange_state(self, state_id):
        if state_id:
            state = self.env['res.country.state'].browse(state_id)
            return {'value': {'country_id': state.country_id.id}}
        return {'value': {}}
    
    @api.multi
    def write(self, vals):
        # tools.image_resize_image_small(vals)
        result = super(PosCompany, self).write(vals)
        return result

    @api.model
    def create(self, vals):
        # tools.image_resize_image_small(vals)
        company = super(PosCompany, self).create(vals)
        return company


class res_company(models.Model):
    _inherit = "res.company"

    branch_ids = fields.One2many(
        'pos.branch',
        'pos_company_id',
        readonly=True,
        string='Branch Child',
    )

    vat = fields.Char(
        required=True,
        size=13
    )

    street = fields.Char(
        required=True
    )
    street2 = fields.Char(
        required=True
    )
    zip = fields.Char(
        required=True
    )
    city = fields.Char(
        required=True
    )
    state_id = fields.Many2one(
        required=True
    )
    country_id = fields.Many2one(
        required=True
    )