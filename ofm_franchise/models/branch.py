# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class PosBranch(models.Model):
    _inherit = "pos.branch"

    state = fields.Selection(
        selection=[
           ('pending', 'Pending'),
           ('active', 'Active'),
           ('closed', 'Closed'),
        ],
        required=True,
        default='pending',
    )

    start_date = fields.Date(
        string="Start Date",
        required=False,
    )

    end_date = fields.Date(
        string="End Date",
        required=False,
    )

    royalty_fee = fields.Integer(
        string="Royalty Fee (%)",
        required=False,
    )

    acc_number = fields.Char(
        string="A/C No.",
        required=False,
        related='res_partner_bank_id.acc_number',
        store=True,
    )

    bank_id = fields.Many2one(
        'res.bank',
        string='Bank',
        required=False,
        index=True,
        related='res_partner_bank_id.bank_id',
        store=True,
    )

    acc_name_en = fields.Char(
        string="Account Name (EN)",
        required=False,
        related='res_partner_bank_id.acc_name_en',
        store=True,
    )

    res_partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Partner Bank",
        required=False,
    )

    remark = fields.Text(
        string="Remark",
        required=False,
    )

    attachment_ids = fields.One2many(
        comodel_name='ir.attachment',
        inverse_name='res_id',
        string='Attachments',
        domain=lambda self: [('res_model', '=', self._name)],
        auto_join=True, )

    is_cron_job = fields.Boolean(
        string="Con Job Day End",
        default=True,
    )

    @api.multi
    def action_branch_active(self):
        self.write({'state': 'active'})
        return True

    @api.multi
    def action_branch_closed(self):
        self.write({'state': 'closed'})
        return True

    @api.multi
    def action_branch_pending(self):
        self.write({'state': 'pending'})
        return True

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = ''.join([
                record.branch_code,
                ' ',
                record.name,
            ])

            result.append((record.id, name))

        return result

    @api.model
    def create(self, vals):
        self.check_acc_number(vals.get('acc_number'))
        acc_number = vals.get('acc_number', False)
        bank_id = vals.get('bank_id', False)
        acc_name_en = vals.get('acc_name_en', False)
        res_partner_bank_id = False
        if acc_number != False:
            partner_bank_id = self.env['res.partner.bank'].search([
                ('acc_number', '=', acc_number),
                ('partner_id', '=', self.partner_id.id),
                ('branch_id', '=', self.id),
            ])
            res_partner_bank_id = partner_bank_id.id
            if not partner_bank_id:
                res_bank_id = self.env['res.partner.bank'].create({
                    'company_id': self.pos_company_id.id,
                    'branch_id': self.id,
                    'acc_number': acc_number,
                    'bank_id': bank_id,
                    'partner_id': self.pos_company_id.partner_id.id,
                    'acc_name_en': acc_name_en
                })
                res_partner_bank_id = res_bank_id.id
            else:
                val = {'acc_number': acc_number}
                if bank_id:
                    val.update({'bank_id': bank_id})
                if acc_name_en:
                    val.update({'acc_name_en': acc_name_en})
                partner_bank_id.write(val)
            vals.update({'res_partner_bank_id': res_partner_bank_id})
        res = super(PosBranch, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        self.check_acc_number(vals.get('acc_number'))
        acc_number = vals.get('acc_number', False) 
        bank_id = vals.get('bank_id', False)
        acc_name_en = vals.get('acc_name_en', False)
        # res = super(PosBranch, self).write(vals)
        if acc_number != False:
            partner_bank_id = self.env['res.partner.bank'].search([
                ('acc_number', '=', acc_number),
                ('partner_id', '=', self.partner_id.id),
                ('branch_id', '=', self.id),
            ])
            res_partner_bank_id = partner_bank_id.id
            if not partner_bank_id:
                res_bank_id = self.env['res.partner.bank'].create({
                    'company_id': self.pos_company_id.id,
                    'branch_id': self.id,
                    'acc_number': acc_number,
                    'bank_id': bank_id or self.bank_id.id,
                    'partner_id': self.partner_id.id,
                    'acc_name_en': acc_name_en or self.acc_name_en})
                res_partner_bank_id = res_bank_id.id
            else:
                val = {'acc_number': acc_number}
                if bank_id:
                    val.update({'bank_id': bank_id})
                if acc_name_en:
                    val.update({'acc_name_en': acc_name_en})
                partner_bank_id.write(val)
            vals.update({'res_partner_bank_id': res_partner_bank_id})
        res = super(PosBranch, self).write(vals)
        return res

    @api.multi
    def check_acc_number(self, acc_number):
        if acc_number and acc_number != None and len(acc_number) > 0:
            try:
                int(acc_number)
                if len(acc_number) != 10:
                    raise Exception(" 10 digits integer.")
            except Exception as e:
                raise ValidationError("A/C No. : %s\nA/C No. must be integer 10 digits integer!!!!" % (acc_number))
