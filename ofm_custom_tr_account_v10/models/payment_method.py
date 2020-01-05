# -*- coding: utf-8 -*-

from odoo import models, api, fields


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method.multi'

    type = fields.Selection(
        selection=[
            ('cash', 'Cash'),
            ('cheque', 'Cheque'),
            ('bank', 'Bank'),
            ('creditcard', 'Credit Card'),
            ('fee', 'Fee'),
            ('discount', 'Discount'),
            ('wht', 'WHT'),
            ('ap', 'AP'),
            ('ar', 'AR'),
            ('writeoff', 'Write off'),
            ('other', 'Other')
        ],
        string='Payment Type',
        required=True
    )

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        required=True,
        index=True,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        # compute='get_company_id',
        # readonly=True,
        required=False,
        default=lambda self: self.env.user.company_id,
    )

    payment_credit_term = fields.Boolean(
        string="Payment Type Credit Term",
        default=False,
    )

    @api.onchange('company_id')
    def onchange_get_domain_company(self):
        self.journal_id = False
        self.property_account_payment_method_id = False
        self.property_credit_account_payment_method_id = False
        self.account_payment_method_id = False

        res_domain = {
            'domain': {
                'journal_id': [
                    ('company_id', '=', self.company_id.id)
                ],
                'property_account_payment_method_id': [
                    ('company_id', '=', self.company_id.id)
                ],
                'property_account_credit_payment_method_id': [
                    ('company_id', '=', self.company_id.id)
                ],
                'account_payment_method_id': [
                    ('company_id', '=', self.company_id.id)
                ]
            },
        }

        return res_domain

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        invoice_line = self.env.context.get('invoice_line', False)
        type_payment_to_customer = self.env.context.get('type_payment_to_customer', False)
        args_name = [arg for arg in args if arg[0] == 'name' and len(arg[2]) > 0]
        if all([
            invoice_line,
            type_payment_to_customer == 'outbound',
        ]):
            include_model = self.env.context.get('include_model', False)
            cn_ids = self.get_payment_method_from_model_line(include_model, invoice_line)

            if args_name:
                name_search = args_name and args_name[0][2] or ''
            else:
                name_search = ''

            payment_ids = self.get_payment_by_query(name_search, cn_ids)

            if len(payment_ids) > 0:
                args += [('id', 'in', payment_ids)]
            else:
                args = [('id', '=', 0)]

        return super(AccountPaymentMethod, self).search(args, offset=offset, limit=limit, order=order, count=count)

    def get_payment_by_query(self, name, cn_ids):

        name = name.lower()

        str_cn_ids = ','.join(map(str, cn_ids))

        if cn_ids:
            query_where_product_product = """
                    cn.id in ({0})
            """.format(str_cn_ids)
        else:
            query_where_product_product = ''

        if len(name) > 0:
            query_where_product_product += """
                and lower(apmm.name) like '%{0}%'
            """.format(name)

        query_tb_payment = """
            select adp.payment_method_id, adp.tender, adp.credit_card_no
            from account_invoice cn
            inner join sale_order so on so.id = cn.so_id
            inner join account_deposit ad on ad.sale_id = so.id and ad.state in ('paid')
            inner join account_deposit_payment_line adp on adp.payment_id = ad.id
            inner join account_payment_method_multi apmm on apmm.id = adp.payment_method_id
            where {0}
        """.format(query_where_product_product)

        self.env.cr.execute(query_tb_payment)
        result_model = self.env.cr.dictfetchall()

        payment_ids = []

        for result_item in result_model:
            payment_method_id = result_item.get('payment_method_id', False)

            if payment_method_id:
                payment_ids.append(payment_method_id)

        return payment_ids

    def get_payment_method_from_model_line(self, model, model_line):
        model_line_ids = []
        cn_ids = []

        for item in model_line:
            if model:
                if model == self._name:
                    model_line_ids.append(item[1])
                else:
                    if item[0] == 4:
                        model_line_ids.append(item[1])
                    elif item[0] == 2:
                        continue
                    else:
                        invoice_id = item[2].get('invoice_id', False)
                        if invoice_id:
                            cn_ids.append(invoice_id)

        if len(model_line_ids) > 0:
            model_db = model.replace('.', '_')
            query_model_line_ids = ''

            for model_line_id in model_line_ids:
                query_model_line_ids += str(model_line_id)
                query_model_line_ids += ','

            query_model_line_ids = query_model_line_ids[:-1]

            str_qeury = "\n".join([
                "SELECT id,invoice_id",
                "FROM {0}".format(model_db),
                "WHERE id IN ({0})".format(query_model_line_ids)
            ])

            self.env.cr.execute(str_qeury)

            result_model = self.env.cr.dictfetchall()

            for result_item in result_model:
                invoice_id = result_item.get('invoice_id', False)

                if invoice_id:
                    cn_ids.append(invoice_id)

        return cn_ids

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=160):
        account_payment_method_ids = self.search(
            [
                ('name', 'ilike', name),
            ] + args,
            limit=limit
        )
        return account_payment_method_ids.sudo().name_get()
