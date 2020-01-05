# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import cStringIO
import contextlib

from odoo import api, models, tools
from tools.translate import trans_export

NEW_LANG_KEY = '__new__'

class BaseLanguageExport(models.TransientModel):
    _inherit = "base.language.export"

    @api.multi
    def act_getfile(self):
        this = self[0]
        lang = this.lang if this.lang != NEW_LANG_KEY else False
        mods = sorted(this.mapped('modules.name')) or ['all']

        with contextlib.closing(cStringIO.StringIO()) as buf:
            trans_export(lang, mods, buf, this.format, self._cr)
            out = base64.encodestring(buf.getvalue())

        filename = 'new'
        if lang:
            filename = tools.get_iso_codes(lang)
        elif len(mods) == 1:
            filename = mods[0]
        extension = this.format
        if not lang and extension == 'po':
            extension = 'pot'
        name = "%s.%s" % (filename, extension)
        this.write({'state': 'get', 'data': out, 'name': name})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'base.language.export',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': this.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
