# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import time
import json
from ast import literal_eval

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


def dump_to_json(values):
    return json.dumps(values).encode('utf8')


class PosPricelistCache(models.Model):
    _name = 'pos.pricelist.cache'

    product_domain = fields.Text(
        required=True,
    )

    product_fields = fields.Text(
        required=True,
    )

    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string="Pricelist",
        required=True,
    )

    cache_branch_ids = fields.One2many(
        comodel_name="pos.pricelist.cache.branch",
        inverse_name="pos_pricelist_cache_id",
        string="Cache Branches",
    )

    product_len = fields.Integer(
        string="Product Length",
        required=False,
        readonly=True,
    )

    cache = fields.Binary(
        attachment=True,
    )

    @api.model
    def refresh_all_caches(self):
        # generate pricelist cache only Public Pricelist
        pricelist = self.env['product.pricelist'].search([('id', '=', self.env.ref('product.list0').id)])[0]
        product_domain = self.env['ir.config_parameter'].sudo().get_param('product_product_domain')
        product_fields = self.env['ir.config_parameter'].sudo().get_param('product_product_fields')
        Product = self.env['product.product'].sudo()
        branch = self.env['pos.branch'].search([], limit=1)[0]

        _logger.info("Start create caches pricelist id:%s name: %s process on 0/1", pricelist.id, pricelist.name)

        start = time.time()

        products = Product.search(literal_eval(product_domain))

        _logger.info("pricelist id:%s name: %s search time %s", pricelist.id, pricelist.name, time.time() - start)

        start = time.time()

        result = products.with_context(
            pricelist=self.pricelist_id.id,
            display_default_code=False,
            pricelist_branch_id=branch.id,
        ).read(literal_eval(product_fields))

        _logger.info("pricelist id:%s name: %s read time %s", pricelist.id, pricelist.name, time.time() - start)

        start = time.time()
        new_pricelist = self.create({
            'pricelist_id': pricelist.id,
            'product_domain': product_domain,
            'product_fields': product_fields,
            'product_len': len(products),
            'cache': base64.encodestring(dump_to_json(result)),
        })
        _logger.info("pricelist id:%s name: %s  write time %s", pricelist.id, pricelist.name, time.time() - start)

        _logger.info("Finish create caches pricelist id:%s name: %s process on 1/1", pricelist.id, pricelist.name)

        del result

        return new_pricelist

    @api.model
    def get_product_domain(self):
        return literal_eval(self.product_domain)

    @api.model
    def get_product_fields(self):
        return literal_eval(self.product_fields)

    @api.model
    def get_cache(self):
        result = self
        if not result.cache:
            result = self.refresh_all_caches()
        return result

    @api.multi
    def unlink(self):
        to_remove_cache = []
        for record in self:
            to_remove_cache += record.cache_branch_ids.ids

        ir_attachment = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'pos.pricelist.cache.branch'),
            ('res_field', '=', 'cache'),
            ('res_id', 'in', to_remove_cache),
        ])

        ir_attachment.sudo().unlink()
        res = super(PosPricelistCache, self).unlink()
        return res


class PosPricelistCacheBranch(models.Model):
    _name = 'pos.pricelist.cache.branch'
    _order = 'id desc'

    pos_pricelist_cache_id = fields.Many2one(
        comodel_name='pos.pricelist.cache',
        string='Pos Pricelist Cache',
    )

    branch_id = fields.Many2one(
        comodel_name='pos.branch',
        string='Branch',
        required=True,
    )

    cache = fields.Binary(
        attachment=True,
    )


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    @api.one
    @api.depends('cache_ids')
    def _get_latest_cache_time(self):
        pos_cache = self.env['pos.pricelist.cache']
        latest_cache = pos_cache.search([('pricelist_id', '=', self.id)], order='id DESC', limit=1)
        if latest_cache:
            self.latest_cache_id = latest_cache

    cache_ids = fields.One2many(
        'pos.pricelist.cache',
        'pricelist_id'
    )

    latest_cache_id = fields.Many2one(
        comodel_name="pos.pricelist.cache",
        string="Latest cache",
        compute='_get_latest_cache_time',
        required=False,
    )

    latest_cache_time = fields.Datetime(
        related='latest_cache_id.write_date',
        string='Latest cache time',
        readonly=True
    )

    @api.multi
    def get_products_from_cache(self):
        if self.latest_cache_id:
            latest_cache_by_branch = self.latest_cache_id.get_cache()
            if latest_cache_by_branch:
                return json.loads(base64.decodestring(latest_cache_by_branch.cache))

        new_cache = self.env['pos.pricelist.cache'].get_cache()
        return json.loads(base64.decodestring(new_cache.cache))

    @api.one
    def new_cache(self):
        self.env['pos.pricelist.cache'].get_cache()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.one
    def delete_cache(self):
        # throw away the old caches
        self.cache_ids.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.one
    def delete_old_caches(self):
        self.delete_old_caches_not_greater_than_number(number=1)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.one
    def delete_old_caches_not_greater_than_number(self, number):
        pos_cache = self.env['pos.pricelist.cache']
        latest_number_cache_ids = pos_cache.search([('pricelist_id', '=', self.id)], order='id DESC', limit=number)
        self.cache_ids.filtered(lambda cache: cache.id not in latest_number_cache_ids.ids).unlink()

    @api.model
    def refresh_old_pricelist_caches(self, number):
        for pricelist in self.search([]):
            pricelist.delete_old_caches_not_greater_than_number(number)
