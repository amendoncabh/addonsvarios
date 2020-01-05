# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import except_orm


class CalDailySummaryFranchise(models.TransientModel):
    _name = 'cal.daily.summary.franchise.wizard'

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Datetime.now,
    )

    pos_cash = fields.Float(
        string="Cash (POS)",
        required=True,
    )

    so_cash = fields.Float(
        string="Cash (Sale Order)",
        required=True,
    )

    credit_term = fields.Float(
        string="ยอดรับชำระเครดิตเทอม (ไม่คำนวณในรายการสรุป)",
        required=True,
    )

    kerry_cash = fields.Float(
        string="Cash (Kerry)",
        required=True,
    )

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        required=True,
        default=lambda self: self.env.user.branch_id,
    )

    manager_id = fields.Many2one(
        comodel_name="res.users",
        string="Manager",
    )

    manager_pin = fields.Char(
        string="PIN (Manager)",
    )

    is_auto_cal = fields.Boolean(
        string="",
        default=False,
    )

    reason = fields.Char(
        string="Reason",
    )

    @api.multi
    def action_edit_daily_summary_franchise(self):
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')
        active = self.env[active_model].browse(active_ids)
        active_cash_kerry = self.env['daily.summary.franchise.cash'].search([
            ('daily_summary_franchise_id', '=', active.id),
            ('name', '=', 'Cash (Kerry)'),
        ])
        active_cash_kerry_line = self.env['daily.summary.franchise.line'].search([
            ('daily_summary_franchise_id', '=', active.id),
            ('session_no_and_so', '=', 'Kerry (Cash)'),
        ])
        active.write({'reason': self.reason,
                      'daily_summary_franchise_line_ids': [[1, active_cash_kerry_line.id,
                                                            {'sub_total': self.kerry_cash,
                                                             'total': self.kerry_cash,
                                                             'bank_transfer': self.kerry_cash}]],
                      'daily_summary_franchise_cash_ids': [[1, active_cash_kerry.id,
                                                            {'total': self.kerry_cash}]]})

    @api.multi
    def action_cal_daily_summary_franchise(self):
        for item in self:
            daily_summary_first = False
            if item.manager_id.pos_security_pin == item.manager_pin or item.is_auto_cal:
                navigate_data = {
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'name': 'ใบสรุปประจำวัน',
                    'res_model': 'daily.summary.franchise',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'context': '{"search_default_not_cancel": 1}',
                }

                parameter_credit_term = (
                    item.branch_id.id,
                    item.date,
                )
                
                item._cr.execute("""
                    select count('') as count_row
                    from daily_summary_franchise
                    where state in ('active', 'verify', 'draft')
                    and branch_id = %s
                """,(item.branch_id.id,))

                count_daily_summary_first = item._cr.dictfetchall()
                if count_daily_summary_first[0]['count_row'] == 0:
                    daily_summary_first = True

                item._cr.execute("""
                    select count('') as count_row
                    from daily_summary_franchise
                    /* Parameter */
                    where branch_id = %s
                          and (date + interval '7 hours')::date = %s
                          and state in ('active', 'verify', 'draft')
                    limit 1
                """, parameter_credit_term)

                count_daily_summary_list = item._cr.dictfetchall()
                if count_daily_summary_list[0]['count_row'] > 0:
                    return navigate_data

                next_date = datetime.strptime(item.date, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                next_date = next_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                back_date = datetime.strptime(item.date, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                back_date = back_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                parameter_pos_session = (
                    item.branch_id.id,
                    back_date,
                    next_date,
                )
                item._cr.execute("""
                    select
                        s.name,
                        s.state,
                        s.start_at
                    from
                        pos_session s
                    inner join pos_config c on c.id = s.config_id
                    where
                        state != 'closed'
                        /* Parameter */
                        and c.branch_id = %s
                        and (start_at + interval '7 hours')::date >= %s
                        and (start_at + interval '7 hours')::date < %s
                """,parameter_pos_session)

                pos_session_open_list = item._cr.dictfetchall()
                if len(pos_session_open_list) > 0:
                    session_name = ','.join([i['name'] for i in pos_session_open_list])
                    raise except_orm(_('มี session ที่ยังเปิดขายอยู่\nจึงทำให้คำนวนสรุปประจำวันไม่ได้\nจะต้องปิด session ก่อน\n\nSession : '+ session_name))
                
                next_day = datetime.strptime(item.date, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                next_day = next_day.strftime(DEFAULT_SERVER_DATE_FORMAT)
                if self.env['daily.summary.franchise'].search([
                                ('branch_id', '=', item.branch_id.id),
                                ('state', '!=', 'cancel'),
                                ('date', '<=', item.date)
                            ]):
                    n_day = 1
                    back_day = datetime.strptime(item.date, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                    back_day = back_day.strftime(DEFAULT_SERVER_DATE_FORMAT)
                else:
                    n_day = 0
                    back_day = datetime.strptime(item.date, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=0)
                    back_day = back_day.strftime(DEFAULT_SERVER_DATE_FORMAT)
                if not daily_summary_first:
                    parameter_detail = (
                        back_day,
                        next_day,
                        back_day,
                        next_day,
                        back_day,
                        next_day,
                        item.branch_id.id,
                        back_day,
                        next_day,
                        back_day,
                        next_day,
                        item.branch_id.id,
                        back_day,
                        next_day,
                        item.branch_id.id,
                        back_day,
                        next_day,
                        item.branch_id.id,
                        item.branch_id.id,
                        back_day,
                        next_day,
                    )
                    item._cr.execute("""
                        with 
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
                        temp_sale_order as (
                        select
                            s_sod.id,
                            type_sale_ofm,
                            before_discount,
                            amount_total,
                            (
                            select
                                case
                                    when sum(l.price_unit) is not null then sum(l.price_unit)
                                    else 0
                                end
                            from
                                sale_order_line l
                            where
                                l.order_id = s_sod.id
                                and l.reward_type = 'discount'
                                and l.promotion = true
                                and l.is_type_discount_f_see = false
                                and l.free_product_id is null ) as amount_discount_by_sor,
                            (
                            select
                                case
                                    when sum(cn.amount_total_signed) is not null then sum(cn.amount_total_signed)
                                    else 0
                                end
                            from
                                account_invoice cn
                            where
                                state in ('open',
                                'paid')
                                and (date_invoice + interval '7 hours')::date >= %s
                                and (date_invoice + interval '7 hours')::date < %s
                                and type = 'out_refund') as inv_amount_total,
                            aiv.date_invoice,
                            amount_discount_by_order,
                            amount_delivery_fee_special,
                            amount_delivery_fee_by_order,
                            so_date_order,
                            sale_payment_type,
                            daily_summary_franchise_id,
                            date_order,
                            s_sod.state
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
                            and daily_summary_franchise_id is null /* Parameter */
                            and s_sod.branch_id = %s
                            and s_sod.state in ('sale',
                            'done')
                        union
                        select
                            s_sod.id,
                            type_sale_ofm,
                            before_discount,
                            amount_total,
                            (
                            select
                                case
                                    when sum(l.price_unit) is not null then sum(l.price_unit)
                                    else 0
                                end
                            from
                                sale_order_line l
                            where
                                l.order_id = s_sod.id
                                and l.reward_type = 'discount'
                                and l.promotion = true
                                and l.is_type_discount_f_see = false
                                and l.free_product_id is null ) as amount_discount_by_sor,
                            (
                            select
                                case
                                    when sum(cn.amount_total_signed) is not null then sum(cn.amount_total_signed)
                                    else 0
                                end
                            from
                                account_invoice cn
                            where
                                state in ('open',
                                'paid')
                                and (date_invoice + interval '7 hours')::date >= %s
                                and (date_invoice + interval '7 hours')::date < %s
                                and type = 'out_refund') as inv_amount_total,
                            ads.date,
                            amount_discount_by_order,
                            amount_delivery_fee_special,
                            amount_delivery_fee_by_order,
                            so_date_order,
                            sale_payment_type,
                            daily_summary_franchise_id,
                            date_order,
                            s_sod.state
                        from
                            sale_order s_sod
                        inner join (
                            select
                                id,
                                sale_id,
                                date,
                                name
                            from
                                account_deposit
                            where
                                state in ('open',
                                'paid')
                                and (date + interval '7 hours')::date >= %s
                                and (date + interval '7 hours')::date < %s ) ads on
                            s_sod.id = ads.sale_id
                        where
                            sale_payment_type = 'deposit'
                            and daily_summary_franchise_id is null /* Parameter */
                            and s_sod.branch_id = %s
                            and s_sod.state in ('sale',
                            'done')
                        ),
                        /* with 3 */
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
                            and cn.daily_summary_franchise_id is null /* Parameter */
                            and so.branch_id = %s
                            and so.sale_payment_type = 'credit'
                        ),
                        /* with 4 */
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
                            and cn.daily_summary_franchise_id is null /* Parameter */
                            and so.branch_id = %s
                        ),
                        /* with 5 */
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
                        /* with 6 */
                        temp_cn_total as (
                        select
                            cn.*,
                            cnl_quantity,
                            cnl.prorate_amount as cnl_disc_all,
                            cnl_disc_see as cnl_disc_see,
                            cnl_disc_sor as cnl_disc_sor,
                            cnl.cnl_subtotal as cnl_subtotal,
                            0 as amount_delivery_fee,
                            cn.amount_total_signed*(-1) as bank_transfer,
                            'Sale Order (Credit Term)'::text as session_no_and_so
                        from
                            temp_cn cn
                        inner join (
                            select
                                quantity as cnl_quantity,
                                quantity*price_unit as cnl_subtotal,
                                prorate_amount,
                                prorate_amount_2 as cnl_disc_see,
                                prorate_amount - prorate_amount_2 as cnl_disc_sor,
                                is_type_discount_f_see,
                                free_product_id,
                                promotion,
                                origin_inv_line_id,
                                invoice_id
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
                            cn.*,
                            cnl_quantity,
                            cnl.prorate_amount as cnl_disc_all,
                            cnl_disc_see as cnl_disc_see,
                            cnl_disc_sor as cnl_disc_sor,
                            cnl.cnl_subtotal as cnl_subtotal,
                            0 as amount_delivery_fee,
                            apl.paid_total*(-1) as bank_transfer,
                            'Sale Order (Cash)'::text as session_no_and_so
                        from
                            temp_cn cn
                        inner join (
                            select
                                quantity as cnl_quantity,
                                quantity*price_unit as cnl_subtotal,
                                prorate_amount,
                                prorate_amount_2 as cnl_disc_see,
                                prorate_amount - prorate_amount_2 as cnl_disc_sor,
                                is_type_discount_f_see,
                                free_product_id,
                                promotion,
                                origin_inv_line_id,
                                invoice_id
                            from
                                account_invoice_line) cnl on
                            cnl.invoice_id = cn.cn_id
                            and cnl.promotion = false
                            and cnl.is_type_discount_f_see = false
                            and cnl.free_product_id is null
                        inner join account_invoice_payment_line ail on
                            cn_id = ail.invoice_id
                        inner join account_payment_line apl on
                            apl.payment_id = ail.payment_id
                        inner join account_payment_method_multi apmm on
                            apmm.id = apl.payment_method_id
                        inner join (
                            select
                                aj.*
                            from
                                account_journal aj
                            left join redeem_type re on aj.redeem_type_id = re.id
                            where
                                aj.type = 'cash'
                                and (re.id is null) or (re.id is not null and re.is_bank_transfer = true) ) ajn on
                            apmm.journal_id = ajn.id
                        where
                            cn.sale_payment_type in ('cash',
                            'deposit')
                            and cn.state = 'paid'
                        union
                        select
                            cn.*,
                            product_uom_qty as cnl_quantity,
                            sol_disc_all as cnl_disc_all,
                            sol_disc_see as cnl_disc_see,
                            sol_disc_sor as cnl_disc_sor,
                            adl.paid_total as cnl_subtotal,
                            amount_delivery_fee*(-1) as amount_delivery_fee,
                            adl.paid_total*(-1) as bank_transfer,
                            'Sale Order (Cash)'::text as session_no_and_so
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
                                prorate_amount as sol_disc_all,
                                prorate_amount - prorate_amount_2 as sol_disc_sor,
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
                        left join temp_delivery_fee dfee on dfee.order_id = so_id
                        inner join (
                            select
                                aj.*
                            from
                                account_journal aj
                            left join redeem_type re on aj.redeem_type_id = re.id
                            where
                                aj.type = 'cash'
                                and (re.id is null) or (re.id is not null and re.is_bank_transfer = true) ) ajn on
                            adl.journal_id = ajn.id
                        where
                            cn.sale_payment_type in ('deposit')
                            and cn.state = 'paid'
                            and cn_parent_invoice_id is null
                        ),
                        /* with 7 */
                        temp_cn_so as (
                        select
                            so_id,
                            session_no_and_so,
                            sale_payment_type,
                            sum(cnl_disc_all) as cnl_disc_all,
                            sum(cnl_disc_sor) as cnl_disc_sor,
                            sum(cnl_disc_see) as cnl_disc_see,
                            sum(amount_delivery_fee) as delivery_fee,
                            min(amount_total_signed) as amount_total_signed,
                            min(bank_transfer) as bank_transfer
                        from
                            temp_cn_total
                        group by so_id,session_no_and_so,sale_payment_type
                        ),
                        /* with 8 */
                        temp_cn_cash_credit as (
                        select
                            session_no_and_so,
                            sum(round((amount_total_signed - cnl_disc_all)::DECIMAL,2)) as sub_total,
                            sum(round(cnl_disc_all::DECIMAL,2)) as discount_by_all,
                            sum(round(cnl_disc_sor::DECIMAL,2)) as discount_by_sor,
                            sum(round(cnl_disc_see::DECIMAL,2)) as discount_by_see,
                            sum(round(delivery_fee::DECIMAL,2)) as delivery_fee,
                            sum(round(amount_total_signed::DECIMAL,2)) as total,
                            sum(round(bank_transfer::DECIMAL,2)) as bank_transfer
                        from
                            temp_cn_so
                        group by session_no_and_so
                        ),
                        /* with 9 */
                        temp_so_cash_credit as (
                        select
                            session_no_and_so as session_no_and_so,
                            sub_total as sub_total,
                            amount_discount_by_sor as discount_by_sor,
                            0 as discount_by_see,
                            0 as delivery_fee,
                            sub_total + amount_discount_by_sor as total,
                            total_and_bank_transfer as bank_transfer,
                            true as is_pos,
                            false as is_so
                        from
                            (
                            select
                                sum(amount_discount_by_sor) as amount_discount_by_sor,
                                session_no_and_so,
                                sum(sub_total) as sub_total,
                                sum(total_and_bank_transfer) as total_and_bank_transfer
                            from
                                (
                                select
                                    pos.id as pos_id,
                                    pos.name as session_no_and_so,
                                    (
                                    select
                                        case
                                            when sum(l.price_subtotal_wo_discount_incl) is not null then sum(l.price_subtotal_wo_discount_incl)
                                            else 0
                                        end
                                    from
                                        pos_order_line l
                                    where
                                        l.order_id = pod.id
                                        and l.reward_type = 'discount'
                                        and l.promotion = true
                                        and l.free_product_id is null ) as amount_discount_by_sor,
                                    sum(pod.before_discount) as sub_total,
                                    (
                                    select
                                        sum(abl.amount) as total_and_bank_transfer
                                    from
                                        account_bank_statement_line abl
                                    inner join (
                                        select
                                            aj.*
                                        from
                                            account_journal aj
                                        left join redeem_type re on aj.redeem_type_id = re.id
                                        where
                                            aj.type = 'cash'
                                            and (re.id is null) or (re.id is not null and re.is_bank_transfer = true) ) ajn on
                                        abl.journal_id = ajn.id
                                    where
                                        pod.id = abl.pos_statement_id ) as total_and_bank_transfer,
                                    (
                                    select
                                        case
                                            when type = 'cash' then true
                                        end as is_cash
                                    from
                                        account_bank_statement_line abl
                                    inner join (
                                        select
                                            aj.*
                                        from
                                            account_journal aj
                                        left join redeem_type re on aj.redeem_type_id = re.id
                                        where
                                            aj.type = 'cash'
                                            and (re.id is null) or (re.id is not null and re.is_bank_transfer = true) ) ajn on
                                        abl.journal_id = ajn.id
                                    where
                                        pod.id = abl.pos_statement_id
                                    group by
                                        type ) as is_cash
                                from
                                    (
                                    select
                                        *
                                    from
                                        pos_order
                                    where
                                        daily_summary_franchise_id is null /* Parameter */
                                        and branch_id = %s
                                        and (date_order + interval '7 hours')::date >= %s
                                        and (date_order + interval '7 hours')::date < %s
                                        and state not in ('draft',
                                        'paid',
                                        'cancel') ) pod
                                inner join pos_session pos on
                                    pod.session_id = pos.id
                                group by
                                    pod.id,
                                    pos_id ) pos
                            where
                                is_cash = true
                            group by
                                session_no_and_so ) pos_data
                        union select
                            session_no_and_so as session_no_and_so,
                            sub_total as sub_total,
                            amount_discount_by_sor as discount_by_sor,
                            amount_discount_by_order*(-1) as discount_by_see,
                            delivery_fee as delivery_fee,
                            sub_total + amount_discount_by_sor + amount_discount_by_order*(-1) + delivery_fee as total,
                            case when so_data.type_sale_ofm is true then sub_total + amount_discount_by_sor + delivery_fee
                            	else sub_total + amount_discount_by_sor 
                            end as bank_transfer,
                            false as is_pos,
                            true as is_so
                        from
                            (
                            select
                                sod.session_no_and_so as session_no_and_so,
                                type_sale_ofm,
                                sum(sod.before_discount) as sub_total,
                                sum(sod.amount_discount_by_sor) as amount_discount_by_sor,
                                sum(sod.amount_discount_by_order) as amount_discount_by_order,
                                sum(sod.amount_total) as total_and_bank_transfer,
                                sum(sod.amount_delivery_fee_special + sod.amount_delivery_fee_by_order) as delivery_fee
                            from
                                (
                                select
                                    t_sod.before_discount as before_discount,
                                    adl.paid_total as amount_total,
                                    amount_discount_by_sor,
                                    amount_discount_by_order,
                                    amount_delivery_fee_special,
                                    amount_delivery_fee_by_order,
                                    so_date_order,
                                    t_sod.type_sale_ofm,
                                    'Sale Order (Cash)'::text as session_no_and_so
                                from
                                    temp_sale_order t_sod
                                inner join account_deposit ads on
                                    t_sod.id = ads.sale_id
                                    and ads.state not in ('draft', 'cancel')
                                inner join account_deposit_payment_line adl on
                                    ads.id = adl.payment_id
                                inner join (
                                    select
                                        aj.*
                                    from
                                        account_journal aj
                                    left join redeem_type re on aj.redeem_type_id = re.id
                                    where
                                        aj.type = 'cash'
                                        and (re.id is null) or (re.id is not null and re.is_bank_transfer = true) ) ajn on
                                    adl.journal_id = ajn.id
                                where
                                    sale_payment_type in ('cash',
                                    'deposit')
                            union
                                select
                                    before_discount,
                                    amount_total,
                                    amount_discount_by_sor,
                                    amount_discount_by_order,
                                    amount_delivery_fee_special,
                                    amount_delivery_fee_by_order,
                                    so_date_order,
                                    type_sale_ofm,
                                    'Sale Order (Credit Term)'::text as session_no_and_so
                                from
                                    temp_sale_order
                                where
                                    sale_payment_type = 'credit' ) sod
                            group by
                                sod.session_no_and_so,
                                type_sale_ofm) so_data
                        )
                        select session_no_and_so,
                            sum(sub_total) as sub_total,
                            sum(discount_by_sor) as discount_by_sor,
                            sum(discount_by_see) as discount_by_see,
                            sum(delivery_fee) as delivery_fee,
                            sum(total) as total,
                            sum(bank_transfer) as bank_transfer
                        from(
                        select so.session_no_and_so,
                                so.sub_total as sub_total,
                                so.discount_by_sor  as discount_by_sor,
                                so.discount_by_see as discount_by_see,
                                so.delivery_fee as delivery_fee,
                                so.total as total,
                                so.bank_transfer as bank_transfer	
                        from temp_so_cash_credit so
                        union
                        select cn.session_no_and_so,
                                round(cn.sub_total::DECIMAL,2) as sub_total,
                                round(cn.discount_by_sor::DECIMAL,2)  as discount_by_sor,
                                round(cn.discount_by_see::DECIMAL,2) as discount_by_see,
                                round(cn.delivery_fee::DECIMAL,2) as delivery_fee,
                                round(cn.total::DECIMAL,2) as total,
                                case when cn.session_no_and_so = 'Sale Order (Credit Term)' 
                                then round(cn.sub_total::DECIMAL,2) + round(cn.discount_by_sor::DECIMAL,2)
                                else round(cn.bank_transfer::DECIMAL,2)*(-1) - round(cn.discount_by_see::DECIMAL,2) end as bank_transfer
                        from temp_cn_cash_credit cn
                        ) sale_cn
                        group by session_no_and_so
                        """, parameter_detail)
                else:
                    parameter_detail = (
                        next_day,
                        next_day,
                        next_day,
                        item.branch_id.id,
                        next_day,
                        next_day,
                        item.branch_id.id,
                        next_day,
                        item.branch_id.id,
                        next_day,
                        item.branch_id.id,
                        item.branch_id.id,
                        next_day,
                    )
                    item._cr.execute("""
                        with 
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
                        temp_sale_order as (
                        select
                            s_sod.id,
                            type_sale_ofm,
                            before_discount,
                            amount_total,
                            (
                            select
                                case
                                    when sum(l.price_unit) is not null then sum(l.price_unit)
                                    else 0
                                end
                            from
                                sale_order_line l
                            where
                                l.order_id = s_sod.id
                                and l.reward_type = 'discount'
                                and l.promotion = true
                                and l.is_type_discount_f_see = false
                                and l.free_product_id is null ) as amount_discount_by_sor,
                            (
                            select
                                case
                                    when sum(cn.amount_total_signed) is not null then sum(cn.amount_total_signed)
                                    else 0
                                end
                            from
                                account_invoice cn
                            where
                                state in ('open',
                                'paid')
                                and (date_invoice + interval '7 hours')::date < %s
                                and type = 'out_refund') as inv_amount_total,
                            aiv.date_invoice,
                            amount_discount_by_order,
                            amount_delivery_fee_special,
                            amount_delivery_fee_by_order,
                            so_date_order,
                            sale_payment_type,
                            daily_summary_franchise_id,
                            date_order,
                            s_sod.state
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
                                and (date_invoice + interval '7 hours')::date < %s
                                and type = 'out_invoice') aiv on
                            s_sod.id = aiv.so_id
                            and so_id is not null
                        where
                            sale_payment_type in ('cash',
                            'credit')
                            and (
                                    (s_sod.type_sale_ofm = true
                                    and (s_sod.so_date_order + interval '7 hours')::date < %s)
                                    or (s_sod.type_sale_ofm = false and aiv.id is not null)
                                )
                            and daily_summary_franchise_id is null /* Parameter */
                            and s_sod.branch_id = %s
                            and s_sod.state in ('sale',
                            'done')
                        union
                        select
                            s_sod.id,
                            type_sale_ofm,
                            before_discount,
                            amount_total,
                            (
                            select
                                case
                                    when sum(l.price_unit) is not null then sum(l.price_unit)
                                    else 0
                                end
                            from
                                sale_order_line l
                            where
                                l.order_id = s_sod.id
                                and l.reward_type = 'discount'
                                and l.promotion = true
                                and l.is_type_discount_f_see = false
                                and l.free_product_id is null ) as amount_discount_by_sor,
                            (
                            select
                                case
                                    when sum(cn.amount_total_signed) is not null then sum(cn.amount_total_signed)
                                    else 0
                                end
                            from
                                account_invoice cn
                            where
                                state in ('open',
                                'paid')
                                and (date_invoice + interval '7 hours')::date < %s
                                and type = 'out_refund') as inv_amount_total,
                            ads.date,
                            amount_discount_by_order,
                            amount_delivery_fee_special,
                            amount_delivery_fee_by_order,
                            so_date_order,
                            sale_payment_type,
                            daily_summary_franchise_id,
                            date_order,
                            s_sod.state
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
                                and (date + interval '7 hours')::date < %s ) ads on
                            s_sod.id = ads.sale_id and ads.state not in ('draft', 'cancel')
                        where
                            sale_payment_type = 'deposit'
                            and daily_summary_franchise_id is null /* Parameter */
                            and s_sod.branch_id = %s
                            and s_sod.state in ('sale',
                            'done')
                        ),
                        /* with 3 */
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
                                and (date_invoice + interval '7 hours')::date < %s
                                and cn.type = 'out_refund'
                                and cn.daily_summary_franchise_id is null /* Parameter */
                                and so.branch_id = %s
                                and so.sale_payment_type = 'credit'
                            ),
                            /* with 4 */
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
                                and (am.payment_date + interval '7 hours')::date < %s
                                and cn.type = 'out_refund'
                                and cn.daily_summary_franchise_id is null /* Parameter */
                                and so.branch_id = %s
                        ),
                        /* with 5 */
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
                        /* with 6 */
                        temp_cn_total as (
                        select
                            cn.*,
                            cnl_quantity,
                            cnl.prorate_amount as cnl_disc_all,
                            cnl_disc_see as cnl_disc_see,
                            cnl_disc_sor as cnl_disc_sor,
                            cnl.cnl_subtotal as cnl_subtotal,
                            0 as amount_delivery_fee,
                            cn.amount_total_signed*(-1) as bank_transfer,
                            'Sale Order (Credit Term)'::text as session_no_and_so
                        from
                            temp_cn cn
                        inner join (
                            select
                                quantity as cnl_quantity,
                                quantity*price_unit as cnl_subtotal,
                                prorate_amount,
                                prorate_amount_2 as cnl_disc_see,
                                prorate_amount - prorate_amount_2 as cnl_disc_sor,
                                is_type_discount_f_see,
                                free_product_id,
                                promotion,
                                origin_inv_line_id,
                                invoice_id
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
                            cn.*,
                            cnl_quantity,
                            cnl.prorate_amount as cnl_disc_all,
                            cnl_disc_see as cnl_disc_see,
                            cnl_disc_sor as cnl_disc_sor,
                            cnl.cnl_subtotal as cnl_subtotal,
                            0 as amount_delivery_fee,
                            apl.paid_total*(-1) as bank_transfer,
                            'Sale Order (Cash)'::text as session_no_and_so
                        from
                            temp_cn cn
                        inner join (
                            select
                                quantity as cnl_quantity,
                                quantity*price_unit as cnl_subtotal,
                                prorate_amount,
                                prorate_amount_2 as cnl_disc_see,
                                prorate_amount - prorate_amount_2 as cnl_disc_sor,
                                is_type_discount_f_see,
                                free_product_id,
                                promotion,
                                origin_inv_line_id,
                                invoice_id
                            from
                                account_invoice_line) cnl on
                            cnl.invoice_id = cn.cn_id
                            and cnl.promotion = false
                            and cnl.is_type_discount_f_see = false
                            and cnl.free_product_id is null
                        inner join account_invoice_payment_line ail on
                            cn_id = ail.invoice_id
                        inner join account_payment_line apl on
                            apl.payment_id = ail.payment_id
                        inner join account_payment_method_multi apmm on
                            apmm.id = apl.payment_method_id
                        inner join (
                            select
                                aj.*
                            from
                                account_journal aj
                            left join redeem_type re on aj.redeem_type_id = re.id
                            where
                                aj.type = 'cash'
                                and (re.id is null) or (re.id is not null and re.is_bank_transfer = true) ) ajn on
                            apmm.journal_id = ajn.id
                        where
                            cn.sale_payment_type in ('cash',
                            'deposit')
                            and cn.state = 'paid'
                        union
                        select
                            cn.*,
                            product_uom_qty as cnl_quantity,
                            sol_disc_all as cnl_disc_all,
                            sol_disc_see as cnl_disc_see,
                            sol_disc_sor as cnl_disc_sor,
                            adl.paid_total as cnl_subtotal,
                            amount_delivery_fee*(-1) as amount_delivery_fee,
                            adl.paid_total*(-1) as bank_transfer,
                            'Sale Order (Cash)'::text as session_no_and_so
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
                                prorate_amount as sol_disc_all,
                                prorate_amount - prorate_amount_2 as sol_disc_sor,
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
                        left join temp_delivery_fee dfee on dfee.order_id = so_id
                        inner join (
                            select
                                aj.*
                            from
                                account_journal aj
                            left join redeem_type re on aj.redeem_type_id = re.id
                            where
                                aj.type = 'cash'
                                and (re.id is null) or (re.id is not null and re.is_bank_transfer = true) ) ajn on
                            adl.journal_id = ajn.id
                        where
                            cn.sale_payment_type in ('deposit')
                            and cn.state = 'paid'
                            and cn_parent_invoice_id is null
                        ),
                        /* with 7 */
                        temp_cn_so as (
                        select
                            so_id,
                            session_no_and_so,
                            sale_payment_type,
                            sum(cnl_disc_all) as cnl_disc_all,
                            sum(cnl_disc_sor) as cnl_disc_sor,
                            sum(cnl_disc_see) as cnl_disc_see,
                            sum(amount_delivery_fee) as delivery_fee,
                            min(amount_total_signed) as amount_total_signed,
                            min(bank_transfer) as bank_transfer
                        from
                            temp_cn_total
                        group by so_id,session_no_and_so,sale_payment_type
                        ),
                        /* with 8 */
                        temp_cn_cash_credit as (
                        select
                            session_no_and_so,
                            sum(round((amount_total_signed - cnl_disc_all)::DECIMAL,2)) as sub_total,
                            sum(round(cnl_disc_all::DECIMAL,2)) as discount_by_all,
                            sum(round(cnl_disc_sor::DECIMAL,2)) as discount_by_sor,
                            sum(round(cnl_disc_see::DECIMAL,2)) as discount_by_see,
                            sum(round(delivery_fee::DECIMAL,2)) as delivery_fee,
                            sum(round(amount_total_signed::DECIMAL,2)) as total,
                            sum(round(bank_transfer::DECIMAL,2)) as bank_transfer
                        from
                            temp_cn_so
                        group by session_no_and_so
                        ),
                        /* with 9 */
                        temp_so_cash_credit as (
                        select
                            session_no_and_so as session_no_and_so,
                            sub_total as sub_total,
                            amount_discount_by_sor as discount_by_sor,
                            0 as discount_by_see,
                            0 as delivery_fee,
                            sub_total + amount_discount_by_sor as total,
                            total_and_bank_transfer as bank_transfer,
                            true as is_pos,
                            false as is_so
                        from
                            (
                            select
                                sum(amount_discount_by_sor) as amount_discount_by_sor,
                                session_no_and_so,
                                sum(sub_total) as sub_total,
                                sum(total_and_bank_transfer) as total_and_bank_transfer
                            from
                                (
                                select
                                    pos.id as pos_id,
                                    pos.name as session_no_and_so,
                                    (
                                    select
                                        case
                                            when sum(l.price_subtotal_wo_discount_incl) is not null then sum(l.price_subtotal_wo_discount_incl)
                                            else 0
                                        end
                                    from
                                        pos_order_line l
                                    where
                                        l.order_id = pod.id
                                        and l.reward_type = 'discount'
                                        and l.promotion = true
                                        and l.free_product_id is null ) as amount_discount_by_sor,
                                    sum(pod.before_discount) as sub_total,
                                    (
                                    select
                                        sum(abl.amount) as total_and_bank_transfer
                                    from
                                        account_bank_statement_line abl
                                    inner join (
                                        select
                                            aj.*
                                        from
                                            account_journal aj
                                    left join redeem_type re on aj.redeem_type_id = re.id
                                    where
                                        aj.type = 'cash'
                                        and (re.id is null) or (re.id is not null and re.is_bank_transfer = true) ) ajn on
                                        abl.journal_id = ajn.id
                                    where
                                        pod.id = abl.pos_statement_id ) as total_and_bank_transfer,
                                    (
                                    select
                                        case
                                            when type = 'cash' then true
                                        end as is_cash
                                    from
                                        account_bank_statement_line abl
                                    inner join (
                                        select
                                            aj.*
                                        from
                                            account_journal aj
                                    left join redeem_type re on aj.redeem_type_id = re.id
                                    where
                                        aj.type = 'cash'
                                        and (re.id is null) or (re.id is not null and re.is_bank_transfer = true) ) ajn on
                                        abl.journal_id = ajn.id
                                    where
                                        pod.id = abl.pos_statement_id
                                    group by
                                        type ) as is_cash
                                from
                                    (
                                    select
                                        *
                                    from
                                        pos_order
                                    where
                                        daily_summary_franchise_id is null /* Parameter */
                                        and branch_id = %s
                                        and (date_order + interval '7 hours')::date < %s
                                        and state not in ('draft',
                                        'paid',
                                        'cancel') ) pod
                                inner join pos_session pos on
                                    pod.session_id = pos.id
                                group by
                                    pod.id,
                                    pos_id ) pos
                            where
                                is_cash = true
                            group by
                                session_no_and_so ) pos_data
                        union select
                            session_no_and_so as session_no_and_so,
                            sub_total as sub_total,
                            amount_discount_by_sor as discount_by_sor,
                            amount_discount_by_order*(-1) as discount_by_see,
                            delivery_fee as delivery_fee,
                            sub_total + amount_discount_by_sor + amount_discount_by_order*(-1) + delivery_fee as total,
                            case when so_data.type_sale_ofm is true then sub_total + amount_discount_by_sor + delivery_fee
                            	else sub_total + amount_discount_by_sor 
                            end as bank_transfer,
                            false as is_pos,
                            true as is_so
                        from
                            (
                            select
                                sod.session_no_and_so as session_no_and_so,
                                type_sale_ofm,
                                sum(sod.before_discount) as sub_total,
                                sum(sod.amount_discount_by_sor) as amount_discount_by_sor,
                                sum(sod.amount_discount_by_order) as amount_discount_by_order,
                                sum(sod.amount_total) as total_and_bank_transfer,
                                sum(sod.amount_delivery_fee_special + sod.amount_delivery_fee_by_order) as delivery_fee
                            from
                                (
                                select
                                    t_sod.before_discount as before_discount,
                                    adl.paid_total as amount_total,
                                    amount_discount_by_sor,
                                    amount_discount_by_order,
                                    amount_delivery_fee_special,
                                    amount_delivery_fee_by_order,
                                    so_date_order,
                                    t_sod.type_sale_ofm,
                                    'Sale Order (Cash)'::text as session_no_and_so
                                from
                                    temp_sale_order t_sod
                                inner join account_deposit ads on
                                    t_sod.id = ads.sale_id
                                    and ads.state not in ('draft', 'cancel')
                                inner join account_deposit_payment_line adl on
                                    ads.id = adl.payment_id
                                inner join (
                                    select
                                        aj.*
                                    from
                                        account_journal aj
                                    left join redeem_type re on aj.redeem_type_id = re.id
                                    where
                                        aj.type = 'cash'
                                        and (re.id is null) or (re.id is not null and re.is_bank_transfer = true) ) ajn on
                                    adl.journal_id = ajn.id
                                where
                                    sale_payment_type in ('cash',
                                    'deposit')
                            union
                                select
                                    before_discount,
                                    amount_total,
                                    amount_discount_by_sor,
                                    amount_discount_by_order,
                                    amount_delivery_fee_special,
                                    amount_delivery_fee_by_order,
                                    so_date_order,
                                    type_sale_ofm,
                                    'Sale Order (Credit Term)'::text as session_no_and_so
                                from
                                    temp_sale_order
                                where
                                    sale_payment_type = 'credit' ) sod
                            group by
                                sod.session_no_and_so,
                                type_sale_ofm) so_data
                        )
                        select session_no_and_so,
                            sum(sub_total) as sub_total,
                            sum(discount_by_sor) as discount_by_sor,
                            sum(discount_by_see) as discount_by_see,
                            sum(delivery_fee) as delivery_fee,
                            sum(total) as total,
                            sum(bank_transfer) as bank_transfer
                        from(
                        select so.session_no_and_so,
                                so.sub_total as sub_total,
                                so.discount_by_sor  as discount_by_sor,
                                so.discount_by_see as discount_by_see,
                                so.delivery_fee as delivery_fee,
                                so.total as total,
                                so.bank_transfer as bank_transfer	
                        from temp_so_cash_credit so
                        union
                        select cn.session_no_and_so,
                                round(cn.sub_total::DECIMAL,2) as sub_total,
                                round(cn.discount_by_sor::DECIMAL,2)  as discount_by_sor,
                                round(cn.discount_by_see::DECIMAL,2) as discount_by_see,
                                round(cn.delivery_fee::DECIMAL,2) as delivery_fee,
                                round(cn.total::DECIMAL,2) as total,
                                case when cn.session_no_and_so = 'Sale Order (Credit Term)' 
                                then round(cn.sub_total::DECIMAL,2) + round(cn.discount_by_sor::DECIMAL,2)
                                else round(cn.bank_transfer::DECIMAL,2)*(-1) - round(cn.discount_by_see::DECIMAL,2) end as bank_transfer
                        from temp_cn_cash_credit cn
                        ) sale_cn
                        group by session_no_and_so
                        """, parameter_detail)

                daily_summary_franchise_line_list = item._cr.dictfetchall()
                if item.kerry_cash > 0.00:
                    daily_summary_franchise_line_list += [
                        {
                            'session_no_and_so': 'Kerry (Cash)',
                            'sub_total': item.kerry_cash,
                            'discount_by_sor': 0.00,
                            'discount_by_see': 0.00,
                            'delivery_fee': 0.00,
                            'total': item.kerry_cash,
                            'bank_transfer': item.kerry_cash,
                        },
                    ]
                item._cr.execute("""
                    select 'ยอดสรุปการชำระเงิน'::text as name,
                           sum(ail.paid_amount) as total
                    from (
                          select *
                          from account_payment
                          /* Parameter */
                          where branch_id = %s
                                and (payment_date + interval '7 hours')::date = %s
                                and state in ('posted', 'reconciled')
                         ) acp
                    inner join account_invoice_payment_line ail on acp.id = ail.payment_id
                    inner join account_invoice aci on ail.invoice_id = aci.id
                    inner join (
                                select *
                                from sale_order
                                where sale_payment_type = 'credit'
                               ) sao on aci.so_id = sao.id
                                        """, parameter_credit_term)

                daily_summary_franchise_credit_term_list = item._cr.dictfetchall()

                daily_summary_franchise_cash_list = [
                    {
                        'name': 'Cash (POS)',
                        'total': item.pos_cash,
                    },
                    {
                        'name': 'Cash (Sale Order)',
                        'total': item.so_cash,
                    },
                    {
                        'name': 'ยอดรับชำระเครดิตเทอม',
                        'total': item.credit_term,
                    },
                    {
                        'name': 'Cash (Kerry)',
                        'total': item.kerry_cash,
                    },
                ]

                if len(daily_summary_franchise_line_list) > 0 or len(daily_summary_franchise_credit_term_list) > 0:
                    new_daily_summary_franchise_obj = item.env['daily.summary.franchise'].create({
                            'company_id': item.branch_id.pos_company_id.id,
                            'date': item.date,
                            'branch_id': item.branch_id.id,
                            'store_code': item.branch_id.branch_code,
                            'store_name': item.branch_id.name,
                            'daily_summary_franchise_line_ids': [
                                (0, 0, x) for x in daily_summary_franchise_line_list
                            ],
                            'daily_summary_franchise_credit_term_ids': [
                                (0, 0, x) for x in daily_summary_franchise_credit_term_list
                            ],
                            'daily_summary_franchise_cash_ids': [
                                (0, 0, x) for x in daily_summary_franchise_cash_list
                            ],
                        })
                    if item.is_auto_cal == True:
                        new_daily_summary_franchise_obj.write({'state': 'verify'})
                    if daily_summary_first == True:
                        new_daily_summary_franchise_obj.write({'is_backdate': True})

                    
                    if not daily_summary_first:
                        parameter_update_pos_so = (
                            new_daily_summary_franchise_obj.id,
                            item.branch_id.id,
                            back_day,
                            next_day,
                            back_day,
                            next_day,
                            back_day,
                            next_day,
                            item.branch_id.id,
                            back_day,
                            next_day,
                            item.branch_id.id,
                            new_daily_summary_franchise_obj.id,
                            new_daily_summary_franchise_obj.id,
                            item.branch_id.id,
                            back_day,
                            next_day,
                            new_daily_summary_franchise_obj.id,
                            item.branch_id.id,
                            back_day,
                            next_day,
                        )
                        item._cr.execute("""
                            /* Update POS */

                            update pos_order
                            set daily_summary_franchise_id = %s
                            from (
                                select distinct pod.id as pos_id
                                from (
                                    select *
                                    from pos_order
                                    /* Parameter */
                                    where daily_summary_franchise_id is null
                                    and branch_id = %s
                                    and (date_order + interval '7 hours')::date >= %s
                                    and (date_order + interval '7 hours')::date < %s
                                    and state not in ('draft', 'paid', 'cancel')
                                    ) pod
                                inner join account_bank_statement_line abl on pod.id = abl.pos_statement_id
                                inner join (
                                    select
                                        aj.*
                                    from
                                        account_journal aj
                                    left join redeem_type re on aj.redeem_type_id = re.id
                                    where
                                        aj.type = 'cash'
                                        and (re.id is null) or (re.id is not null and re.is_bank_transfer = true)
                                    ) ajn on abl.journal_id = ajn.id
                                inner join pos_session pos on pod.session_id = pos.id
                                ) pos_result
                            where id = pos_result.pos_id;
                            
                            /* Update SO */

                            WITH temp_sale_order as (
                                    select
                                        s_sod.id,
                                        so_date_order,
                                        sale_payment_type
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
                                            state in ('open', 'paid')
                                            and (date_invoice + interval '7 hours')::date >= %s
                                            and (date_invoice + interval '7 hours')::date < %s
                                            and type = 'out_invoice') aiv on
                                        s_sod.id = aiv.so_id
                                        and so_id is not null
                                    where
                                        sale_payment_type in ('cash', 'credit')
                                        and (
                                                (s_sod.type_sale_ofm = true
                                                and (s_sod.so_date_order + interval '7 hours')::date >= %s
                                                and (s_sod.so_date_order + interval '7 hours')::date < %s)
                                                or (s_sod.type_sale_ofm = false and aiv.id is not null)
                                            )
                                        and daily_summary_franchise_id is null
                                        /* Parameter */
                                        and s_sod.branch_id = %s
                                        and s_sod.state in ('sale', 'done')
                                    union
                                    select
                                        s_sod.id,
                                        so_date_order,
                                        sale_payment_type
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
                                            state in ('open', 'paid')
                                            and (date + interval '7 hours')::date >= %s
                                            and (date + interval '7 hours')::date < %s
                                        ) ads on s_sod.id = ads.sale_id and ads.state not in ('draft', 'cancel')
                                    where
                                        sale_payment_type = 'deposit'
                                        and daily_summary_franchise_id is null
                                        /* Parameter */
                                        and s_sod.branch_id = %s
                                        and s_sod.state in ('sale', 'done')
                                )
                            update sale_order
                            set daily_summary_franchise_id = %s
                            from (
                                select sod.id as so_id
                                from (
                                        select t_sod.id,
                                            t_sod.so_date_order
                                        from temp_sale_order t_sod
                                        inner join account_deposit ads on t_sod.id = ads.sale_id and ads.state not in ('draft', 'cancel')
                                        inner join account_deposit_payment_line adl on ads.id = adl.payment_id
                                        inner join (
                                                    select
                                                        aj.*
                                                    from
                                                        account_journal aj
                                                    left join redeem_type re on aj.redeem_type_id = re.id
                                                    where
                                                        aj.type = 'cash'
                                                        and (re.id is null) or (re.id is not null and re.is_bank_transfer = true)
                                                ) ajn on adl.journal_id = ajn.id
                                        where sale_payment_type in ('cash','deposit')
                                        union
                                        select id,
                                            so_date_order
                                        from temp_sale_order
                                        where sale_payment_type = 'credit'
                                    ) sod
                                ) so_result
                            where id = so_result.so_id;

                            /* Update CN */
                            update account_invoice cn
                            set daily_summary_franchise_id = %s
                            from (
                            select
                                cn.id
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
                                and so.branch_id = %s
                                and (date_invoice + interval '7 hours')::date >= %s
                                and (date_invoice + interval '7 hours')::date < %s
                                and cn.type = 'out_refund'
                                and cn.daily_summary_franchise_id is null /* Parameter */
                                and so.sale_payment_type = 'credit'
                            ) cn_credit_term
                            where
	                            cn.id = cn_credit_term.id ;
                            
                            update account_invoice cn
                            set daily_summary_franchise_id = %s
                            from (
                            select
                                cn.id
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
                            /* Parameter */
                            where
                                cn.state in ('paid')
                                and am.state = 'posted'
                                and so.branch_id = %s
                                and (am.payment_date + interval '7 hours')::date >= %s
                                and (am.payment_date + interval '7 hours')::date < %s
                                and cn.type = 'out_refund'
                                and cn.daily_summary_franchise_id is null /* Parameter */
                                and so.sale_payment_type != 'credit'
                            ) cn_cash_card
                            where
	                            cn.id = cn_cash_card.id ;
                            """, parameter_update_pos_so)
                    else:
                        parameter_update_pos_so = (
                            new_daily_summary_franchise_obj.id,
                            item.branch_id.id,
                            next_day,
                            next_day,
                            next_day,
                            item.branch_id.id,
                            next_day,
                            item.branch_id.id,
                            new_daily_summary_franchise_obj.id,
                            new_daily_summary_franchise_obj.id,
                            item.branch_id.id,
                            next_day,
                            new_daily_summary_franchise_obj.id,
                            item.branch_id.id,
                            next_day,
                        )
                        item._cr.execute("""
                            /* Update POS */

                            update pos_order
                            set daily_summary_franchise_id = %s
                            from (
                                select distinct pod.id as pos_id
                                from (
                                    select *
                                    from pos_order
                                    /* Parameter */
                                    where daily_summary_franchise_id is null
                                    and branch_id = %s
                                    and (date_order + interval '7 hours')::date < %s
                                    and state not in ('draft', 'paid', 'cancel')
                                    ) pod
                                inner join account_bank_statement_line abl on pod.id = abl.pos_statement_id
                                inner join (
                                    select
                                        aj.*
                                    from
                                        account_journal aj
                                    left join redeem_type re on aj.redeem_type_id = re.id
                                    where
                                        aj.type = 'cash'
                                        and (re.id is null) or (re.id is not null and re.is_bank_transfer = true)
                                    ) ajn on abl.journal_id = ajn.id
                                inner join pos_session pos on pod.session_id = pos.id
                                ) pos_result
                            where id = pos_result.pos_id;
                            
                            /* Update SO */

                            WITH temp_sale_order as (
                                    select
                                        s_sod.id,
                                        so_date_order,
                                        sale_payment_type
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
                                            state in ('open', 'paid')
                                            and (date_invoice + interval '7 hours')::date < %s
                                            and type = 'out_invoice') aiv on
                                        s_sod.id = aiv.so_id
                                        and so_id is not null
                                    where
                                        sale_payment_type in ('cash', 'credit')
                                        and (
                                                (s_sod.type_sale_ofm = true
                                                and (s_sod.so_date_order + interval '7 hours')::date < %s)
                                                or (s_sod.type_sale_ofm = false and aiv.id is not null)
                                            )
                                        and daily_summary_franchise_id is null
                                        /* Parameter */
                                        and s_sod.branch_id = %s
                                        and s_sod.state in ('sale', 'done')
                                    union
                                    select
                                        s_sod.id,
                                        so_date_order,
                                        sale_payment_type
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
                                            state in ('open', 'paid')
                                            and (date + interval '7 hours')::date < %s
                                        ) ads on s_sod.id = ads.sale_id and ads.state not in ('draft', 'cancel')
                                    where
                                        sale_payment_type = 'deposit'
                                        and daily_summary_franchise_id is null
                                        /* Parameter */
                                        and s_sod.branch_id = %s
                                        and s_sod.state in ('sale', 'done')
                                )
                            update sale_order
                            set daily_summary_franchise_id = %s
                            from (
                                select sod.id as so_id
                                from (
                                        select t_sod.id,
                                            t_sod.so_date_order
                                        from temp_sale_order t_sod
                                        inner join account_deposit ads on t_sod.id = ads.sale_id and ads.state not in ('draft', 'cancel')
                                        inner join account_deposit_payment_line adl on ads.id = adl.payment_id
                                        inner join (
                                                    select
                                                        aj.*
                                                    from
                                                        account_journal aj
                                                    left join redeem_type re on aj.redeem_type_id = re.id
                                                    where
                                                        aj.type = 'cash'
                                                        and (re.id is null) or (re.id is not null and re.is_bank_transfer = true)
                                                ) ajn on adl.journal_id = ajn.id
                                        where sale_payment_type in ('cash','deposit')
                                        union
                                        select id,
                                            so_date_order
                                        from temp_sale_order
                                        where sale_payment_type = 'credit'
                                    ) sod
                                ) so_result
                            where id = so_result.so_id;

                            /* Update CN Credit Term */
                            update account_invoice cn
                            set daily_summary_franchise_id = %s
                            from (
                            select
                                cn.id
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
                                and so.branch_id = %s
                                and (date_invoice + interval '7 hours')::date < %s
                                and cn.type = 'out_refund'
                                and cn.daily_summary_franchise_id is null /* Parameter */
                                and so.sale_payment_type = 'credit'
                            ) cn_credit_term
                            where
	                            cn.id = cn_credit_term.id ;
                            /* Update CN Cash Card */
                            update account_invoice cn
                            set daily_summary_franchise_id = %s
                            from (
                            select
                                cn.id
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
                            /* Parameter */
                            where
                                cn.state in ('paid')
                                and am.state = 'posted'
                                and so.branch_id = %s
                                and (am.payment_date + interval '7 hours')::date < %s
                                and cn.type = 'out_refund'
                                and cn.daily_summary_franchise_id is null /* Parameter */
                                and so.sale_payment_type != 'credit'
                            ) cn_cash_card
                            where
	                            cn.id = cn_cash_card.id ;
                                                """, parameter_update_pos_so)

                if item.is_auto_cal is False:
                    return navigate_data
            else:
                raise except_orm(_('PIN not match.'))
