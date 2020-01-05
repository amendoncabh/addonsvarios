# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.addons.base.res.res_partner import FormatAddress
from odoo.exceptions import except_orm


class CustomerMember(models.Model, FormatAddress):
    _inherit = "res.partner"

    @api.model
    def _default_branch_id(self):
        if self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id
            return branch_id
        else:
            raise except_orm(_('Error!'), _(u" Please Set Branch For This User "))

    @api.model
    def _default_property_payment_term_id(self):
        return self.env.ref('account.account_payment_term_net').id

    main_contact_person = fields.Char( 
        string='Main Contact Person',
        size=50,
    )

    max_aging = fields.Float(
        default=10000,
    )

    comment = fields.Text(
        string='Internal Note'
    )

    follow_up_note = fields.Text(
        string='Follow Up Note'
    )

    customer_payment_type = fields.Selection(
        selection=[
            ('cash', 'Cash /Credit Card'),
            ('credit', 'Credit Term'),
        ],
        string='Customer Type'
    )

    credit_term_tender_id = fields.Many2one(
        comodel_name="account.payment.method.multi",
        string="Payment Methods",
    )

    billing_condition_type = fields.Selection(
        selection=[
            ('delivery_billing', 'ส่งของพร้อมวางบิล'),
            ('delivery_billing_period', 'ส่งของ /วางบิลตามรอบ'),
        ],
        string='Billing Condition'
    )

    type = fields.Selection(
        selection=[
            ('contact', 'Contact'),
            ('invoice', 'Invoice address'),
            ('delivery', 'Shipping address'),
            ('billing', 'Billing address'),
            ('other', 'Other address')
        ],
        string='Address Type',
        default='contact',
        help="Used to select automatically the right address according to the context in sales and purchases documents."
    )

    customer_code = fields.Char(
        string='Customer Code',
        readonly=True,
    )

    branch_id = fields.Many2one(
        comodel_name='pos.branch',
        string='Branch',
        default=_default_branch_id,
        required=False,
    )

    ignore_repeat = fields.Boolean(
        'Allow Duplicate Tax Or Branch Code',
        default=True,
        track_visibility='onchange',
    )

    @api.onchange('customer_payment_type')
    def onchange_customer_payment_type(self):
        if self.customer_payment_type == 'credit' and not self.property_payment_term_id:
            self.property_payment_term_id = self._default_property_payment_term_id()
        else:
            self.property_payment_term_id = False

    @api.onchange('max_aging')
    def onchange_max_aging_on_parent(self):
        for child_id in self.child_ids:
            child_id.update({
                'max_aging': self.max_aging
            })

    def get_customer_code(self):
        branch_id = self._context.get('branch_id', False)

        if branch_id:
            branch_code = branch_id.branch_code
            prefix = branch_code
        else:
            branch_code = False
            prefix = False

        ctx = dict(self._context)
        ctx.update({
            'branch_code': branch_code,
            'padding': 6,
            'prefix': prefix,
            'res_model': 'res.partner.customer',
            'not_sequence_id': True,
        })

        customer_sequence = self.env['company.session.sequence'].with_context(ctx).next_sequence()

        return customer_sequence

    def get_data_from_vals(self, vals):
        company_id = vals.get('company_id', False)
        branch_id = vals.get('branch_id', False)

        vals_item = {}

        if company_id:
            vals_item.update({
                'company_id': self.env['res.company'].browse(company_id),
            })

        if branch_id:
            vals_item.update({
                'branch_id': self.env['pos.branch'].browse(branch_id),
            })

        return vals_item

    def get_branch_by_company(self):
        if self.company_id.id == self.env.user.branch_id.pos_company_id.id:
            self.branch_id = self._default_branch_id()
        else:
            self.branch_id = False
           
        branch_domain = {
            'domain': {
                'branch_id': [
                    ('pos_company_id', '=', self.company_id.id)
                ],
            },
        }

        return branch_domain

    @api.onchange('company_id')
    def onchange_company(self):
        res = self.get_branch_by_company()

        return res

    def list_duplicate_field(self):
        duplicate_field = [
            'name',
            'company_id',

        ]

        return duplicate_field

    def check_create_from_customer(self, ctx):
        key_customer = [
            'search_default_customer',
            'default_customer',
            'customer'
        ]

        for key in key_customer:
            if ctx.get(key, 0) == 1:
                return True

    @api.model
    def create(self, vals):
        ctx = dict(self._context)
        is_customer = self.check_create_from_customer(ctx)

        if all([
            is_customer,
            not vals.get('parent_id', False)
        ]):
        
            ctx.update(self.get_data_from_vals(vals))

            customer_code = self.with_context(ctx).get_customer_code()

            vals.update({
                'customer_code': customer_code,
            })

        res = super(CustomerMember, self).create(vals)

        return res

    @api.onchange('name', 'type')
    def _onchange_type(self):
        if self.type == "delivery" and self.name:
            if len(self.name) > 50:
                self.update({
                    'name' : ''
                })
                self.env.user.notify_warning(
                    "Response",
                    "Number of characters cannot exceed 50 for shipping type."
                )
