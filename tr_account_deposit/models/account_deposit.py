from datetime import datetime
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.tools import float_round
from odoo.exceptions import UserError, except_orm, Warning, RedirectWarning

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_deposit': 'sale',
    'in_deposit': 'purchase',
}


class AccountDeposit(models.Model):
    _name = 'account.deposit'
    _inherit = ['mail.thread']
    _order = 'date desc'

    @api.model
    def _default_journal(self):
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id or self.env.user.company_id.currency_id

    @api.model
    def _default_company(self):
        company_id = self._context.get('company_id', self.env.user.company_id.id)

        return company_id or 1

    def _default_branch(self):
        branch_id = self._context.get('branch_id', False)
        if branch_id:
            return branch_id
        return self.env.user.branch_id

    is_first_print_dpo = fields.Boolean(
        string="First Print",
        readonly=True,
        default=True,
    )

    print_time_dpo = fields.Integer(
        string="Deposit Print Count",
        required=False,
        default=0,
    )

    name = fields.Char(
        string="Name",
        index=True,
        default="New",
        readonly=True,
        copy=False,
        track_visibility='onchange',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        required='True',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        track_visibility='onchange',
    )
    account_entry_id = fields.Many2one(
        comodel_name='account.move',
        string='Entry',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        required='True',
        default=_default_journal,
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        track_visibility='onchange',
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        string="Account",
        required='True',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        track_visibility='onchange',
    )
    date = fields.Date(
        string='Date',
        required='True',
        readonly=True,
        default=fields.Datetime.now,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        track_visibility='onchange',

    )
    origin = fields.Char(
        string='Source Document',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        }
    )
    amount_tax = fields.Float(
        string='Tax',
        # digits=dp.get_precision('Account'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_untaxed = fields.Float(
        string='Amount Untaxed',
        # digits=dp.get_precision('Account'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    paid_total = fields.Float(
        string='Paid Total',
        # digits=dp.get_precision('Account'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    type = fields.Selection(
        [
            ('in_deposit', 'Payment Deposit'),
            ('out_deposit', 'Receive Deposit')
        ],
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        }
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancel')
        ],
        index=True,
        string='State',
        default='draft',
        track_visibility='onchange',
    )
    deposit_line = fields.One2many(
        comodel_name='account.deposit.line',
        inverse_name='deposit_id',
        string='Detail Line',
        copy=True,
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        }
    )
    payment_line = fields.One2many(
        comodel_name='account.deposit.payment.line',
        inverse_name='payment_id',
        string='Detail Line',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        }

    )
    invoice_id = fields.Many2one(
        comodel_name='account.invoice',
        string='Invoice',
        readonly=True
    )
    sale_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sale',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        }
    )
    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        }
    )
    note = fields.Text(
        string='Note',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        }
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=_default_currency,
        required=True,
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        }
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=_default_company,
        required=True,
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        }
    )
    branch_id = fields.Many2one(
        comodel_name='pos.branch',
        string='Branch',
        default=_default_branch,
        required=True,
    )
    tax_line = fields.One2many(
        comodel_name='account.deposit.tax',
        inverse_name='deposit_id',
        string='Tax Lines',
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        copy=False
    )
    check_total = fields.Float(
        string='Verification Total',
        # digits=dp.get_precision('Account'),
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        default=0.0
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry',
        readonly=True,
        index=True,
        ondelete='restrict',
        copy=False,
        help="Link to the automatically generated Journal Items.",
        states={
            'draft': [
                ('readonly', False)
            ]
        }
    )
    account_refund_id = fields.Many2one(
        comodel_name='account.account',
        string="Refund ID",
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        }
    )
    validate_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Validate By',
        readonly=True
    )
    internal_number = fields.Char(
        string='Invoice Number',
        readonly=True,
        default=False,
        copy=False,
        help="Unique number of the invoice, computed automatically when the invoice is created."
    )

    is_hide_reset_to_draft = fields.Boolean(
        string='Hide Reset to Draft',
        compute='compute_is_hide_reset_to_draft',
        default=True,
    )

    is_hide_deposit_return = fields.Boolean(
        string='Hide Deposit Return',
        compute='compute_is_hide_deposit_return',
        store=False,
        default=True,
    )

    type_sale_ofm = fields.Boolean(
        string='Type Sale OFM',
        readonly=True,
        default=False,
    )

    change_rounding = fields.Float(
        string='Rounding',
        digits=0,
        track_visibility='onchange',
        store=True,
        readonly=True,
    )

    def write(self, values):
        # tracking change in line_ids
        masege_obj = self.env['mail.message']
        body_dict = self.line_ids_changing(values=values, body_dict={})
        message_qty_before = len(masege_obj.search
                                 ([('model', '=', 'account.deposit'), ('res_id', '=', self.id)]))
        res = super(AccountDeposit, self).write(values)
        message_qty_after = len(masege_obj.search
                                ([('model', '=', 'account.deposit'), ('res_id', '=', self.id)]))
        if body_dict != {}:
            status = message_qty_after - message_qty_before  # 0 = create 1=update in mail.message
            body_dict = self.line_ids_changing(values, body_dict)
            self.update_log(body_dict=body_dict, status=status)  # update log

        return res

    def line_ids_changing(self, values, body_dict):
        for val_key in values:
            body = ''
            if val_key == 'payment_line':
                field_ids = 'payment_line'

                body = """\
                    <table class="table_log" bgcolor="white"><tbody bgcolor="white"> \
                        <tr>\
                            <td>Payment Method</td>\
                            <td>Payment Journal</td>\
                            <td>Tender</td>\
                            <td>Credit Card No.</td>\
                            <td>Total</td>\
                        </tr>\
                        """

                query = """
                select apmm.name as payment_method,
                    aj.name as payment_journal,
                    coalesce(adpl.tender,'') as tender,
                    coalesce(adpl.credit_card_no,'') as credit_card_no,
                    adpl.paid_total as total
                from account_deposit_payment_line adpl 
                    inner join account_payment_method_multi apmm on adpl.payment_method_id = apmm.id
                    inner join account_journal aj on adpl.journal_id = aj.id
                    where adpl.payment_id = %s  
                order by adpl.id
                """

            elif val_key == 'deposit_line' and values.get(val_key,False):
                field_ids = 'deposit_line'

                body = """\
                        <table class="table_log"><tbody bgcolor="white">\
                            <tr>\
                                <td>Description</td>\
                                <td>Taxes</td>\
                                <td>Total</td>\
                                <td>Amount</td>\
                            </tr>\
                        """

                query = """
                    select 	adl.id as id,
                            adl.name as name,
                            adl.total as total,
                            adl.price_subtotal as price_subtotal,
                            array_to_string(array_agg(distinct act.name),',') AS tax
                    from (select id,
                                name,
                                total,
                                price_subtotal
                                from account_deposit_line
                                where deposit_id = %s
                        ) adl 
                    inner join (select deposit_line_id,
                                    tax_id
                                    from account_deposit_line_tax
                                ) adlt on adlt.deposit_line_id = adl.id
                    inner join ( select id,
                                name
                                from account_tax) act on adlt.tax_id = act.id
                    group by adl.id,adl.name,adl.total,adl.price_subtotal
                    order by id
                """

            else:
                continue
            self._cr.execute(query, (self.id,))
            query_results = self._cr.dictfetchall()
            for line_dict in query_results:
                if field_ids == 'payment_line':
                    body += '<tr>\
                                <td>{}</td>\
                                <td>{}</td>\
                                <td>{}</td>\
                                <td>{}</td>\
                                <td>{}</td>\
                             </tr>'.format(line_dict['payment_method'],
                                           line_dict['payment_journal'],
                                           line_dict['tender'],
                                           line_dict['credit_card_no'],
                                           line_dict['total'],
                                           )

                if field_ids == 'deposit_line':
                    body += '<tr>\
                                <td>{}</td>\
                                <td>{}</td>\
                                <td>{}</td>\
                                <td>{}</td>\
                            </tr>'.format(line_dict['name'],
                                          line_dict['tax'],
                                          line_dict['total'],
                                          line_dict['price_subtotal'],
                                          )
            body = body + '</tbody></table>'
            if body_dict == {} or body_dict.get(field_ids) == None:  # case for before super , create key and value
                body_dict[field_ids] = body
            elif body_dict.get(field_ids) != None:  # case for after super , update value
                icon = '<p><span class="fa fa-angle-double-down fa-1x" style=""></span><br></p>'
                body_dict[field_ids] = body_dict.get(field_ids) + icon + body
        return body_dict

    def update_log(self, body_dict, status):
        body = ''
        for key, val in body_dict.items():
            body += '<h3>{}</h3>'.format(key)
            body += val
        body = """\
        <!DOCTYPE html>\
                <html>\
                <head>\
                <style>\
                .table_log {\
                    border: 1px solid black\
                }\
                .table_log tr{\
                    border: 1px solid black\
                }\
                .table_log td{\
                    border: 1px solid black\
                }\
                .table_log th{\
                    border: 1px solid black\
                }\
            </style>\
            </head>\
            <body>\
            <div style='background-color: rgb(228 ,228 ,228);'>%s</div>\
            </body>\
            </html> """ % (body)
        if status == 0:  # create record in mail.message
            self._cr.execute("""
                    INSERT INTO mail_message (model,res_id,parent_id,body,date,message_type,
                                                create_uid,create_date,author_id)
                    VALUES ('account.deposit',%s,Null,%s,now(),'email',%s,now(),%s)
                    """, (self.id, body, self.env.user.id, self.env.user.partner_id.id))
        else:  # update record in mail.message
            self._cr.execute(""" 
                    with tb_mail_meaasge as (
                        select id
                        from mail_message
                        where res_id = %s
                        order by id desc limit 1
                        )
                    update mail_message
                    set body = %s
                    from tb_mail_meaasge tb_mail 
                    where mail_message.id = tb_mail.id
                    """, (self.id, body))
        return True

    hide_cancel_button = fields.Boolean(
        string="Hide Cancel Button",
        compute='_compute_hide_hide_cancel_button',
        readonly=True,
    )

    @api.multi
    def _compute_hide_hide_cancel_button(self):
        for record in self:
            value  = self.env['ir.config_parameter'].search([
                ('key', '=', 'account_deposit_hide_cancel_button'),
                ]).value
            if value.lower() == 'true':
               record.hide_cancel_button = True
               return True
            record.hide_cancel_button = False


    def get_account_deposit_out_no(self):
        if self.sale_id.sale_payment_type == 'deposit':
            res_model = 'account.invoice' + '.out_invoice.' + str(self.journal_id.id)
        else:
            res_model = self._name + '.out_invoice.' + str(self.journal_id.id)

        seq = self.env['pos.session.sequence'].search([
            ('branch_code', '=', self.branch_id.branch_code),
            ('res_model', '=', res_model),
        ], limit=1)

        sequence = self.journal_id.sequence_id

        if self.type in ['out_refund', 'in_refund'] and self.journal_id.refund_sequence:
            if not self.journal_id.refund_sequence_id:
                raise UserError(_('Please define a Tax Invoice Return Sequence'))
            sequence = self.journal_id.refund_sequence_id

        prefix = sequence.prefix

        if not seq:
            padding = 5
            if self.branch_id.branch_code:
                if prefix.find('/') != -1:
                    prefixs = sequence.prefix.split('/')
                elif prefix.find('-') != -1:
                    prefixs = sequence.prefix.split('-')
                else:
                    raise UserError(_(u"This %s Prefix Don't Have Special Character" % prefix))

                if self.type in ['in_invoice']:
                    prefix = prefixs[0] + '-' + self.branch_id.branch_code + '%(y)s%(month)s'
                    padding = 6

                else:
                    prefix = prefixs[0] + '-' + self.branch_id.branch_code + '%(y)s%(month)s'

            date_order = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ctx = dict(self._context)
            ctx.update({'res_model': res_model})

            sequence_id = self.branch_id.with_context(ctx).next_sequence(date_order, prefix, padding, False)

        else:

            sequence_id = seq.sequence_id

        new_name = sequence_id.with_context(ir_sequence_date=self.date).next_by_id()

        if self.sale_id.sale_payment_type != 'deposit':
            new_name = new_name.replace("SI-", "Receipt-")
        return new_name

    def get_account_deposit_in_no(self):
        prefix = 'DPI-' + self.branch_id.branch_code + '%(y)s%(month)s'
        ctx = dict(self._context)

        ctx.update({'res_model': 'account.deposit.in'})

        account_deposit_in_no = self.branch_id.with_context(ctx).next_sequence(self.date, prefix, 5) or '/'

        return account_deposit_in_no

    def get_name(self):
        if (not self.name) or self.name == 'New':
            if self.type == 'out_deposit':
                name = self.get_account_deposit_out_no()
            else:
                name = self.get_account_deposit_in_no()

            return name

    @api.model
    def get_move_line(self):
        res = []
        for deposit in self:

            if deposit.type == 'in_deposit':
                amount = -deposit.amount_untaxed
            else:
                amount = deposit.amount_untaxed

            if deposit.type_sale_ofm:
                acc_name = ''.join([
                    'Deposit: ',
                    deposit.name
                ])
            else:
                acc_name = ''.join([
                    'Cash/ Credit: ',
                    deposit.name
                ])

            res.append({
                'type': 'dest',
                'name': acc_name,
                'price': amount,
                'account_id': deposit.account_id.id,
                'date_maturity': deposit.date,
                'amount_currency': False,
                'currency_id': False,
                'ref': deposit.name,
                'deposit_id': deposit.id,
            })
            # residual = deposit.residual - total
            # if residual <= 0:
            deposit.write({'state': 'paid'})

        return res

    def get_state_hide_reset_to_draft(self):
        return [
            'draft',
            'open',
            'paid',
        ]

    @api.one
    @api.depends('deposit_line.total', 'tax_line.amount', 'payment_line.paid_total')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.deposit_line)
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.paid_total = sum(line.paid_total for line in self.payment_line)
        if self.change_rounding:
            self.paid_total += self.change_rounding

    @api.multi
    @api.depends('state')
    def compute_is_hide_reset_to_draft(self):
        for rec in self:
            rec.is_hide_reset_to_draft = True

    @api.multi
    def button_reset_taxes(self):
        account_deposit_tax = self.env['account.deposit.tax']
        ctx = dict(self._context)
        for deposit in self:
            self._cr.execute("DELETE FROM account_deposit_tax WHERE deposit_id=%s AND manual is False", (deposit.id,))
            self.invalidate_cache()
            partner = deposit.partner_id
            if partner.lang:
                ctx['lang'] = partner.lang
            for taxs in account_deposit_tax.compute(deposit).values():
                account_deposit_tax.create(taxs)
        return self.with_context(ctx).write({
            'deposit_line': []
        })

    @api.multi
    def button_compute(self, set_total=False):
        self.button_reset_taxes()
        for deposit in self:
            if set_total:
                deposit.check_total = deposit.amount_total
        return True

    @api.multi
    def deposit_open(self):
        total_deposit_line = sum([deposit_line_rec.total for deposit_line_rec in self.deposit_line])
        if float_round(self.paid_total, precision_digits=0.01) != float_round(total_deposit_line,
                                                                              precision_digits=0.01):
            raise except_orm(_('Error!'), _(u"Paid Total Invalid."))

        # obj_sequence = self.pool.get('ir.sequence')
        self.button_reset_taxes()
        if (self.name is False or self.name == 'New') and self.internal_number is False:
            self.name = self.get_name()
            self.write({
                'internal_number': self.name
            })
        else:
            self.name = self.internal_number

        self.move_id = self.action_move_create()

        return self.write({
            'state': 'open',
            'validate_partner_id': self.env.user.partner_id.id,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    @api.multi
    def deposit_cancel(self):
        if self.move_id:
            if self.move_id.state == 'draft':
                journal_move_id = self.move_id
                self.move_id = None
                journal_move_id.unlink()
            else:
                self.move_id.action_auto_reverse()
                # self.move_id.account_reverse_id.button_validate()

        if self.sale_id:
            self.sale_id.update({
                'sale_payment_type': False,
            })

        self.write({
            'state': 'cancel'
        })

        return True

    @api.multi
    @api.depends('state')
    def compute_is_hide_deposit_return(self):
        if self.sale_id and not self.sale_id.type_sale_ofm:
            self.is_hide_deposit_return = True
        else:
            account_invoice = self.env['account.invoice'].search_count([('so_id', '=', self.sale_id.id)])
            if account_invoice:
                self.is_hide_deposit_return = True
            else:
                self.is_hide_deposit_return = False

    @api.multi
    def deposit_return(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'Deposit Reverse Transfer',
            'res_model': 'deposit.stock.return.picking',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('tr_account_deposit.view_deposit_stock_return_picking_form', False).id,
            'target': 'new',
            'deposit_id': self.id,
        }

    @api.multi
    def deposit_return_action(self):

        ctx = dict(self._context) or {}
        ctx.update({
            'skip_modify_cn': False
        })
        so_id = self.env['sale.order'].search([('id', '=', self.sale_id.id)])
        spk_id = self.env['stock.picking'].search([('origin', '=', so_id.name)])

        invoice_ids = spk_id.create_invoice(spk_id)
        cn_ids = spk_id.with_context(ctx).create_cn(spk_id)

        if cn_ids:
            self.invoice_id = cn_ids.id

            # Update action_invoice_open()
            cn_ids.action_invoice_open()

            cn_ids.write({'state': 'paid', })

            so_id.action_cancel_so()
            invoice_ids.unlink()

        if spk_id:
            spk_id.write({
                'state': 'cancel',
            })

        if self.sale_id:
            self.sale_id.update({
                'sale_payment_type': 'deposit',
            })

        self.write({
            'state': 'paid',
        })

        return True

    @api.multi
    def action_move_create(self):
        # account_invoice_tax = self.env['account.deposit.tax']
        account_move_line = self.env['account.move.line']
        for deposit in self:
            if not deposit.deposit_line:
                raise except_orm(_('No Deposit Lines!'), _('Please create some deposit lines.'))
            if not deposit.payment_line:
                raise except_orm(_('No Payment Lines!'), _('Please create some payment lines.'))
            temp_deposit = deposit.paid_total - deposit.amount_tax
            if float_round(deposit.amount_untaxed, precision_digits=0.01) != float_round(temp_deposit,
                                                                                         precision_digits=0.01):
                raise except_orm(_('Payment in not balance!'), _('Please check payment lines.'))
            if deposit.move_id:
                continue
            date = deposit.date
            ctx = dict(deposit._context, lang=deposit.partner_id.lang)
            ctx['date'] = date
            ctx['company_id'] = deposit.company_id.id

            move_val = {
                'name': deposit.name,
                'ref': deposit.name,
                'journal_id': deposit.journal_id.id,
                'narration': deposit.note,
                'partner_id': deposit.partner_id.id,
                'company_id': deposit.company_id.id
            }

            move_id = deposit.env['account.move'].with_context(branch_id=deposit.branch_id.id).create(move_val)

            if deposit.type == 'in_deposit':
                for line in deposit.deposit_line:
                    move_line_detail = {
                        'name': line.name,
                        'debit': line.price_subtotal,
                        'credit': 0.00,
                        'move_id': move_id.id,
                        'date': deposit.date,
                        'account_id': deposit.account_id.id,
                        'ref': deposit.name,
                        'journal_id': deposit.journal_id.id,
                        'partner_id': deposit.partner_id.id,
                        'tax_amount': line.price_subtotal,
                    }

                    account_move_line.with_context(check_move_validity=False).create(move_line_detail)

                for tax in deposit.tax_line:
                    move_line_detail = {
                        'name': tax.name,
                        'debit': tax.amount,
                        'credit': 0.00,
                        'move_id': move_id.id,
                        'account_id': tax.account_id.id,
                        'journal_id': deposit.journal_id.id,
                        'partner_id': deposit.partner_id.id,
                        'tax_amount': tax.amount,
                    }

                    account_move_line.with_context(check_move_validity=False).create(move_line_detail)

                for payment in deposit.payment_line:
                    move_line_detail = {
                        'name': payment.payment_method_id.name,
                        'debit': 0.00,
                        'credit': payment.paid_total,
                        'move_id': move_id.id,
                        'account_id': payment.payment_method_id.account_id.id,
                        'ref': None,
                        'journal_id': deposit.journal_id.id,
                        'partner_id': deposit.partner_id.id,

                    }
                    account_move_line.with_context(check_move_validity=False).create(move_line_detail)
            else:
                for line in deposit.deposit_line:
                    move_line_detail = {
                        'name': line.name,
                        'debit': 0.00,
                        'credit': line.price_subtotal,
                        'move_id': move_id.id,
                        'date': deposit.date,
                        'account_id': deposit.account_id.id,
                        'ref': deposit.name,
                        'journal_id': deposit.journal_id.id,
                        'partner_id': deposit.partner_id.id,
                        'tax_amount': line.price_subtotal,
                    }

                    account_move_line.with_context(check_move_validity=False).create(move_line_detail)

                for tax in deposit.tax_line:
                    move_line_detail = {
                        'name': tax.name,
                        'debit': 0.00,
                        'credit': tax.amount,
                        'move_id': move_id.id,
                        'account_id': tax.account_id.id,
                        'journal_id': deposit.journal_id.id,
                        'partner_id': deposit.partner_id.id,
                        'tax_amount': tax.amount,
                    }
                    account_move_line.with_context(check_move_validity=False).create(move_line_detail)

                for payment in deposit.payment_line:
                    payment_obj = deposit.env['account.payment.method.multi']

                    move_line_detail = {
                        'name': payment.payment_method_id.name,
                        'debit': (payment.paid_total * payment.payment_method_id.percent) / 100,
                        'credit': 0.00,
                        'move_id': move_id.id,
                        'account_id': payment.payment_method_id.property_account_payment_method_id.id,
                        'ref': None,
                        'journal_id': deposit.journal_id.id,
                        'partner_id': deposit.partner_id.id,
                    }
                    account_move_line.with_context(check_move_validity=False).create(move_line_detail)
                    # get parent of payment method
                    method = payment_obj.search([('account_payment_method_id', '=', payment.payment_method_id.id)])
                    if method:
                        for line in method:
                            move_line_detail = {
                                'name': line.name,
                                'debit': (payment.paid_total * line.percent) / 100,
                                'credit': 0.00,
                                'move_id': move_id.id,
                                'account_id': line.property_account_payment_method_id.id,
                                'ref': None,
                                'journal_id': deposit.journal_id.id,
                                'partner_id': deposit.partner_id.id,
                            }
                            account_move_line.with_context(check_move_validity=False).create(move_line_detail)

            # rounding
            if deposit.change_rounding:
                if not deposit.journal_id.default_debit_rounding_account_id:
                    raise UserError(_(
                        'Please set Rounding Account of Invoice Journal')
                    )
                move_line_detail = {
                    'name': 'Rounding',
                    'debit': deposit.change_rounding,
                    'credit': 0.00,
                    'move_id': move_id.id,
                    'account_id': deposit.journal_id.default_debit_rounding_account_id.id,
                    'ref': None,
                    'journal_id': deposit.journal_id.id,
                    'partner_id': deposit.partner_id.id,

                }
                account_move_line.with_context(check_move_validity=False).create(move_line_detail)

            move_id.post()

            return move_id

    @api.multi
    def action_cancel_draft(self):
        # go from canceled state to draft state
        self.write({
            'state': 'draft'
        })

        return True

    @api.model
    def tax_line_move_line_get(self):
        res = []
        # keep track of taxes already processed
        done_taxes = []
        # loop the invoice.tax.line in reversal sequence
        for tax_line in sorted(self.tax_line, key=lambda x: -x.sequence):
            if tax_line.amount:
                tax = tax_line.tax_id
                if tax.amount_type == "group":
                    for child_tax in tax.children_tax_ids:
                        done_taxes.append(child_tax.id)
                res.append({
                    'deposit_tax_line_id': tax_line.id,
                    'tax_line_id': tax_line.tax_id.id,
                    'type': 'tax',
                    'name': tax_line.name,
                    'price_unit': tax_line.amount,
                    'quantity': 1,
                    'price': tax_line.amount,
                    'account_id': tax_line.account_id.id,
                    'account_analytic_id': tax_line.account_analytic_id.id,
                    'invoice_id': self.id,
                    'tax_ids': [(6, 0, list(done_taxes))] if tax_line.tax_id.include_base_amount else []
                })
                done_taxes.append(tax.id)
        return res


class AccountDepositLine(models.Model):
    _name = 'account.deposit.line'

    @api.one
    @api.depends('deposit_line_tax_id', 'price_subtotal', 'product_id', 'total')
    def _compute_price(self):
        price = self.total
        taxes = self.deposit_line_tax_id.compute_all(
            price,
            self.deposit_id.currency_id,
            product=self.product_id,
            partner=self.deposit_id.partner_id
        )
        self.price_subtotal = taxes['total_excluded']
        if self.deposit_id:
            self.price_subtotal = self.deposit_id.currency_id.round(self.price_subtotal)

    def get_product(self):
        product_id = self.env['product.product']

        if self.deposit_id.type == 'out_deposit':
            product_id = product_id.search([
                ('name', '=', 'Deposit From Sale')
            ])
        elif self.deposit_id.type == 'in_deposit':
            product_id = product_id.search([
                ('name', '=', 'Deposit From Purchase')
            ])

        return product_id

    deposit_id = fields.Many2one(
        comodel_name='account.deposit',
        string='Deposit'
    )
    deposit_line_tax_id = fields.Many2many(
        comodel_name='account.tax',
        relation='account_deposit_line_tax',
        column1='deposit_line_id',
        column2='tax_id',
        string='Taxes',
    )
    price_subtotal = fields.Float(
        string='Amount',
        # digits=dp.get_precision('Account'),
        store=True,
        readonly=True,
        compute='_compute_price'
    )
    name = fields.Char(
        string='Description'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        default=get_product
    )
    total = fields.Float(
        string='Total'
    )

    @api.onchange('product_id')
    def onchange_product_id_change(self):
        product = self.product_id
        values = {}
        if product:
            values['name'] = product.partner_ref
            if self.deposit_id.type in 'out_deposit':
                account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
            else:
                account = product.property_account_expense_id or product.categ_id.property_account_expense_categ_id
            # account = fpos.map_account(account)

            if self.deposit_id.type in 'out_deposit':
                values['deposit_line_tax_id'] = product.taxes_id or account.tax_ids
                if product.description_sale:
                    values['name'] += '\n' + product.description_sale
            else:
                values['deposit_line_tax_id'] = product.supplier_taxes_id or account.tax_ids
                if product.description_purchase:
                    values['name'] += '\n' + product.description_purchase

        return {
            'value': values
        }


class AccountDepositTax(models.Model):
    _name = "account.deposit.tax"
    _description = "Deposit Tax"
    _order = 'sequence'

    @api.one
    @api.depends('base', 'base_amount', 'amount', 'tax_amount')
    def _compute_factors(self):
        self.factor_base = self.base_amount / self.base if self.base else 1.0
        self.factor_tax = self.tax_amount / self.amount if self.amount else 1.0

    deposit_id = fields.Many2one(
        comodel_name='account.deposit',
        string='Deposit Line',
        ondelete='cascade',
        index=True
    )
    name = fields.Char(
        string='Tax Description',
        required=True
    )
    tax_id = fields.Many2one(
        'account.tax',
        string='Tax',
        ondelete='restrict'
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Tax Account',
        required=True,
        domain=[
            ('user_type_id.type', 'not in', ['view', 'income', 'closed'])
        ]
    )
    account_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic account'
    )
    base = fields.Float(
        string='Base',
        # digits=dp.get_precision('Account')
    )
    amount = fields.Float(
        string='Amount',
        # digits=dp.get_precision('Account')
    )
    manual = fields.Boolean(
        string='Manual',
        default=True
    )
    sequence = fields.Integer(
        string='Sequence',
        help="Gives the sequence order when displaying a list of invoice tax."
    )
    base_amount = fields.Float(
        string='Base Code Amount',
        # digits=dp.get_precision('Account'),
        default=0.0
    )
    tax_amount = fields.Float(
        # string='Tax Code Amount', digits=dp.get_precision('Account'),
        default=0.0
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='account_id.company_id',
        store=True,
        readonly=True
    )
    factor_base = fields.Float(
        string='Multipication factor for Base code',
        compute='_compute_factors'
    )
    factor_tax = fields.Float(
        string='Multipication factor Tax code',
        compute='_compute_factors'
    )

    @api.multi
    def base_change(self, base, currency_id=False, company_id=False, date=False):
        factor = self.factor_base if self else 1
        company = self.env['res.company'].browse(company_id)
        if currency_id and company.currency_id:
            currency = self.env['res.currency'].browse(currency_id)
            currency = currency.with_context(date=date or fields.Date.context_today(self))
            base = currency.compute(base * factor, company.currency_id, round=False)
        return {
            'value': {
                'base_amount': base
            }
        }

    @api.multi
    def amount_change(self, amount, currency_id=False, company_id=False, date=False):
        factor = self.factor_tax if self else 1
        company = self.env['res.company'].browse(company_id)
        if currency_id and company.currency_id:
            currency = self.env['res.currency'].browse(currency_id)
            currency = currency.with_context(date=date or fields.Date.context_today(self))
            amount = currency.compute(amount * factor, company.currency_id, round=False)
        return {
            'value': {
                'tax_amount': amount
            }
        }

    @api.v8
    def compute(self, deposit):
        tax_grouped = {}
        currency = deposit.currency_id.with_context(date=deposit.date or fields.Date.context_today(deposit))
        company_currency = deposit.company_id.currency_id
        for line in deposit.deposit_line:

            taxes = line.deposit_line_tax_id.compute_all(
                (line.total * (1 - (0.0) / 100.0)),
                deposit.currency_id,
                1,
                line.product_id,
                deposit.partner_id
            )['taxes']

            for tax in taxes:
                val = {
                    'deposit_id': deposit.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'base': currency.round(line.total * 1),
                    'tax_id': tax['id'],
                }
                if deposit.type in ('in_deposit', 'out_deposit'):
                    val['base_amount'] = currency.compute(val['base'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'], company_currency, round=False)
                    val['account_id'] = tax['account_id'] or line.account_id.id
                    # val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_amount'] = currency.compute(val['base'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'], company_currency, round=False)
                    val['account_id'] = tax['refund_account_id'] or line.account_id.id
                    # val['account_analytic_id'] = tax['account_analytic_paid_id']

                key = (val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])

        return tax_grouped

    @api.v7
    def compute(self, cr, uid, deposit_id, context=None):
        recs = self.browse(cr, uid, [], context)
        invoice = recs.env['account.deposit'].browse(deposit_id)
        return recs.compute(invoice)

    @api.model
    def move_line_get(self, deposit_id):
        res = []

        query_str = """
            SELECT id,
                account_id,
                deposit_id,
                manual,
                company_id,
                amount as tax_amount,
                account_analytic_id,
                name,
                base_amount as amount
            FROM account_deposit_tax
            WHERE deposit_id = %s
        """

        self._cr.execute(query_str, (deposit_id,))

        for row in self._cr.dictfetchall():
            if not (row['amount'] or row['tax_amount']):
                continue
            res.append({
                'type': 'tax',
                'name': row['name'],
                'price_unit': row['amount'],
                'quantity': 1,
                'price': row['amount'] or 0.0,
                'account_id': row['account_id'],
                'account_analytic_id': row['account_analytic_id'],
            })
        return res


class AccountDepositPaymentLine(models.Model):
    _name = 'account.deposit.payment.line'

    payment_id = fields.Many2one(
        comodel_name='account.deposit',
        string='Deposit'
    )

    payment_method_id = fields.Many2one(
        comodel_name='account.payment.method.multi',
        string='Payment Method',
        required='True'
    )

    bank_id = fields.Many2one(
        comodel_name='res.bank',
        string="Bank"
    )

    paid_total = fields.Float(
        string='Total',
        required='True'
    )

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Payment Journal",
        required=True,
        index=True,
    )

    approve_code = fields.Char(
        string='Approve Code',
        digit=6,
    )

    tender = fields.Selection(
        string="Tender",
        selection=[
            ('VISA', 'VISA'),
            ('MAST', 'MAST'),
            ('TPNC', 'TPNC'),
            ('JCB', 'JCB'),
            ('KBANK', 'KBANK'),
            ('CUPC', 'CUPC'),
            ('QKBN', 'QKBN'),
        ],
        default='VISA',
    )

    credit_card_no = fields.Char(
        string='Credit Card No.',
        digit=16,
    )

    is_credit_card = fields.Boolean(
        string="",
        related='journal_id.is_credit_card'
    )

    credit_card_no_encrypt = fields.Char(
        string='Credit Card No.',
        digit=16,
        compute='_credit_card_encrypt',
    )

    @api.multi
    @api.depends('credit_card_no')
    def _credit_card_encrypt(self):
        for record in self:
            if record.credit_card_no:
                credit_card_font = record.credit_card_no[:6]
                credit_card_back = record.credit_card_no[-4:]
                credit_card_replace = 'x' * (len(record.credit_card_no) - 10)

                record.credit_card_no_encrypt = credit_card_font + credit_card_replace + credit_card_back
