# -*- coding: utf-8 -*-

from openerp import api, models


class WizardModel(models.TransientModel):
    _name = "module.wizard_model"

    @api.multi
    def action_accept(self):
        self.ensure_one()
        self.do_something_useful()
