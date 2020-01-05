# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import except_orm


class POSSessionSequence(models.Model):
    _name = 'company.session.sequence'
    _description = 'Company Session Sequence'

    size = fields.Char(
        string='Padding',
    )
    res_model = fields.Char(
        string='Res Model',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Comapny',
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        copy=False,
    )
    branch_id = fields.Many2one(
        comodel_name='pos.branch',
        string='Branch Location',
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        copy=False,
    )
    branch_code = fields.Char(
        string='Branch Code',
        required=True,
    )
    sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string='Session Sequence',
        ondelete='restrict',
    )

    def check_branch_code(self):
        if not self.branch_id:
            raise except_orm(_('Error!'), _(u" Please Set Branch"))
        elif not self.branch_id.branch_code:
            raise except_orm(_('Error!'), _(u" Please Set Store Code "))
        else:
            return True

    def check_company(self):
        if not self.company_id:
            raise except_orm(_('Error!'), _(u" Please Set Company "))
        else:
            return True

    def next_sequence(self):
        company_id = self._context.get('company_id', False)
        branch_id = self._context.get('branch_id', False)
        branch_code = self._context.get('branch_code', False)
        not_sequence_id = self._context.get('not_sequence_id', False)

        if not company_id:
            raise except_orm(_('Error!'), _(u" Please Set Company "))
        elif not branch_id:
            raise except_orm(_('Error!'), _(u" Please Set Branch"))
        elif not branch_code:
            raise except_orm(_('Error!'), _(u" Please Set Store Code "))

        if all([
            company_id,
            branch_id,
        ]):
            seq = self.env['company.session.sequence'].search([
                ('company_id', '=', company_id.id),
                ('branch_id', '=', branch_id.id),
                ('res_model', '=', self._context.get('res_model', 'res.partner')),
            ], limit=1)

            if not seq:
                seq = self.create_sequence()
        else:
            raise except_orm(_('Error!'), _('Can Not Create Because Not Have Sequence Or Not Set Branch'))

        if not_sequence_id:
            return seq.sequence_id.next_by_id()
        else:
            return seq.sequence_id

    @api.multi
    def create_sequence(self):
        company_id = self._context.get('company_id', False)
        branch_id = self._context.get('branch_id', False)
        branch_code = self._context.get('branch_code', False)
        padding = self._context.get('padding', False)
        prefix = self._context.get('prefix', False)
        res_model = self._context.get('res_model', 'res.partner')

        ofm_seq_template = self.env.ref('sequence_per_company.ofm_seq_template_no_date').sudo().copy()
        code = '{}.{}.{}'.format(res_model, branch_code, branch_id.id)
        name = '{}.{}.{}'.format(res_model, branch_code, branch_id.id)

        if not padding:
            padding = ofm_seq_template.padding

        if not prefix:
            prefix = branch_code

        ofm_seq_template.write({
            'code': code,
            'name': name,
            'padding': padding,
            'prefix': prefix,
        })
        # TODO:
        # Add into sequence table
        session_sequence_id = self.create({
            'size': branch_code,
            'res_model': res_model,
            'company_id': company_id.id,
            'branch_id': branch_id.id,
            'branch_code': branch_code,
            'sequence_id': ofm_seq_template.id,
        })

        return session_sequence_id