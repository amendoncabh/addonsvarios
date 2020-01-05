# -*- coding: utf-8 -*-
import locale

from odoo import api, fields, models, tools


class WizardChangeDetail(models.TransientModel):
    _inherit = 'wizard.change.detail'

    def _get_tax_id(self):
        ctx = dict(self._context)
        partner_id = ctx.get('default_partner_id')
        partner = self.env['res.partner'].browse([partner_id])
        return partner.vat

    number = fields.Char(
        default=_get_tax_id,
        related=None,
        string='IDCard/TaxID',
        track_visibility='always',
    )

    @api.multi
    def change_detail(self):
        #check to see if theres a change in vat id, if changed, then write
        vat = self.partner_id.vat
        number = self.number
        if vat != number:
            self.partner_id.write({
                'vat': number
            })

        def bformat(val):
            date = fields.Date.from_string(val)
            locale.setlocale(locale.LC_TIME, 'th_TH.utf8')
            return date.strftime("%e %B %Ey")

        inv_obj = self.env['account.invoice']
        for form in self:
            for inv in inv_obj.browse(self._context.get('active_id', False)):
                residual = tools.float_round(
                    inv.residual,
                    precision_rounding=0.01
                )
                invoices = inv.copy()
                invoices.write({
                    'branch_id': inv.branch_id.id,
                    'date_invoice': inv.date_invoice,
                    'tax_id_customer': form.number,
                    'name_customer': form.name,
                    'address_inv': form.partner_id.get_new_addr(),
                    'note': form.comment,
                    'move_id': inv.move_id.id,
                    'tax_number': inv.get_name_invoice(),
                    'state': 'open',
                    'old_inv_id': inv.id,
                    'date_due': inv.date_due,
                    'note': u'เป็นการยกเลิกและออกใบกำกับภาษีฉบับใหม่ แทนฉบับเดิมเลขที่ %s วันที่ %s เนื่องจาก %s'
                            % (inv.tax_number, bformat(inv.date_invoice), form.comment)
                })

                if inv.pos_id:
                    inv.pos_id.invoice_id = invoices.id

                # Change Old Invoice
                inv.write({'move_id': None,
                           'state': 'cancel',
                           # 'note':form.comment,
                           })
                action = self.env.ref('account.action_invoice_tree1').read()[0]

                if action:
                    action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
                    action['res_id'] = invoices.id
                else:
                    action = {'type': 'ir.actions.act_window_close'}
                return action
