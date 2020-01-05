# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CalMonthlySummaryFranchise(models.TransientModel):
    _name = 'cal.monthly.summary.franchise.wizard'

    month = fields.Selection(
        string="Month",
        selection=[
            ('01', 'มกราคม'),
            ('02', 'กุมภาพันธ์'),
            ('03', 'มีนาคม'),
            ('04', 'เมษายน'),
            ('05', 'พฤษภาคม'),
            ('06', 'มิถุนายน'),
            ('07', 'กรกฎาคม'),
            ('08', 'สิงหาคม'),
            ('09', 'กันยายน'),
            ('10', 'ตุลาคม'),
            ('11', 'พฤษจิกายน'),
            ('12', 'ธันวาคม'),
        ],
        required=True,
        default='05',
    )

    year = fields.Selection(
        string="Year",
        selection=[
            ('2014', '2014'),
            ('2015', '2015'),
            ('2016', '2016'),
            ('2017', '2017'),
            ('2018', '2018'),
            ('2019', '2019'),
            ('2020', '2020'),
            ('2021', '2021'),
            ('2022', '2022'),
            ('2023', '2023'),
            ('2024', '2024'),
            ('2025', '2025'),
            ('2026', '2026'),
            ('2027', '2027'),
            ('2028', '2028'),
            ('2029', '2029'),
            ('2030', '2030'),
            ('2031', '2031'),
            ('2032', '2032'),
            ('2033', '2033'),
            ('2034', '2034'),
            ('2035', '2035'),
            ('2036', '2036'),
            ('2037', '2037'),
            ('2038', '2038'),
        ],
        required=True,
        default='2019',
    )

    branch_from_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch From",
        required=True,
        default=lambda self: self.env.user.branch_id,
    )

    branch_to_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch To",
        required=True,
        default=lambda self: self.env.user.branch_id,
    )


    @api.onchange(
        'branch_from_id',
        'branch_to_id')
    def onchange_branch_from_to(self):
        if self.branch_from_id and self.branch_to_id:
            if self.branch_from_id.branch_code > self.branch_to_id.branch_code:
                raise ValidationError(_("'Store Code From' must less than 'Store Code To'."))

    def _compute_acc_inv_amount(self, branch_id, inv_type, partner_vat, state, date_from, date_to):
        inv_ids = self.env['account.invoice'].search([
            ('branch_id', '=', branch_id),
            ('type', '=', inv_type),
            ('partner_id.vat', '=', partner_vat),
            ('state', 'in', state),
            ('date_invoice', '>=', date_from),
            ('date_invoice', '<=', date_to)
        ])

        draft_inv_ids = self.env['account.invoice'].search([
            ('branch_id', '=', branch_id),
            ('type', '=', inv_type),
            ('partner_id.vat', '=', partner_vat),
            ('state', '=', 'draft'),
            ('date_invoice', '>=', date_from),
            ('date_invoice', '<=', date_to),
            ('picking_id.state', '=', 'done')
        ])

        draft_amount_total = 0
        draft_amount_untaxed = 0
        draft_amount_wht = 0
        draft_amount_tax = 0

        if draft_inv_ids:
            draft_amount_total = sum(draft_inv_ids.mapped('amount_total'))
            draft_amount_untaxed = sum(draft_inv_ids.mapped('amount_untaxed'))
            draft_amount_wht = sum(draft_inv_ids.mapped('amount_wht'))
            draft_amount_tax = sum(draft_inv_ids.mapped('amount_tax'))

        result = {
            'amount_total': sum(inv_ids.mapped('amount_total')) + draft_amount_total,
            'amount_untaxed': sum(inv_ids.mapped('amount_untaxed')) + draft_amount_untaxed,
            'amount_wht': sum(inv_ids.mapped('amount_wht')) + draft_amount_wht,
            'amount_tax': sum(inv_ids.mapped('amount_tax')) + draft_amount_tax
        }
        return result

    def _compute_pos_amount(self, branch_id, state, date_from, date_to, royalty_fee):
        parameter = (
            'KE%',
            date_from,
            date_to,
            date_from,
            date_to,
            branch_id,
            date_from,
            date_to,
            branch_id,
            date_from,
            date_to,
            branch_id,
            date_from,
            date_to,
            branch_id,
            date_from,
            date_to,
            branch_id,
        )
        self._cr.execute("""
            WITH
            /* with 1 */
            temp_delivery_fee as (
                select
                    sum(sol.price_unit * sol.product_uom_qty) as amount_delivery_fee,
                    sol.order_id
                from sale_order_line sol
                inner join account_invoice ai on ai.so_id = sol.order_id
                where ai.parent_invoice_id is null and ai.type = 'out_refund'
                and (sol.is_type_delivery_special = true or -- special place
                sol.is_type_delivery_by_order = true) -- depend on type sale ofm such as true : <499 False
                group by order_id
            ),
            /* with 2 */
            temp_kerry as (
            select
                so.id as so_id,
                sol.price_total as kerry_price_total
            from sale_order so
            inner join sale_order_line sol on sol.order_id = so.id
            inner join product_product pp on
                pp.id = sol.product_id
            inner join product_template prt on pp.product_tmpl_id = prt.id
                and prt.type = 'service'
            where
                pp.default_code ilike %s
            ),
            /* with 3 */
            temp_sale_order as (
            select sale_data.*,
                COALESCE(kr.kerry_price_total,0.0) as kerry_total
            from (
                select
                    s_sod.id,
                    amount_discount_by_order,
                    (
                        select case when sum(price_subtotal) is not null
                                then sum(price_subtotal) end
                        from sale_order_line sol
                        where sol.order_id = s_sod.id
                        and sol.is_type_discount_f_see = false
                        and sol.is_type_delivery_by_order = false
                    ) as price_subtotal_dics_sor,
                    so_date_order,
                    date_order
                from
                    sale_order s_sod
                left join (
                    select
                        id,
                        so_id,
                        date_invoice,
                        number
                    from
                        account_invoice
                    where
                        state in ('open',
                        'paid')
                        and (date_invoice + interval '7 hours')::date >= %s
                        and (date_invoice + interval '7 hours')::date < %s
                        and type = 'out_invoice') aiv on
                    s_sod.id = aiv.so_id
                    and so_id is not null
                where
                    sale_payment_type in ('cash',
                    'credit')
                    and (
                            (s_sod.type_sale_ofm = true
                            and (s_sod.so_date_order + interval '7 hours')::date >= %s
                            and (s_sod.so_date_order + interval '7 hours')::date < %s)
                            or (s_sod.type_sale_ofm = false and aiv.id is not null)
                        )
                    and s_sod.branch_id = %s
                    and s_sod.state in ('sale',
                    'done')
                union
                select
                    s_sod.id,
                    amount_discount_by_order,
                    (
                        select case when sum(price_subtotal) is not null
                                then sum(price_subtotal) end
                        from sale_order_line sol
                        where sol.order_id = s_sod.id
                        and sol.is_type_discount_f_see = false
                        and sol.is_type_delivery_by_order = false
                    ) as price_subtotal_dics_sor,
                    so_date_order,
                    date_order
                from
                    sale_order s_sod
                inner join (
                    select
                        id,
                        sale_id,
                        date,
                        name,
                        state
                    from
                        account_deposit
                    where
                        state in ('open',
                        'paid')
                        and (date + interval '7 hours')::date >= %s
                        and (date + interval '7 hours')::date < %s ) ads on
                    s_sod.id = ads.sale_id and ads.state not in ('draft', 'cancel')
                where
                    sale_payment_type = 'deposit'
                    and s_sod.branch_id = %s
                    and s_sod.state in ('sale',
                    'done')
                ) sale_data
            left join temp_kerry kr on kr.so_id = sale_data.id
            ),
            /* with 4 */
            temp_cn_credit_term as (
            select
                so.id as so_id,
                so.sale_payment_type,
                cn.id as cn_id,
                cn.parent_invoice_id as cn_parent_invoice_id,
                cn.state,
                cn.amount_total_signed
            from
                account_invoice cn
            inner join (
                select
                    id,
                    sale_payment_type,
                    branch_id
                from
                    sale_order ) so on
                so.id = cn.so_id
            where
                cn.state in ('open',
                'paid')
                and (date_invoice + interval '7 hours')::date >= %s
                and (date_invoice + interval '7 hours')::date < %s
                and cn.type = 'out_refund'
                and so.branch_id = %s
                and so.sale_payment_type = 'credit'
            ),
            /* with 5 */
            temp_cn_cash_card as (
            select
                so.id as so_id,
                so.sale_payment_type,
                cn.id as cn_id,
                cn.parent_invoice_id as cn_parent_invoice_id,
                cn.state,
                cn.amount_total_signed
            from
                account_invoice cn
            inner join (
                select
                    id,
                    sale_payment_type,
                    branch_id
                from
                    sale_order ) so on
                so.id = cn.so_id
            inner join account_invoice_payment_line ail on
                cn.id = ail.invoice_id
            inner join account_payment am on
                am.id = ail.payment_id
            where
                cn.state in ('paid')
                and am.state = 'posted'
                and so.sale_payment_type != 'credit'
                and (am.payment_date + interval '7 hours')::date >= %s
                and (am.payment_date + interval '7 hours')::date < %s
                and cn.type = 'out_refund'
                and so.branch_id = %s
            ),
            /* with 6 */
            temp_cn as (
            select
                so_id,
                sale_payment_type,
                cn_id,
                cn_parent_invoice_id,
                state,
                amount_total_signed
            from
                temp_cn_cash_card
            union
            select
                so_id,
                sale_payment_type,
                cn_id,
                cn_parent_invoice_id,
                state,
                amount_total_signed
            from
                temp_cn_credit_term
            ),
            /* with 7 */
            bank_credit_card as (
            select
                abl.pos_statement_id as pos_id,
                COALESCE(sum(abl.amount),0.0) as total_credit_card
            from
                account_bank_statement_line abl
            inner join (
                select
                    *
                from
                    account_journal
                where
                    is_credit_card = true ) ajn on
                abl.journal_id = ajn.id
            group by pos_id
            ),
            /* with 8 */
            deposit_credit_card as (
            select
                dep.sale_id as sale_id,
                COALESCE(sum(adl.paid_total),0.0) as total_credit_card
            from
                account_deposit  dep
            inner join account_deposit_payment_line adl on
                            dep.id = adl.payment_id
            inner join (
                select
                    *
                from
                    account_journal
                where
                    is_credit_card = true ) ajn on
                adl.journal_id = ajn.id
            where dep.state not in ('draft', 'cancel')
            group by sale_id
            ),
            /* with 9 */
            so_discount_by_sor as (
            select
                so.id,
                case
                    when sum(sol.price_unit) is not null then sum(sol.price_unit)
                    else 0
                end
            from
                sale_order so
            inner join sale_order_line sol on
                sol.order_id = so.id
            where
                sol.reward_type = 'discount'
                and sol.promotion = true
                and sol.is_type_discount_f_see = false
                and sol.free_product_id is null
            group by so.id
            ),
            /* with 10 */
            temp_cn_total as (
            select
                sum(cnl_subtotal - cnl_disc_sor)*(-1) as price_subtotal_dics_sor,
                sum(cnl_disc_see)*(-1) as discount_by_see,
                sum(credit_card)*(-1) as credit_card
            from
                (
                select
                    cnl.cnl_subtotal as cnl_subtotal,
                    cnl_disc_sor as cnl_disc_sor,
                    cnl_disc_see as cnl_disc_see,
                    0 as credit_card
                from
                    temp_cn cn
                inner join (
                    select
                        price_subtotal as cnl_subtotal,
                        prorate_amount_2 as cnl_disc_see,
                        prorate_amount_exclude as cnl_disc_all,
                        prorate_amount_exclude - prorate_amount_exclude_2 as cnl_disc_sor,
                        prorate_amount_exclude_2 as cnl_disc_exclude_see,
                        prorate_amount_exclude as cnl_disc_exclude_all,
                        prorate_amount_exclude - prorate_amount_exclude_2 as cnl_disc_exclude_sor,
                        is_type_discount_f_see,
                        free_product_id,
                        promotion,
                        invoice_id,
                        origin_inv_line_id
                    from
                        account_invoice_line) cnl on
                    cnl.invoice_id = cn.cn_id
                    and cnl.promotion = false
                    and cnl.is_type_discount_f_see = false
                    and cnl.free_product_id is null
                where
                    cn.sale_payment_type = 'credit'
            union
                select
                    cnl.cnl_subtotal as cnl_subtotal,
                    cnl_disc_sor as cnl_disc_sor,
                    cnl_disc_see as cnl_disc_see,
                    (
                    select
                        coalesce(sum(paid_total)*(-1), 0.0) as bank_transfer
                    from
                        account_invoice_payment_line ail
                    inner join account_payment_line apl on
                        apl.payment_id = ail.payment_id
                    inner join account_payment_method_multi apmm on
                        apmm.id = apl.payment_method_id
                    inner join (
                        select
                            *
                        from
                            account_journal
                        where
                            is_credit_card = true ) ajn on
                        apmm.journal_id = ajn.id
                    where
                        ail.invoice_id = cn_id ) as credit_card
                from
                    temp_cn cn
                inner join (
                    select
                        price_subtotal as cnl_subtotal,
                        prorate_amount_2 as cnl_disc_see,
                        prorate_amount_exclude as cnl_disc_all,
                        prorate_amount_exclude - prorate_amount_exclude_2 as cnl_disc_sor,
                        prorate_amount_exclude_2 as cnl_disc_exclude_see,
                        prorate_amount_exclude as cnl_disc_exclude_all,
                        prorate_amount_exclude - prorate_amount_exclude_2 as cnl_disc_exclude_sor,
                        is_type_discount_f_see,
                        free_product_id,
                        promotion,
                        invoice_id,
                        origin_inv_line_id
                    from
                        account_invoice_line) cnl on
                    cnl.invoice_id = cn.cn_id
                    and cnl.promotion = false
                    and cnl.is_type_discount_f_see = false
                    and cnl.free_product_id is null
                where
                    cn.sale_payment_type in ('cash',
                    'deposit')
                    and cn.state = 'paid'
            union
                select
                    adl.paid_total as cnl_subtotal,
                    sol_disc_see as cnl_disc_see,
                    sol_disc_exclude_sor as cnl_disc_sor,
                    (
                    select
                        coalesce(sum(adl.paid_total)*(-1), 0.0) as credit_card
                    from
                        account_deposit dep
                    inner join account_deposit_payment_line adl on
                        dep.id = adl.payment_id
                    inner join (
                        select
                            *
                        from
                            account_journal
                        where
                            is_credit_card = true ) ajn on
                        adl.journal_id = ajn.id
                    where
                        dep.sale_id = cn.so_id
                        and dep.state not in ('draft', 'cancel') ) as bank_transfer
                from
                    temp_cn cn
                inner join (
                    select
                        order_id,
                        product_id,
                        free_product_id,
                        is_line_discount_delivery_promotion,
                        is_type_delivery_special,
                        is_type_delivery_by_order,
                        is_type_discount_f_see,
                        prorate_amount_2 as sol_disc_see,
                        prorate_amount_exclude as sol_disc_exclude_all,
                        prorate_amount_exclude - prorate_amount_exclude_2 as sol_disc_exclude_sor,
                        product_uom_qty
                    from
                        sale_order_line ) sol on
                    sol.order_id = cn.so_id
                    and sol.is_line_discount_delivery_promotion = false
                    and sol.is_type_delivery_special = false
                    and sol.is_type_delivery_by_order = false
                    and sol.is_type_discount_f_see = false
                    and sol.free_product_id is null
                inner join (
                    select
                        id,
                        name,
                        sale_id,
                        state
                    from
                        account_deposit ) dep on
                    dep.sale_id = cn.so_id
                    and dep.state not in ('draft', 'cancel')
                inner join account_deposit_payment_line adl on
                    dep.id = adl.payment_id
                left join temp_delivery_fee dfee on
                    dfee.order_id = so_id
                where
                    cn.sale_payment_type in ('deposit')
                    and cn.state = 'paid'
                    and cn_parent_invoice_id is null ) cn_total )
            select
                sum(price_subtotal_dics_sor) as price_subtotal_dics_sor,
                sum(discount_by_see) as discount_by_see,
                sum(credit_card) as credit_card
            from (
                select COALESCE(sum(price_subtotal_dics_sor),0.0) as price_subtotal_dics_sor,
                COALESCE(sum(discount_by_see),0.0) as discount_by_see,
                COALESCE(sum(credit_card),0.0) as credit_card
                from(
                    select  price_subtotal_dics_sor as price_subtotal_dics_sor,
                            0 as discount_by_see,
                            total_credit_card as credit_card
                    from (
                        select sum(price_subtotal_dics_sor) as price_subtotal_dics_sor,
                        sum(amount_discount_by_sor) as amount_discount_by_sor,
                        sum(total_credit_card) as total_credit_card
                        from (
                            select pos.id as pos_id,
                                pos.name as session_no_and_so,
                                sum(pod.total_products_vat_included) as price_subtotal_dics_sor,
                                sum(bcc.total_credit_card) as total_credit_card,
                                (
                                    select case when sum(l.price_subtotal_wo_discount_incl) is not null 
                                                            then sum(l.price_subtotal_wo_discount_incl)
                                                            else 0 end
                                    from pos_order_line l
                                    where l.order_id = pod.id
                                    and l.reward_type = 'discount'
                                    and l.promotion = true
                                    and l.free_product_id is null
                                ) as amount_discount_by_sor

                            from (
                                select *
                                from pos_order
                                    /* Parameter */
                                where (date_order + interval '7 hours')::date >= %s
                                    and (date_order + interval '7 hours')::date < %s
                                    and branch_id = %s
                                    and state not in ('draft', 'paid', 'cancel')
                                ) pod
                            inner join pos_session pos on pod.session_id = pos.id
                            left join bank_credit_card bcc on bcc.pos_id = pod.id
                            group by pod.id,pos.id
                        ) pos
                    ) pos_data
                    union
                    select price_subtotal_dics_sor as price_subtotal_dics_sor,
                            amount_discount_by_order as discount_by_see,
                            total_credit_card as credit_card
                    from (
                        select sum(sod.price_subtotal_dics_sor) as price_subtotal_dics_sor,
                                sum(sod.amount_discount_by_order) as amount_discount_by_order,
                                sum(sod.total_credit_card) as total_credit_card
                        from (
                                select (price_subtotal_dics_sor - kerry_total) as price_subtotal_dics_sor, --kerry include vat
                                        amount_discount_by_order,
                                        total_credit_card
                                from temp_sale_order t_sod
                                left join deposit_credit_card dcc on dcc.sale_id = t_sod.id
                            ) sod
                        ) so_data
                    ) sale_all
                    union
                    select *
                    from temp_cn_total
                    ) sale_all
                    """, parameter)
        amount_sale_all = self._cr.dictfetchall()
        discount_by_see = amount_sale_all[0]['discount_by_see']
        price_subtotal_dics_sor = amount_sale_all[0]['price_subtotal_dics_sor']
        payment_credit_card = amount_sale_all[0]['credit_card']
        amount_royalty_fee = price_subtotal_dics_sor * royalty_fee / 100
        result = {
            'payment_credit_card': payment_credit_card,
            'amount_royalty_fee': amount_royalty_fee,
            'discount_by_see': discount_by_see,
        }
        return result

    @api.multi
    def action_cal_monthly_summary_franchise(self):
        daily_summ_fran_obj = self.env['daily.summary.franchise']
        monthly_summ_fran_obj = self.env['monthly.summary.franchise']
        branch_obj = self.env['pos.branch']
        if self.month and self.year and self.branch_from_id and self.branch_to_id:
            branch_obj = self.env['pos.branch']
            branch_ids = branch_obj.search([('branch_code', '>=', self.branch_from_id.branch_code),
                                            ('branch_code', '<=', self.branch_to_id.branch_code)])
        if branch_ids:
            num_calculated = 0
            for branch_id in branch_ids:
                name = 'FR' + self.year[2:4] + self.month + branch_id.branch_code
                msf_id = monthly_summ_fran_obj.search([('name', '=', name)])
                if msf_id.name != False:
                    num_calculated += 1
        if num_calculated == len(branch_ids):
            raise ValidationError(_("สาขาที่เลือกได้มีการสร้างใบสรุปรายเดือนแล้ว ไม่สามารถทำการสร้างซ้ำได้"))
        for item in self:
            date_from = datetime.date(year=int(item.year), day=01, month=int(item.month))
            date_to = date_from + relativedelta(months=1)
            last_month_from = date_from - relativedelta(months=1)
            last_month_to = last_month_from + relativedelta(months=1) - relativedelta(days=1)
            month_name = dict(item._fields['month'].selection).get(item.month)
            if self.month != '1':
                last_month = '0'+str(int(self.month) - 1) if int(self.month) - 1 < 10 else str(int(self.month) - 1)
                last_month_name = dict(item._fields['month'].selection).get(last_month)
                last_month_year = item.year
            else:
                last_month_name = dict(item._fields['month'].selection).get('12')
                last_month_year = str(int(item.year) - 1)
            branch_ids = self.env['pos.branch'].search([('branch_code', '>=', self.branch_from_id.branch_code),
                                                        ('branch_code', '<=', self.branch_to_id.branch_code)])
            if branch_ids:
                msf_ids = []
                for branch_id in branch_ids:
                    name = 'FR' + item.year[2:4] + item.month + branch_id.branch_code
                    monthly_summ_fran_ids = monthly_summ_fran_obj.search([('name', '=', name)])
                    if not monthly_summ_fran_ids:
                        sale_amount_dict = self._compute_pos_amount(
                            branch_id.id,
                            ('open', 'paid', 'done', 'invoiced'),
                            date_from.strftime("%Y-%m-%d"),
                            date_to.strftime("%Y-%m-%d"),
                            branch_id.royalty_fee
                        )
                        # search from daily summary for 1.1 
                        daily_summ_fran_ids = daily_summ_fran_obj.search([('date', '>=', date_from.strftime("%Y-%m-%d")),
                                                                        ('date', '<=', date_to.strftime("%Y-%m-%d")),
                                                                        ('branch_id', '=', branch_id.id),
                                                                        ('is_backdate', '=', False),
                                                                        ('state', '!=', 'cancel')])
                        daily_summ_bank_transfer = sum(daily_summ_fran_ids.mapped('sum_bank_transfer'))
                        assets_vals = [
                            {
                                'number': 1.1,
                                'name': 'เงินสะสมจากโอนประจำวัน',
                                'coa_type': 'assets',
                                'amount': daily_summ_bank_transfer,
                                'amount_total': daily_summ_bank_transfer,
                                'amount_original': daily_summ_bank_transfer,
                            },
                            {
                                'number': 1.2,
                                'name': 'เงินสะสมจาก EDC',
                                'coa_type': 'assets',
                                'amount': sale_amount_dict['payment_credit_card'],
                                'amount_total': sale_amount_dict['payment_credit_card'],
                                'amount_original': sale_amount_dict['payment_credit_card'],
                            },
                            {
                                'number': 1.3,
                                'name': 'เงินสะสมจาก T1C',
                                'coa_type': 'assets',
                            },
                            {
                                'number': 1.4,
                                'name': 'เงินสะสมจาก Coupon เงินสด',
                                'coa_type': 'assets',
                            },
                            {
                                'number': 1.5,
                                'name': "ส่วนลดโดย F'See",
                                'coa_type': 'assets',
                                'amount': sale_amount_dict['discount_by_see'],
                                'amount_total': sale_amount_dict['discount_by_see'],
                                'amount_original': sale_amount_dict['discount_by_see'],
                            },
                            {
                                'number': 1.6,
                                'name': "ปรับปรุงส่วนลด F'See",
                                'coa_type': 'assets',
                            },
                            {
                                'number': 1.7,
                                'name': "ปรับปรุงค่าจัดส่ง",
                                'coa_type': 'assets',
                            },
                            {
                                'number': 1.8,
                                'name': "ปรับปรุงเงินสะสม 1.1 - 1.4",
                                'coa_type': 'assets',
                            },
                        ]

                        # 2.1
                        ap_amount_dict = self._compute_acc_inv_amount(
                            branch_id.id,
                            'in_invoice',
                            '0107551000134',
                            ('open', 'paid'),
                            last_month_from.strftime("%Y-%m-%d"),
                            last_month_to.strftime("%Y-%m-%d")
                        )
                        # 2.2
                        rtv_amount_dict = self._compute_acc_inv_amount(
                            branch_id.id,
                            'in_refund',
                            '0107551000134',
                            ('open', 'paid'),
                            date_from.strftime("%Y-%m-%d"),
                            date_to.strftime("%Y-%m-%d")
                        )
                        liabilities_vals = [
                            {
                                'number': 2.1,
                                'name': "ค่าซื้อสินค้าเข้าร้าน (" + str(last_month_name) + " " + str(last_month_year) + ")",
                                'coa_type': 'liabilities',
                                'amount': ap_amount_dict['amount_untaxed'] * (-1),
                                'vat_amount': (ap_amount_dict['amount_tax']) * (-1),
                                'amount_total': ap_amount_dict['amount_total'] * (-1),
                                'amount_original': ap_amount_dict['amount_total'] * (-1),
                            },
                            {
                                'number': 2.2,
                                'name': "ค่าคืนสินค้าจากยอดซื้อตามข้อ 2.1",
                                'coa_type': 'liabilities',
                                'amount': rtv_amount_dict['amount_untaxed'] * (-1),
                                'vat_amount': (rtv_amount_dict['amount_tax']) * (-1),
                                'amount_total': rtv_amount_dict['amount_total'] * (-1),
                                'amount_original': rtv_amount_dict['amount_total'] * (-1),
                            },
                            {
                                'number': 2.3,
                                'name': "ค่าขนส่งของ COL จากยอดซื้อเดือน" + month_name + " " + item.year,
                                'coa_type': 'liabilities',
                            },
                            {
                                'number': 2.4,
                                'name': "ปรับปรุงค่าใช้จ่าย",
                                'coa_type': 'liabilities',
                            },
                        ]
                        revenues_vals = [
                            {
                                'number': 3.1,
                                'name': "รายรับแนะนำลูกค้า  (Commission)",
                                'coa_type': 'revenues',
                            },
                            {
                                'number': 3.2,
                                'name': "รายรับจากการการันตี GP (Compensation)",
                                'coa_type': 'revenues',
                            },
                            {
                                'number': 3.3,
                                'name': "รายรับ Rebate",
                                'coa_type': 'revenues',
                            },
                            {
                                'number': 3.4,
                                'name': "ปรับปรุงรายได้อื่นๆ",
                                'coa_type': 'revenues',
                            },
                        ]
                        cog_vals = [
                            {
                                'number': 4.1,
                                'name': "ค่า Royalty Fee ของยอดขายสินค้า",
                                'coa_type': 'cog',
                                'amount': sale_amount_dict['amount_royalty_fee'] * (-1),
                                'amount_total': sale_amount_dict['amount_royalty_fee'] * (-1),
                                'amount_original': sale_amount_dict['amount_royalty_fee'] * (-1),
                                'coa_to': 'see',
                                'coa_from': 'sor',
                            },
                            {
                                'number': 4.2,
                                'name': "ค่า System MA",
                                'coa_type': 'cog',
                            },
                            {
                                'number': 4.3,
                                'name': "ค่าธรรมเนียม EDC",
                                'coa_type': 'cog',
                            },
                            {
                                'number': 4.4,
                                'name': "ค่าธรรมเนียม ธนาคาร",
                                'coa_type': 'cog',
                            },
                            {
                                'number': 4.5,
                                'name': "ค่าปรับปรุง Royalty Fee จากการเบิกใช้ และนับสต็อก",
                                'coa_type': 'cog',
                            },
                            {
                                'number': 4.6,
                                'name': "ปรับปรุงค่าดำเนินการ",
                                'coa_type': 'cog',
                            },
                        ]
                        expenses_vals = [
                            {
                                'number': 5.1,
                                'name': "เงินรับแทนค่าบริการ Kerry",
                                'coa_type': 'expenses',
                            },
                            {
                                'number': 5.2,
                                'name': "ค่าบริการจัดส่ง Kerry",
                                'coa_type': 'expenses',
                                
                            },
                            {
                                'number': 5.3,
                                'name': "รายได้ค่า Commission Kerry จ่ายให้ See ( หลังหัก W/T แล้ว )",
                                'coa_type': 'expenses',
                            },
                            {
                                'number': 5.4,
                                'name': "รายได้ค่า Commission See จ่ายให้ Sor ( หลังหัก W/T แล้ว )",
                                'coa_type': 'expenses',
                            },
                            {
                                'number': 5.5,
                                'name': "ปรับปรุง Kerry",
                                'coa_type': 'expenses',
                                
                            },
                        ]
                        msf_id = monthly_summ_fran_obj.create({
                            'name': name,
                            'company_id': branch_id.pos_company_id.id,
                            'month': item.month,
                            'year': item.year,
                            'branch_id': branch_id.id,
                            'store_code': branch_id.branch_code,
                            'state': 'draft',
                            'monthly_summary_franchise_assets_ids': [(0, 0, x) for x in assets_vals],
                            'monthly_summary_franchise_liabilities_ids': [(0, 0, x) for x in liabilities_vals],
                            'monthly_summary_franchise_revenues_ids': [(0, 0, x) for x in revenues_vals],
                            'monthly_summary_franchise_cog_ids': [(0, 0, x) for x in cog_vals],
                            'monthly_summary_franchise_expenses_ids': [(0, 0, x) for x in expenses_vals],
                        })
                        msf_ids.append(msf_id.id)
            domain = [
                ('id', 'in', msf_ids)
            ]
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'name': 'ใบสรุปประจำเดือน',
            'res_model': 'monthly.summary.franchise',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': '{"search_default_not_cancel": 1}',
            'domain': domain,
        }
