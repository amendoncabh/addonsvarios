# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Trinity Roots co.,ltd. (<http://www.trinityroots.co.th>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import date
from odoo import api, fields, models
from odoo.exceptions import except_orm
from odoo.tools.translate import _


class AccountMove(models.Model):
    _inherit = "account.move"

    auto_reverse_date = fields.Date(
        string='Auto Reverse Date',
        default=fields.Date.today(),
        readonly=True
    )

    account_reverse_id = fields.Many2one(
        comodel_name='account.move',
        string='Reverse Entry',
        readonly=True
    )

    def button_loadtemplate(self):
        for data in self:
            if data.account_model_id:
                for line in data.account_model_id.lines_id:
                    move_line = self.env['account.move.line']
                    move_line.create({
                        'account_id': line.account_id.id,
                        'name': line.name,
                        'debit': line.debit,
                        'credit': line.credit,
                        'move_id': data.id,
                    })
        return True

    @api.multi
    def action_auto_reverse(self):
        for rec in self:
            acc_move_line_obj = rec.env['account.move.line']
            default = {}
            context = {} if rec._context is None else rec._context.copy()
            obj = rec
            if not obj[0].auto_reverse_date:
                obj[0].auto_reverse_date = date.today().strftime('%Y-%m-%d')
            if obj[0].account_reverse_id:
                raise except_orm(_('Account reverse!'), _("Account Entry this reverse is done!!"))
            default.update({
                'state': 'draft',
                'name': '/',
                'journal_id': 5,
            })
            context.update({
                'copy': True,
            })
            # copy record first
            cp_id = rec.copy()
            rec.write({
                'account_reverse_id': cp_id.id
            })
            write_ct = {
                'auto_reverse_date': None,
                'ref': obj[0].name,
                'narration': 'Revert From Move Entry '+obj[0].name
            }
            # re-write head record first
            write_cp_id = rec.write(write_ct)
            # search and read line records
            search_con = {}
            move_line_ids = acc_move_line_obj.search([
                ('move_id', '=', cp_id.id)
            ])
            for line_id in move_line_ids:
                brwse_line = acc_move_line_obj.browse(line_id.id)
                new_line_cr = brwse_line.debit
                new_line_db = brwse_line.credit
                write_line_ct = {
                    'credit': new_line_cr,
                    'debit': new_line_db,
                }
                acc_move_line_obj.write(write_line_ct)

            return {
                    'name': _("Journal Entries"),
                    'view_mode': 'form',
                    'view_id': False,
                    'view_type': 'form',
                    'res_id': cp_id.id or False, # id of the object to which to redirected
                    'res_model': 'account.move', # object name
                    'type': 'ir.actions.act_window',
                    'target': 'current', # if you want to open the form in new tab
            }


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    invoice_id = fields.Many2one(
        comodel_name='account.invoice',
        string='Invoice'
    )
    voucher_id = fields.Many2one(
        comodel_name='account.voucher',
        string='Voucher'
    )
    deposit_id = fields.Many2one(
        comodel_name='account.deposit',
        string='Deposit'
    )

