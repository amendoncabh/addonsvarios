import logging

from odoo import api, models, _, fields

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    property_pos_id = fields.Many2one(
        comodel_name='account.account.template',
        required=True,
        string="POS for Account Move Sale")

    property_customer_invoice_abb_id = fields.Many2one(
        comodel_name='account.account.template',
        required=True,
        string="Customer Invoice for Account Move Out")

    property_account_rounding_id = fields.Many2one(
        comodel_name='account.account.template',
        required=True,
        string="POS Order Rounding for Account Move Sale"
    )

    property_account_deposit_id = fields.Many2one(
        comodel_name='account.account.template',
        required=True,
        string="Deposit Account"
    )

    #product :Account Properties, Account Stock Properties

    stock_input_account = fields.Many2one(
        comodel_name='account.account.template',
        required=True,
        string="Stock Input Account"
    )

    stock_output_account = fields.Many2one(
        comodel_name='account.account.template',
        required=True,
        string="Stock Output Account"
    )

    stock_valuation_account = fields.Many2one(
        comodel_name='account.account.template',
        required=True,
        string="Stock Valuation Account"
    )

    property_stock_return_account = fields.Many2one(
        comodel_name='account.account.template',
        required=True,
        string="Stock Return Account"
    )
    expense_refund_account = fields.Many2one(
        comodel_name='account.account.template',
        required=True,
        string="Expense Refund Account"
    )



    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):

        journals_dict_add = [
            {
                'name': _(company.company_code_account + ' Customer Invoice ABB'),
                'type': 'sale',
                'code': 'PIV',
                'favorite': True,
                'sequence': 10
            },
            {
                'name': _(company.company_code_account + ' POS Sale Journal'),
                'type': 'sale',
                'code': 'POSS',
                'favorite': False,
                'sequence': 11
            },
            {
                'name': _('Receive Journal'),
                'type': 'cash',
                'code': 'RV',
                'option': 'sale',
                'favorite': False,
                'sequence': 21
            },
            {
                'name': _('Payment Journal'),
                'type': 'cash',
                'code': 'PV',
                'option': 'purchase',
                'favorite': False,
                'sequence': 22
            }
        ]

        if journals_dict != None:
            journals_dict.extend(journals_dict_add)

        res_dict = super(AccountChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict)

        for res in res_dict:
            code = res.get('code', False)
            if res['type'] in ['sale', 'purchase']:
                res['refund_sequence'] = True
            res['update_posted'] = True

            if code == 'POSS':
                res['default_credit_account_id'] = acc_template_ref.get(self.property_pos_id.id)
                res['default_debit_account_id'] = acc_template_ref.get(self.property_pos_id.id)
                res['default_credit_rounding_account_id'] = acc_template_ref.get(self.property_account_rounding_id.id)
                res['default_debit_rounding_account_id'] = acc_template_ref.get(self.property_account_rounding_id.id)
            elif code == 'PIV':
                res['default_credit_account_id'] = acc_template_ref.get(self.property_customer_invoice_abb_id.id)
                res['default_debit_account_id'] = acc_template_ref.get(self.property_customer_invoice_abb_id.id)
            elif code == 'BILL':
                res['code'] = 'AP'
            elif code == 'INV':
                res['code'] = 'SI'
            elif code == 'STJ':
                res['code'] = 'JV'

            #stam all detail journals
            res['default_credit_rounding_account_id'] = acc_template_ref.get(self.property_account_rounding_id.id)
            res['default_debit_rounding_account_id'] = acc_template_ref.get(self.property_account_rounding_id.id)

            res['default_credit_deposit_account_id'] = acc_template_ref.get(self.property_account_deposit_id.id)
            res['default_debit_deposit_account_id'] = acc_template_ref.get(self.property_account_deposit_id.id)


        return res_dict

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        super(AccountChartTemplate, self).generate_journals(acc_template_ref, company, journals_dict)
        journal_ids = self.env['account.journal'].search([
            ('company_id', '=', company.id),
        ])

        def set_prefix_refund_sequence(journal_id, code):
            prefix_list = journal_id.refund_sequence_id.prefix.split('/')
            prefix_list[0] = code
            prefix = '/'.join(prefix_list)
            journal_id.refund_sequence_id.update({
                'prefix': prefix,
            })

        for journal_id in journal_ids:
            if journal_id.code == 'PIV':
                set_prefix_refund_sequence(journal_id, 'PCN')
            elif journal_id.code == 'SI':
                set_prefix_refund_sequence(journal_id, 'CN')
            elif journal_id.code == 'AP':
                set_prefix_refund_sequence(journal_id, 'RTV')

    def generate_properties(self, acc_template_ref, company, property_list=None):
        super(AccountChartTemplate, self).generate_properties(acc_template_ref=acc_template_ref, company=company)

        PropertyObj = self.env['ir.property']  # Property Stock Journal
        todo_list = [  # Property Stock Accounts
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
            'property_stock_return_account',
            'expense_refund_account',
        ]

        for record in todo_list:
            account = getattr(self, record)

            if record == 'property_stock_account_input_categ_id':
                value = acc_template_ref.get(self.stock_input_account.id)
            elif record == 'property_stock_account_output_categ_id':
                value = acc_template_ref.get(self.stock_output_account.id)
            elif record == 'property_stock_valuation_account_id':
                value = acc_template_ref.get(self.stock_valuation_account.id)
            elif record == 'property_stock_return_account':
                value = acc_template_ref.get(self.property_stock_return_account.id)
            elif record == 'expense_refund_account':
                value = acc_template_ref.get(self.expense_refund_account.id)
            else:
                value = account and 'account.account,' + str(acc_template_ref[account.id]) or False

            if value:
                company.write({record: value})

                field = self.env['ir.model.fields'].search(
                    [('name', '=', record), ('model', '=', 'product.category'), ('relation', '=', 'account.account')],
                    limit=1)
                vals = {
                    'name': record,
                    'company_id': company.id,
                    'fields_id': field.id,
                    'value': value,
                }

                properties = PropertyObj.search([('name', '=', record), ('company_id', '=', company.id)])
                if properties:
                    # the property exist: modify it
                    properties.write(vals)
                else:
                    # create the property
                    PropertyObj.create(vals)

    @api.multi
    def create_record_with_xmlid(self, company, template, model, vals):
        # Create a record for the given model with the given vals and
        # also create an entry in ir_model_data to have an xmlid for the newly created record
        # xmlid is the concatenation of company_id and template_xml_id
        ir_model_data = self.env['ir.model.data']
        template_xmlid = ir_model_data.search([('model', '=', template._name), ('res_id', '=', template.id)])
        if template_xmlid:
            new_xml_id = str(company.id) + '_' + template_xmlid.name
        else:
            new_xml_id = False

        return ir_model_data._update(model, template_xmlid.module, vals, xml_id=new_xml_id, store=True, noupdate=True,
                                     mode='init', res_id=False)
