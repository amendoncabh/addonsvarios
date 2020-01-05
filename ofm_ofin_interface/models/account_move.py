# -*- coding: tis-620 -*-

from datetime import datetime

from pytz import timezone

from odoo import models, tools, fields

tools.config['ofin_dir'] = tools.config.get('ofin_dir', '/opt/ofin_production/')


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_get_data_already = fields.Boolean(
        'Interface Already',
        copy=False,
        readonly=True,
        default=False,
    )

    parent_id = fields.Many2one(
        'account.move',
        string="Parent move",
        readonly=True
    )

    is_gen_credit_card_already = fields.Boolean(
        'Credit Card Interface',
        copy=False,
        readonly=True,
        default=False,
    )

    def convert_query_result_to_dict(self, query_str, keys, object_values={}):

        self.env.cr.execute(query_str)
        query_results = self.env.cr.dictfetchall()

        for item in query_results:
            key = (tuple(item[key] for key in keys))
            invoice_item = object_values.get(key, False)
            if not invoice_item:
                object_values.update({
                    key: {
                        'id': item['id']
                    }
                })

        return object_values

    def search_key_in_dict(self, keys, object_values, object_browse):

        object_value = object_values.get(keys, False)

        if object_value:
            return object_browse.browse(object_value['id'])
        else:
            return False

    def create_vi_sor_and_pay_franchise(self):
        self.create_vendor_invoice_to_sor()

    def create_vendor_invoice_to_sor(self):
        franchise_invoice_id = self._context.get('franchise_invoice_id', False)

        pos_branch = self.env['pos.branch']
        account_account = self.env['account.account']

        query_str = """
            select id,code,company_id 
            from account_account
        """

        account_value_ids = self.convert_query_result_to_dict(
            query_str,
            ('code', 'company_id')
        )

        account_journal = self.env['account.journal']
        ir_config_param = self.env['ir.config_parameter']

        account_invoice = self.env['account.invoice']

        account_payment_method_multi = self.env['account.payment.method.multi']
        account_payment = self.env['account.payment']
        account_payment_method = self.env['account.payment.method']
        account_tax = self.env['account.tax']

        omni_franchise_store_code = ir_config_param.get_param('omni_franchise_store_code', False)

        omni_branch = pos_branch.search(
            [
                ('branch_code', '=', omni_franchise_store_code)
            ],
            limit=1
        )

        if omni_branch:

            omni_pos_company_id = omni_branch.pos_company_id.id

            sor_invoice_account_id = self.search_key_in_dict(
                (
                    '21410050',
                    omni_pos_company_id
                ),
                account_value_ids,
                account_account
            )

            sor_tax_id = account_tax.search(
                [
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', omni_pos_company_id)
                ],
                limit=1
            )

            omni_journal_id = account_journal.search(
                [
                    ('company_id', '=', omni_branch.pos_company_id.id),
                    ('type', '=', 'purchase')
                ]
            )

            vendor_invoice_domain = [
                ('state', '=', 'open'),
                ('type', '=', 'in_invoice'),
                ('branch_id.branch_code', '!=', omni_franchise_store_code)
            ]

            if franchise_invoice_id:
                vendor_invoice_domain += [('id', '=', franchise_invoice_id)]

            vendor_invoices_franchise = account_invoice.search(
                vendor_invoice_domain,
                order="id desc"
            )

            # find for use in account_payment not important
            account_payment_method_id = account_payment_method.search(
                [
                    ('payment_type', '=', 'outbound'),
                    ('code', '=', 'manual'),
                ]
            )

            for vendor_invoice_franchise in vendor_invoices_franchise:
                franchise_branch_id = vendor_invoice_franchise.branch_id

                # find account payment method multi if not found create new object and if not equal assign new
                account_payment_method_multi_id = account_payment_method_multi.with_context(
                    force_company=vendor_invoice_franchise.user_id.company_id.id
                ).search(
                    [
                        ('type', '=', 'ap'),
                    ],
                    limit=1,
                )

                account_account_payment_method_id = self.search_key_in_dict(
                    (
                        '11315710',
                        vendor_invoice_franchise.user_id.company_id.id
                    ),
                    account_value_ids,
                    account_account
                )

                if not account_account_payment_method_id:
                    continue

                if account_payment_method_multi_id:
                    if account_payment_method_multi_id.property_account_payment_method_id:
                        property_account_payment_method_id = account_payment_method_multi_id.property_account_payment_method_id
                        if property_account_payment_method_id.code != '11315710':
                            account_payment_method_multi_id.update({
                                'property_account_payment_method_id': account_account_payment_method_id,
                            })
                    else:
                        account_payment_method_multi_id.update({
                            'property_account_payment_method_id': account_account_payment_method_id,
                        })
                else:
                    account_payment_method_multi_id = account_payment_method_multi.with_context(
                        force_company=vendor_invoice_franchise.user_id.company_id.id
                    ).create({
                        'type': 'ap',
                        'property_account_payment_method_id': account_account_payment_method_id,
                        'name': 'CASH',
                    })

                franchise_journal_id = account_journal.search(
                    [
                        ('company_id', '=', franchise_branch_id.pos_company_id.id),
                        ('type', '=', 'bank')
                    ]
                )
                payment_partner_id = vendor_invoice_franchise.partner_id
                sor_partner_id = vendor_invoice_franchise.partner_id

                refund_ids = []

                if vendor_invoice_franchise.child_ids:
                    refund_is_wrong = False
                    for child_id in vendor_invoice_franchise.child_ids:
                        if child_id.state != 'open':

                            if all([
                                child_id.state == 'draft',
                                child_id.vendor_invoice_date,
                                child_id.reference,
                            ]):
                                print 'pass'
                                refund_ids.append(child_id)
                                child_id.action_invoice_open()
                                child_id.reconcile_refund()
                                # child_id.env.cr.commit()
                            else:
                                print 'break'
                                refund_is_wrong = True
                                break
                        else:
                            print 'pass'
                            refund_ids.append(child_id)
                            child_id.reconcile_refund()
                            # child_id.env.cr.commit()

                    if refund_is_wrong:
                        continue

                sor_vendor_invoice_id = vendor_invoice_franchise.with_context(
                    tracking_disable=True,
                    force_company=omni_branch.pos_company_id.id
                ).copy({
                    'picking_id': False,
                    'company_id': omni_branch.pos_company_id.id,
                    'partner_id': sor_partner_id.id,
                    'journal_id': omni_journal_id.id,
                    'branch_id': omni_branch.id,
                    'origin': vendor_invoice_franchise.number,
                    'account_id': sor_invoice_account_id.id,
                    'reference': vendor_invoice_franchise.reference,
                    'vendor_invoice_date': vendor_invoice_franchise.vendor_invoice_date
                })
                for invoice_line_id in sor_vendor_invoice_id.invoice_line_ids:
                    tax_existing = False
                    invoice_line_id.update({
                        'purchase_line_id': False
                    })
                    if invoice_line_id.invoice_line_tax_ids:
                        tax_existing = True
                    invoice_line_id.with_context(
                        tracking_disable=True,
                        force_company=omni_branch.pos_company_id.id
                    )._onchange_product_id()
                    if tax_existing is False:
                        invoice_line_id.invoice_line_tax_ids = False
                sor_vendor_invoice_id._onchange_invoice_line_ids()
                sor_vendor_invoice_id.compute_taxes()
                sor_vendor_invoice_id.action_invoice_open()

                if refund_ids:
                    for refund_id in refund_ids:
                        sor_refund_invoice_id = refund_id.with_context(
                            tracking_disable=True,
                            force_company=omni_branch.pos_company_id.id
                        ).copy({
                            'picking_id': False,
                            'parent_invoice_id': sor_vendor_invoice_id.id,
                            'company_id': omni_branch.pos_company_id.id,
                            'partner_id': sor_partner_id.id,
                            'journal_id': omni_journal_id.id,
                            'branch_id': omni_branch.id,
                            'origin': refund_id.number,
                            'account_id': sor_invoice_account_id.id,
                            'reference': refund_id.reference,
                            'vendor_invoice_date': refund_id.vendor_invoice_date
                        })

                        for invoice_line_id in sor_refund_invoice_id.invoice_line_ids:
                            invoice_line_id.update({
                                'invoice_line_tax_ids': [(6, 0, [sor_tax_id.id])],
                                'account_id': omni_journal_id.default_credit_account_id.id,
                                'purchase_line_id': False
                            })
                        for tax_line_id in sor_refund_invoice_id.tax_line_ids:
                            tax_line_id.update({
                                'tax_id': sor_tax_id.id,
                                'account_id': sor_tax_id.account_id.id
                            })
                            # tax_line_id.env.cr.commit()

                        sor_refund_invoice_id.compute_taxes()
                        sor_refund_invoice_id.action_invoice_open()
                        sor_refund_invoice_id.env.cr.commit()

                # vendor_invoice_franchise.env.cr.commit()

                prepare_payment_invoice_line = [
                    (
                        0, 0,
                        {
                            'invoice_id': vendor_invoice_franchise.id,
                            'paid_amount': vendor_invoice_franchise.residual,
                        }
                    )
                ]

                prepare_payment_line = [
                    (
                        0, 0,
                        {
                            'payment_method_id': account_payment_method_multi_id.id,
                            'paid_total': vendor_invoice_franchise.residual,
                        }
                    )
                ]

                if vendor_invoice_franchise.residual > 0:
                    account_payment_id = account_payment.create_payment_from_account_invoice(
                        vendor_invoice_franchise
                    )

                    account_payment_id.write({
                        'payment_line': prepare_payment_line
                    })

                    account_payment_id.post()

                    account_payment_id.env.cr.commit()

                sor_vendor_invoice_id.env.cr.commit()

        return True

    def get_vendor_invoice_open(self):
        return True

    def _prepare_account_move_line(self, move_line, amount, credit_account_id, debit_account_id):

        debit_line_vals = {
            'name': move_line.name,
            'ref': move_line.move_id.name,
            'partner_id': move_line.partner_id and move_line.partner_id.id or None,
            'debit': amount,
            'credit': 0,
            'account_id': debit_account_id.id,
        }
        credit_line_vals = {
            'name': move_line.name,
            'ref': move_line.move_id.name,
            'partner_id': move_line.partner_id and move_line.partner_id.id or None,
            'debit': 0,
            'credit': amount,
            'account_id': credit_account_id.id,
        }

        res = [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]

        return res

    def prepare_account_move(self, move_line, credit_account_id, debit_account_id, account_journal_sor, omni_branch):

        account_move = self

        move_lines = self._prepare_account_move_line(
            move_line,
            move_line.debit,
            credit_account_id,
            debit_account_id,
        )

        move_val = {
            'branch_id': omni_branch.id,
            'journal_id': account_journal_sor.id,
            'line_ids': move_lines,
            'date': move_line.move_id.date,
            'ref': move_line.move_id.name,
            'parent_id': move_line.move_id.id,
            'company_id': credit_account_id.company_id.id
        }

        new_account_move = account_move.create(move_val)

        return new_account_move

    def create_sor_received_instead(self):

        ir_config_param = self.env['ir.config_parameter']
        account_account = self.env['account.account']
        account_journal = self.env['account.journal']
        pos_branch = self.env['pos.branch']

        account_code_credit_card = ir_config_param.get_param(
            'credit_card_code_account',
            False
        )

        account_code_credit_sor = ir_config_param.get_param(
            'credit_card_account_credit_sor',
            False
        )

        account_code_debit_sor = ir_config_param.get_param(
            'credit_card_account_debit_sor',
            False
        )

        omni_franchise_store_code = ir_config_param.get_param(
            'omni_franchise_store_code',
            False
        )

        omni_branch = pos_branch.search(
            [
                ('branch_code', '=', omni_franchise_store_code)
            ],
            limit=1
        )

        account_account_ids = account_account.search(
            [
                ('code', '=', account_code_credit_card),
            ],
        )

        account_code_credit_sor = account_account.search(
            [
                ('code', '=', account_code_credit_sor),
                ('company_id.parent_company_id', '=', False)
            ],
            limit=1
        )

        account_code_debit_sor = account_account.search(
            [
                ('code', '=', account_code_debit_sor),
                ('company_id.parent_company_id', '=', False)
            ],
            limit=1
        )

        account_journal_sor = account_journal.search(
            [
                ('is_credit_card', '=', True),
                ('company_id.parent_company_id', '=', False)
            ],
            limit=1
        )

        if account_account_ids and account_code_credit_sor and account_code_debit_sor:
            account_map_company = {}
            for account_account_id in account_account_ids:
                key = account_account_id.company_id.id
                is_key_exist = account_map_company.get(key, False)
                if not is_key_exist:
                    account_map_company.update({
                        key: account_account_id
                    })

            for key, account_id in account_map_company.items():
                company_id = key
                move_line_ids = self.env['account.move.line'].search(
                    [
                        ('company_id', '=', company_id),
                        ('account_id', '=', account_id.id),
                        ('debit', '!=', 0),
                        ('move_id.is_gen_credit_card_already', '=', False)
                    ],
                    order='move_id'
                )

            for move_line_id in move_line_ids:
                new_account_move = self.prepare_account_move(
                    move_line_id,
                    account_code_credit_sor,
                    account_code_debit_sor,
                    account_journal_sor,
                    omni_branch,
                )
                new_account_move.post()
                move_line_id.move_id.write({
                    'is_gen_credit_card_already': True
                })

                self.env.cr.commit()

    def get_gl_gr_to_file(self):

        type_of_sale = [
            'pos-sale',
            'pos-inv-return',
            'pos-received-instead',
            'cost-good-sold'
        ]

        type_of_inventory = [
            'receive',
            'return',
        ]

        def round_by_tools(amount):
            return tools.float_round(
                amount,
                precision_rounding=0.01
            )

        ofin_log_data_obj = self.env['ofin.log.data.to.file']
        account_invoice = self.env['account.invoice']
        account_move = self.env['account.move']

        tr_convert = self.env['tr.convert']
        now_utc = tr_convert.convert_datetime_to_bangkok(datetime.now(timezone('UTC')))

        query_str = '''
            with 
            list_type_sale as (
                select 'pos-sale'
                union 
                select 'pos-inv-return'
                union
                select 'pos-received-instead'
                union
                select 'cost-good-sold'
                ),
            list_type_inv_receive as (
                select 'ap-inv-receive'
                union 
                select 'sp-inv-receive'
                ),
            list_type_inv_return as (
                select 'ap-inv-return'
                union 
                select 'sp-inv-return'
                ),
            invoice_with_po as (
                select 
                ail.invoice_id,
                pol.order_id
                from 
                account_invoice_line ail
                inner join account_invoice ai on ai.id = ail.invoice_id
                inner join purchase_order_line pol on pol.id = ail.purchase_line_id
                inner join account_move am on am.id = ai.move_id
                inner join res_company rc on rc.id = ai.company_id
                where 
                (ai.state = 'paid' and rc.parent_company_id is not null) 
                and (am.is_get_data_already = False or am.is_get_data_already is null)
                group by 
                ail.invoice_id,
                pol.order_id
                ),
            temp_account_move as (
                select 
                sp.id as object_id,
                am.id as am_id,
                'sp-inv-receive' as gl_type,
                sp.name,
                'ODO-INV' as source
                from 
                stock_picking sp
                inner join account_move am on am.id = sp.account_move_id
                inner join stock_location sl on sl.id = sp.location_id
                inner join purchase_order po on po.group_id = sp.group_id
                inner join res_company rc on rc.id = am.company_id
                where 
                (am.is_get_data_already = False or am.is_get_data_already is null)
                and po.state in ('purchase', 'done')
                and rc.select_to_interface_ofin = True 
                and sl.usage = 'supplier'
            
                union
            
                select 
                sp_rt.id as object_id,
                am.id as am_id,
                'sp-inv-return' as gl_type,
                sp_rt.name,
                'ODO-INV' as source
                from 
                stock_picking sp_rt
                inner join stock_picking sp on sp.name = sp_rt.origin
                inner join account_move am on am.id = sp_rt.account_move_id
                inner join stock_location sl on sl.id = sp_rt.location_dest_id
                inner join purchase_order po on po.group_id = sp.group_id
                inner join res_company rc on rc.id = am.company_id
                where 
                (am.is_get_data_already = False or am.is_get_data_already is null)
                and po.state in ('purchase', 'done')
                and rc.select_to_interface_ofin = True 
                and sl.usage = 'supplier'
            
                union
            
                select 
                ai.id as object_id,
                am.id as am_id,
                'ap-inv-receive' as gl_type,
                ai.number as name,
                'ODO-MER' as source
                from 
                account_invoice ai
                inner join account_move am on am.id = ai.move_id
                inner join invoice_with_po inv_po on inv_po.invoice_id = ai.id
                inner join purchase_order po on po.id = inv_po.order_id
                inner join res_company rc on rc.id = am.company_id
                where parent_invoice_id is null 
                and po.state in ('purchase', 'done')
                and rc.select_to_interface_ofin = True 
            
                union
            
                select 
                ai_cn.id as object_id,
                am.id as am_id,
                'ap-inv-return' as gl_type,
                ai_cn.number as name,
                'ODO-MER' as source
                from account_invoice ai_cn 
                inner join account_move am on am.id = ai_cn.move_id
                inner join invoice_with_po inv_po on inv_po.invoice_id = ai_cn.id
                inner join purchase_order po on po.id = inv_po.order_id
                inner join res_company rc on rc.id = am.company_id
                where parent_invoice_id is not null 
                and po.state in ('purchase', 'done')
                and rc.select_to_interface_ofin = True 
            
                union
            
                select 
                poss.id as object_id,
                accm.id as am_id,
                'pos-sale' as gl_type,
                poss.name as name,
                'EPOS SALES' as source
                from account_move accm
                inner join pos_order pos on pos.account_move = accm.id
                inner join pos_session poss on poss.id = pos.session_id
                inner join res_company rc on rc.id = pos.company_id
                where rc.parent_company_id is not null
                and (accm.is_get_data_already = False or accm.is_get_data_already is null)
                and poss.state in ('closed')
                and rc.select_to_interface_ofin = True
                group by accm.id,poss.id
            
                union
            
                select 
                sp.id as object_id,
                accm.id as am_id,
                'cost-good-sold' as gl_type,
                sp.name as name,
                'EPOS SALES' as source
                from account_move accm
                inner join stock_picking sp on sp.account_move_id = accm.id
                inner join stock_picking sp_pos on sp_pos.group_id = sp.group_id
                inner join pos_order pos on pos.picking_id = sp_pos.id
                inner join pos_session poss on poss.id = pos.session_id
                inner join res_company rc on rc.id = pos.company_id
                where rc.parent_company_id is not null
                and (accm.is_get_data_already = False or accm.is_get_data_already is null)
                and poss.state in ('closed')
                and rc.select_to_interface_ofin = True
                group by accm.id,sp.id
            
                union
            
                select 
                ai.id as object_id,
                accm.id as am_id,
                'pos-inv-return' as gl_type,
                ai.name as name,
                'EPOS SALES' as source
                from account_move accm
                inner join account_invoice ai on ai.move_id = accm.id
                inner join pos_order pos on pos.invoice_id = ai.id
                inner join pos_session poss on poss.id = pos.session_id
                inner join res_company rc on rc.id = pos.company_id
                where rc.parent_company_id is not null
                and (accm.is_get_data_already = False or accm.is_get_data_already is null)
                and poss.state in ('closed')
                and rc.select_to_interface_ofin = True
                group by accm.id,ai.id
            
                union
            
                select 
                accm.id as object_id,
                accm.id as am_id,
                'pos-received-instead' as gl_type,
                accm.ref as name,
                'EPOS SALES' as source
                from account_move accm
                inner join res_company rc on rc.id = accm.company_id
                where rc.parent_company_id is null
                and accm.parent_id is not null
                and (accm.is_get_data_already = False or accm.is_get_data_already is null)
                and rc.select_to_interface_ofin = True
                group by accm.id
            
                )
            select 
            po_b.branch_code,
            temp_am.gl_type,
            case
            when acca.code like '21405250' or pt.default_code like 'KE00%'
            then '29310'
            when acca.code like '4110505%' or acca.code like '4120505%'
            then pt.cp_cid_ofm
            else '99999'
            end as cost_center,
            
            acca.code,
            
            case
            when acca.code like '21410050%' and rp.oracle_branch_code is not null and length(rp.oracle_branch_code) > 0
            then rp.oracle_branch_code
            when parent_move.id is not null and sum(accml.credit) <> 0 
            then parent_branch.branch_code
            when acca.sub_account is not null
            then acca.sub_account
            else '999999'
            end as sub_account,
            
            TO_CHAR(accm.date::date, 'DDMMYY') as date,
            
            TO_CHAR(accm.date::date, 'YYMMDD') as file_date,
            
            sum(accml.debit) as debit,
            
            sum(accml.credit) as credit,
            
            temp_am.source as source,
            
            case 
            when temp_am.gl_type in (select * from list_type_inv_receive)
            then 'Local-purchase'
            when temp_am.gl_type in (select * from list_type_sale)
            then concat(po_b.branch_code, '-POS-Sales')
            when temp_am.gl_type in (select * from list_type_inv_return)
            then 'Purchase-Return'
            end as Category,
            
            concat(temp_am.source,'-',TO_CHAR((now() + interval '7 hours')::date, 'YYYYMMDD')) as batch_name,
            
            'blank_10' as cfs_flag,
            
            case
            when temp_am.gl_type = 'pos-sale'
            then 'Journal Import Create'
            else accml.name  
            end as description,
            
            case 
            when temp_am.gl_type in (select * from list_type_inv_receive)
            then 'Local-purchase'
            when temp_am.gl_type in (select * from list_type_sale)
            then concat(po_b.branch_code, '-POS-Sales')
            when temp_am.gl_type in (select * from list_type_inv_return)
            then 'Purchase-Return'
            end as journal_name,
            
            accm.id as account_move_id
            from 
            temp_account_move temp_am
            inner join account_move accm on accm.id = temp_am.am_id
            inner join pos_branch po_b on po_b.id = accm.branch_id
            inner join account_move_line accml on accml.move_id = accm.id
            inner join account_account acca on acca.id = accml.account_id
            left join res_partner rp on rp.id = accml.partner_id
            left join account_move parent_move on parent_move.id = accm.parent_id
            left join pos_branch parent_branch on parent_branch.id = parent_move.branch_id
            left join product_product pp on pp.id = accml.product_id
            left join product_template pt on pt.id = pp.product_tmpl_id
            where credit <> 0 or debit <> 0
            group by
            rp.id,
            po_b.id,
            acca.id,
            accm.id,
            temp_am.gl_type,
            accml.name,
            temp_am.am_id,
            temp_am.source,
            pt.default_code,
            pt.cp_cid_ofm,
            parent_move.id,
            parent_branch.id
            order by 
            accm.date,
            temp_am.am_id,
            acca.id
        '''
        self.env.cr.execute(query_str)
        data_gl_gr = self.env.cr.dictfetchall()

        group_gl_gr_move = {}

        for gl_gr in data_gl_gr:
            key = (
                gl_gr['account_move_id']
            )
            if group_gl_gr_move.get(key, False):
                group_gl_gr_move[key]['move_lines'].append(gl_gr)
            else:
                group_gl_gr_move.update({
                    key: {
                        'move_lines': [gl_gr],
                        'branch_code': gl_gr['branch_code'],
                        'file_date': gl_gr['file_date'],
                        'gl_type': gl_gr['gl_type']
                    }
                })

        now_query_str = '-'.join(
            [
                str(now_utc.year),
                str(now_utc.month),
                str(now_utc.day)
            ]
        )

        group_res_id_branch, res_id_log_amount = account_invoice.prepare_data_for_compare_amount_of_data(
            'account.move',
            now_query_str
        )

        head_log_values = {}

        for move_id, gl_gr_list in group_gl_gr_move.items():

            move_obj_id = account_move.browse(move_id)

            if group_res_id_branch.get(gl_gr_list['branch_code'], False):
                if move_id in group_res_id_branch[gl_gr_list['branch_code']]:
                    log_amount = res_id_log_amount[move_id]
                    log_amount += 1
                    log_amount_str = '{:02d}'.format(log_amount)
                else:
                    log_amount_str = '{:02d}'.format(1)
            else:
                log_amount_str = '{:02d}'.format(1)

            if gl_gr_list['gl_type'] in type_of_sale:
                title_file_name = u'ZXMSAL'
            else:
                title_file_name = u'ZXMINV'

            file_name = ''.join([
                title_file_name,
                gl_gr_list['branch_code'][-2:],
                gl_gr_list['file_date'],
                log_amount_str
            ])

            file_name_val = file_name + '.VAL'
            file_name_dat = file_name + '.DAT'

            detail_move_dat_file = []

            sum_debit_gr_gl = 0
            sum_credit_gr_gl = 0

            for gl_gr in gl_gr_list['move_lines']:
                debit = round_by_tools(gl_gr['debit'])
                credit = round_by_tools(gl_gr['credit'])
                debit_amount = '{:012.2f}'.format(debit)
                credit_amount = '{:012.2f}'.format(credit)

                detail_line_dat_file_list = [
                    account_invoice.put_blank_string(gl_gr['branch_code']),
                    account_invoice.put_blank_string(gl_gr['cost_center']),
                    account_invoice.put_blank_string(gl_gr['code']),
                    account_invoice.put_blank_string(gl_gr['sub_account']),
                    account_invoice.put_blank_string(gl_gr['date']),
                    debit_amount,
                    credit_amount,
                    account_invoice.put_blank_string(gl_gr['source']).ljust(20),
                    account_invoice.put_blank_string(gl_gr['category']).ljust(20),
                    account_invoice.put_blank_string(gl_gr['batch_name']).ljust(20),
                    account_invoice.put_blank_string(gl_gr['cfs_flag']),
                    account_invoice.put_blank_string(gl_gr['description']).ljust(240),
                    account_invoice.put_blank_string(gl_gr['journal_name']).ljust(50),
                    '\n',
                ]
                sum_debit_gr_gl += round_by_tools(gl_gr['debit'])
                sum_credit_gr_gl += round_by_tools(gl_gr['credit'])

                detail_move_dat_file.append(''.join(detail_line_dat_file_list))

            diff_debit_credit_amount = round_by_tools(sum_debit_gr_gl - sum_credit_gr_gl)
            if diff_debit_credit_amount:
                if diff_debit_credit_amount > 0:
                    detail_line_dat_file_list[5] = '{:012.2f}'.format(0)
                    detail_line_dat_file_list[6] = '{:012.2f}'.format(diff_debit_credit_amount)
                    sum_credit_gr_gl += diff_debit_credit_amount
                else:
                    detail_line_dat_file_list[5] = '{:012.2f}'.format(abs(diff_debit_credit_amount))
                    detail_line_dat_file_list[6] = '{:012.2f}'.format(0)
                    sum_debit_gr_gl += abs(diff_debit_credit_amount)

                detail_move_dat_file.append(''.join(detail_line_dat_file_list))

            detail_move_dat_file_str = ''.join(detail_move_dat_file)

            count_data_head_file = account_invoice.write_file_ofin(
                file_name_dat,
                detail_move_dat_file_str.replace(u'\xa0', u' '),
                u'dat'
            )

            total_new_head = [0]
            new_move_debit = []
            new_move_credit = []

            if head_log_values.get(file_name_val, False):
                total_new_head = head_log_values[file_name_val]['total_new_line']
                new_move_debit = head_log_values[file_name_val]['debit']
                new_move_credit = head_log_values[file_name_val]['credit']
                count_data_head_file = 0

            total_new_head.append(len(detail_move_dat_file))
            new_move_debit.append(sum_debit_gr_gl)
            new_move_credit.append(sum_credit_gr_gl)

            head_log_values[file_name_val] = {
                'total_old_line': [count_data_head_file],
                'total_new_line': total_new_head,
                'debit': new_move_debit,
                'credit': new_move_credit,
            }

            head_log_value = head_log_values[file_name_val]

            amount_head_data = sum(head_log_value['total_old_line'] + head_log_value['total_new_line'])
            sum_amount_all_debit_str = sum(head_log_value['debit'])
            sum_amount_all_credit_str = sum(head_log_value['credit'])

            detail_val_file = ''.join([
                file_name_dat,
                '{:010d}'.format(amount_head_data),
                '{:015.2f}'.format(sum_amount_all_debit_str),
                '{:015.2f}'.format(sum_amount_all_credit_str)
            ])

            account_invoice.write_file_ofin(file_name_val, detail_val_file, 'log')

            ofin_log_data_id = ofin_log_data_obj.create({
                'res_id': move_id,
                'res_model': 'account.move',
                'log_amount': int(log_amount_str),
                'file_name_ref': file_name_val,
                'date_log_transaction': move_obj_id.date,
                'branch_code': gl_gr_list['branch_code']
            })

            move_obj_id.update({
                'is_get_data_already': True
            })

            ofin_log_data_id.env.cr.commit()

            move_obj_id.env.cr.commit()
