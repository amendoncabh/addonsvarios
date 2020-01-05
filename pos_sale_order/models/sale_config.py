# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models, tools

tools.config['time_save_to_server'] = tools.config.get('time_save_to_server', 7500)
time_save_to_server = tools.config['time_save_to_server']

class PosConfig(models.Model):
    _inherit = "pos.config"

    so_uuid = fields.Char(readonly=True, default=lambda self: str(uuid.uuid4()),
                       help='A globally unique identifier for this pos configuration, used to prevent conflicts in client-generated data')

    @api.multi
    def open_pos_sale_order(self):
        sale_type = 'instore'
        if self._context.get('is_dropship', False):
            sale_type = 'dropship'

        self.env['sale.session'].create({
            'user_id': self.env.uid,
            'config_id': self.id,
            'sale_type': sale_type,
        })

        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            # 'url': '/sale/web/%s/' % base64.encodestring(json.dumps(param)),
            'url': '/sale/web/',
        }

    @api.model
    def get_time_save_to_server(self):
        result = int(time_save_to_server)
        return result
