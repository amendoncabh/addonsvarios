# -*- coding: tis-620 -*-

from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta
import os
import codecs
from pytz import timezone

tools.config['batch_file_path'] = tools.config.get('batch_file_path', '/opt/ofm_the_one_card/batch/')
BATCH_PATH = tools.config['batch_file_path']
DELIMITED_SYMBOL = '|'
TRANSACTION_LINE_LIMIT = 100000
DAT_FILE_TITLE = 'BCH_OFMFCH_T1C_NRTSales'


class PosOrder(models.Model):
    _inherit = 'pos.order'

    batch_done = fields.Boolean(
        string='Batch Done',
        default=False,
    )


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    batch_done = fields.Boolean(
        string='Batch Done',
        default=False,
    )


class PosSoBatch(models.AbstractModel):
    _name = 'pos.so.batch'

    def get_pos_so_to_file(self):

        now = datetime.now(timezone('Asia/Bangkok'))

        # dat_file_count use for count for a batch file to summarise on .ctrl file
        dat_file_count = 1

        dat_sequence = "%04d" % dat_file_count
        dat_file_name = DAT_FILE_TITLE + '_' + \
                        now.strftime('%d%m%Y') + '_' + \
                        now.strftime('%H%M%S') + '.dat' + '.' + dat_sequence

        # Get batch_path from .cfg file 'batch_file_path' parameter
        batch_file_path_by_date = BATCH_PATH

        # Parameters
        # batch_data use to arrange data from query into batch file format
        batch_data = ''
        # trans_seq use for replace into SourceTransID on the sequence section (001, 002, ....)
        trans_seq = 1
        # total_rec use for count transaction line of current batch file
        # it will stamp on the header
        total_rec = 0
        # rec_count use for count all record in selected date to summarise on .ctrl file
        rec_count = 0

        detail_query_str = '''WITH PosOrderNO as (
                select
                po.id ,
                po.return_order_id
                from
                pos_order po
                where
                po.batch_done is not true
                and po.state not in ('draft',
                'cancel') 
            ),
            PosReturnOrderNO as (
                select
                return_po.id as pos_id,
                return_po.return_order_id as original_id,
                pol.id as pos_line_id,
                pol.original_line_id as orginal_line_id,
                row_number() over (partition by pol.order_id
                order by
                pol.id) as row_no,
                return_po.return_order_id,
                origin_inv.inv_no as inv_no,
                origin_inv.date_order as po_date,
                pb.branch_code as pb_branch_code
                from
                pos_order_line pol
                left join pos_order return_po on
                return_po.id = pol.order_id
                left join (
                select
                    id,
                    inv_no,
                    date_order,
                    session_id
                from
                    pos_order
                order by
                    id )origin_inv on
                origin_inv.id = return_po.return_order_id
                left join pos_session ps on
                ps.id = origin_inv.session_id
                left join pos_config pc on
                pc.id = ps.config_id
                left join pos_branch pb on
                pb.id = pc.branch_id
                where
                return_po.batch_done is not true
                and return_po.state not in ('draft',
                'cancel')
                and (return_po.is_return_order is true
                or return_po.is_void_order is true)
                and pol.promotion_name is null
                or pol.promotion_name = '' ),
                PosReturnSeq as (
                select
                row_number() over (partition by pol.order_id
                order by
                pol.id) as row_no,
                pol.id as pos_line_id
                from
                (
                select
                    distinct original_id
                from
                    PosReturnOrderNO ) return_pos
                inner join pos_order_line pol on
                return_pos.original_id = pol.order_id
                where
                pol.promotion_name is null
                or pol.promotion_name = '' 
            ),
            PosData as (
                select
                bis.pos_id,
                bis.original_id,
                bis.pos_line_id,
                bis.orginal_line_id,
                OrderNO.row_no as orgin_row_no,
                bis.row_no,
                bis.inv_no as orgin_inv_no,
                bis.po_date as po_date,
                bis.pb_branch_code as pb_branch_code,
                'P'::varchar as transsubtype,
                0 as absl_id
                from
                PosReturnOrderNO bis
                inner join PosReturnSeq OrderNO on
                bis.orginal_line_id = OrderNO.pos_line_id
                union all
                select
                po.id as pos_id,
                null as orginal_id,
                pol1.id as pos_line_id,
                null as orginal_line_id,
                null as orgin_row_no,
                row_number() over (partition by pol1.order_id
                order by
                pol1.id) as row_no,
                null as orgin_inv_no,
                null as po_date,
                null as pb_branch_code,
                'P'::varchar as transsubtype,
                0 as absl_id
                from
                pos_order_line pol1
                inner join (
                select
                    id
                from
                    pos_order
                where
                    batch_done is not true
                    and state not in ('draft',
                    'cancel')
                    and is_return_order is not true
                    and is_void_order is not true ) po on
                pol1.order_id = po.id
                left join PosReturnSeq OrderNO on
                pol1.id = OrderNO.pos_line_id
                where
                pol1.promotion_name is null
                or pol1.promotion_name = ''
                union all
                -------T

                select po.id as pos_id,
                po.return_order_id as orginal_id,
                null as pos_line_id,
                null as orginal_line_id,
                case
                    when ReturnNO.inv_no is not null 
                    then row_number() over (partition by po.id order by po.id)
                    else null
                end as orgin_row_no,
                row_number() over (partition by po.id order by po.id) as row_no,
                ReturnNO.inv_no as orgin_inv_no,
                ReturnNO.po_date as po_date,
                ReturnNO.pb_branch_code as pb_branch_code,
                'T'::varchar as transsubtype,
                absl.id as absl_id
                from
                account_bank_statement_line absl
                inner join PosOrderNO po on
                po.id = absl.pos_statement_id
                left join(
                select
                    distinct re.pos_id ,
                    re.original_id,
                    re.inv_no,
                    re.po_date,
                    re.pb_branch_code
                from
                    PosReturnOrderNO re )ReturnNO on
                ReturnNO.pos_id = po.id
                where
                absl.name not like '%return%'
                union all
                ------A

                select po.id as pos_id,
                po.return_order_id as orginal_id,
                null as pos_line_id,
                null as orginal_line_id,
                case
                    when ReturnNO.inv_no is not null  
                    then row_number() over (partition by po.id order by po.id)
                    else null
                end as orgin_row_no,
                row_number() over (partition by po.id
                order by
                po.id) as row_no,
                ReturnNO.inv_no as orgin_inv_no,
                ReturnNO.po_date as po_date,
                ReturnNO.pb_branch_code as pb_branch_code,
                'A'::varchar as transsubtype,
                0 as absl_id
                from
                PosOrderNO po
                left join(
                select
                    distinct re.pos_id ,
                    re.original_id,
                    re.inv_no,
                    re.po_date,
                    re.pb_branch_code
                from
                    PosReturnOrderNO re )ReturnNO on
                ReturnNO.pos_id = po.id 
            ),
            Pos_batch as (
                select
                '1'::varchar as lnidentifier,
                concat( 'OFMFCH', '_', 'SOFC' , pb.branch_code, '_', po.inv_no, '_', '#No#', '_', to_char(now(), 'dd_HH24MISSMS') ) as sourcetransid,
                concat( 'SOFC' , pb.branch_code )as storeno,
                pc.pos_no as pos_no,
                concat( 'SOFC' , pb.branch_code, po.inv_no, to_char(po.date_order + interval '7 hour', 'DDHH24MI') ) as receiptno,
                case
                    when po.is_return_order then '07'
                    when po.is_void_order then '09'
                    else '01'
                end as transtype,
                --------------------P and C (Coupon)-------------------------
                case when pt.is_coupon = True
            then 'C'::VARCHAR
            else pdt.transsubtype 
            end as transsubtype,
            -------------------------------------------------------------
                to_char(po.date_order + interval '7 hour', 'DDMMYYYY_HH24:MI:SS:MS') as transdate,
                to_char(po.date_order + interval '7 hour', 'DDMMYYYY') as businessdate,
                ''::varchar as invoicedate,
                ''::varchar as deliverydate,
                'N'::varchar as earnonlineflag,
                coalesce( case when po.the_one_card_no = 'N/A' then '' else po.the_one_card_no end, '' ) as theonecardno,
                coalesce( case when po.phone_number = 'N/A' then '' else po.phone_number end, '' ) as mobileno,
                ''::varchar as userid,
                pdt.row_no as itemseqno,
                coalesce(pt.sku_ofm, '') as productcode,
                coalesce(pp.barcode, '') as productbarcode,
                coalesce( round(abs(pol.qty), 4) , 1.0000::numeric ) as quantity,
                round(abs(pol.price_unit), 4) as priceunit,
                case
                    when pol.promotion_id is not null then abs(round(abs(coalesce(pol.price_subtotal_wo_discount_incl,0)::numeric), 4) - round(abs(coalesce(posl_free_product.price_subtotal_wo_discount_incl, 0) )::numeric, 4))
                    else round(abs(pol.price_subtotal_wo_discount_incl::numeric), 4)
                end as pricetotal,
                case
                    when pol.promotion_id is not null then abs(round(abs(coalesce(pol.price_unit,0)::numeric), 4) - round(abs(coalesce(posl_free_product.price_unit,0))::numeric, 4))
                    else round(abs(pol.price_unit::numeric), 4)
                end as netpriceunit,
                case
                    when pdt.transsubtype = 'T' then
                case
                    when aj.type = 'cash' 
                    then round(abs(absl.amount), 4) + coalesce(absl_return.return_amount, 0)
                    else round(abs(absl.amount), 4)
                end
                    when pdt.transsubtype = 'A' 
            then round(abs(po.amount_total), 4)
                    else
                case
                when pol.promotion_id is not null then abs(round(abs(coalesce(pol.price_subtotal_incl,0)::numeric), 4) - round(abs(coalesce(posl_free_product.price_subtotal_incl,0))::numeric, 4))
                else round(abs(pol.price_subtotal_incl::numeric), 4)
                end
                end as netpricetotal,
                case
                    when pol.promotion_id is not null then abs(round(abs(pol.prorate_amount::numeric), 4) - round(abs(posl_free_product.price_subtotal_incl)::numeric, 4))
                    when pdt.transsubtype = 'A' then 0.0000::numeric
                    else round(abs(pol.prorate_amount::numeric), 4)
                end as discounttotal,
                case
                    when pol.promotion_id is not null then round(abs(0), 4)
                    when pdt.transsubtype = 'A' then round(abs(po.amount_tax), 4)
                    else round((round(abs(pol.price_subtotal_incl), 4) - round(abs(pol.price_subtotal), 4)) / round(abs(pol.qty), 4), 4)
                end as vatamount,
                case
                    when pdt.transsubtype = 'T' then
                    case
                    when aj.type = 'bank' then upper(absl.credit_card_type)::varchar
                    else upper(aj.name)::varchar
                    end
                    else ''
                end as tendertype,
                case
                    when pdt.transsubtype = 'T' then
                    case
                    when aj.is_credit_card is true then overlay(absl.credit_card_no placing 'xxxxxx' from 7 for 6)
                    else ''::varchar
                    end
                    else ''
                end as tenderrefno,
                case
                    when po.is_return_order is true
                    or po.is_void_order is true then concat( 'SOFC' , pdt.pb_branch_code, pdt.orgin_inv_no, to_char(pdt.po_date + interval '7 hour', 'DDHH24MI') )
                    else ''
                end as originalreceiptno,
                pdt.orgin_row_no as originalitemsequenceno,
                po.inv_no as displayreceiptno,
                case
                    when po.is_return_order is true then
                    case
                    when round(abs(return_po.amount_total), 4) = round(abs(po.amount_total), 4) then 'Y'
                    else 'N'
                    end
                    else ''::varchar
                end as returnallflag,
                'pos'::varchar as type_batch,
                pdt.pos_id as no_id,
                po.branch_id as branch_id
                from PosData pdt
                left join pos_order_line pol on pdt.pos_line_id = pol.id or pdt.pos_line_id = null
                left join account_bank_statement_line absl on absl.id = pdt.absl_id
                left join account_journal aj on aj.id = absl.journal_id
                left join pos_order po on po.id = pol.order_id or po.id = pdt.pos_id
                left join pos_session ps on ps.id = po.session_id
                left join pos_config pc on pc.id = ps.config_id
                left join pos_branch pb on pb.id = pc.branch_id
                left join product_product pp on pp.id = pol.product_id
                left join product_template pt on pt.id = pp.product_tmpl_id
                left join(
                    select
                    distinct posl_free_product.order_id,
                    posl_free_product.promotion_id,
                    posl_free_product.free_product_id,
                    posl_free_product.price_subtotal_wo_discount_incl,
                    posl_free_product.price_unit,
                    posl_free_product.price_subtotal_incl
                from
                    pos_order_line posl_free_product
                where
                    posl_free_product.free_product_id is not null --posl_free_product.promotion is true 
                )posl_free_product on posl_free_product.order_id = pol.order_id
                    and posl_free_product.free_product_id = pol.product_id 
                    and posl_free_product.promotion_id = pol.promotion_id
                    and pol.promotion is true 
                left join(
                select
                    distinct return_po.id,
                    return_po.amount_total
                from
                    pos_order return_po
                left join pos_session return_ps on return_ps.id = return_po.session_id
                left join pos_config return_pc on return_pc.id = return_ps.config_id
                left join pos_branch return_pb on return_pb.id = return_pc.branch_id
                order by return_po.id 
                 )return_po on return_po.id = po.return_order_id
                left join(
                select
                    distinct absl.pos_statement_id,
                    sum(absl.amount) as return_amount
                from
                    account_bank_statement_line absl
                left join account_journal aj on aj.id = absl.journal_id
                where absl.name like '%return%'
                group by absl.pos_statement_id 
                )absl_return on absl_return.pos_statement_id = po.id
                left join(
                select
                    distinct posl.order_id,
                    sum(posl.prorate_amount) as prorate_amount
                from
                    pos_order_line posl
                where
                    posl.promotion_name is null
                    or posl.promotion_name = ''
                group by posl.order_id
                order by posl.order_id 
                )pol_total on pol_total.order_id = po.id
                ------------Not Coupon Show--------------------------
            where pt.is_coupon is not True 
                -------------------------------------
                order by
                pdt.pos_id asc ,
                pdt.pos_line_id ,
                transsubtype desc,
                row_no 
            ),
            ------------------------END--POS--------------------------------------------
            ------------------------Start--SO--------------------------------------------
	      So_order as (
                select so.id as id,
                   so.so_date_order as so_date_order,
                   accinv.id as inv_id,
                   accinv.number as inv_number,
                   accinv.parent_invoice_id as parent_invoice_id,
                   case when accinv.type = 'out_refund'
                    then True
                    else False
                   end as inv_order_return,
                   case when accinv.parent_invoice_id is null
                    then True
                    else False
                   end as deposit_order_return,
                   so.sale_payment_type as sale_payment_type
                from ( 
                   select accinv.so_id,  
                    accinv.id,
                    accinv.number,
                    accinv.type,
                    accinv.parent_invoice_id as parent_invoice_id,
                    accinv.state
                   from account_invoice accinv 
                    where so_id is not null
			and batch_done is not true
			and accinv.state in ('open', 'paid')
                )accinv
                inner join (
                    select
                    so.id ,
                    so.so_date_order,
                    so.sale_payment_type
                    from
                    sale_order so
                    where
                    so.state not in ('draft', 'cancel', 'sent') 
                )so on so.id = accinv.so_id
                where accinv.state = 'paid' or (so.sale_payment_type = 'credit' and accinv.state = 'open')
                order by id
            ),
    So_DeliveryFee as(
		select so.id,
			so.inv_id,
			sum(inv_l.amount_subtotal) as price_total,
			'T' as tender,
			'A' as amount
		from So_order so
		inner join (
			select id, invoice_id, amount_subtotal
			from account_invoice_line
			where name like 'Delivery%'
		)inv_l on inv_l.invoice_id = so.inv_id
		group by so.id, so.inv_id, tender, amount
            ),
    SoTender as (

                select 
			so.id as so_id,
			--row_number() over (partition by so.inv_id order by so.id) as row_no,
			null as originseqno,
			'T'::varchar as transsubtype,
			adpt.id as adpt_id,
			adpt_line.id as adpt_line,
			null as spt_id, --sp.spt_id as spt_id,
			so.inv_id, 
			so.inv_number,
			so.inv_order_return,
			so.deposit_order_return,
			null as cn_line_id,
			so.parent_invoice_id as parent_invoice_id,
			apl.id as cn_payment_id,
			null as prorate_vat,
			so.sale_payment_type as sale_payment_type,
			---------------------------------
			coalesce( abs(round(abs(apl.paid_total::numeric), 4)),0) + coalesce(abs(round(abs(adpt_line.paid_total::numeric), 2)),0) as amount_pay
                from
                So_order so

                ----------------Deposit----------------------
		left join (
		    select
		    adpt.id ,
		    adpt.sale_id
		    from
		    account_deposit adpt
		    where
		    adpt.state not in ('draft', 'cancel', 'sent') 
                 )adpt on adpt.sale_id = so.id 
                 ----------------Deposit-Line---------------------
                left join account_deposit_payment_line adpt_line  on adpt_line.payment_id = adpt.id
                and so.deposit_order_return = True --and so.inv_order_return = True
                ---------------CN Invoice-----------------------------
                left join account_invoice_payment_line aip on aip.invoice_id = so.inv_id and aip.paid_amount != 0
                left join account_payment_line apl on apl.payment_id = aip.payment_id 
                 ----------------Credit Term---------------------------


            )

            ,
            SoData as (
                ---------------------------P   
                select so.id as so_id,
                row_number() over (partition by so.inv_id order by accinv_line.id) as row_no,
                null as originseqno,
                'P'::varchar as transsubtype,
                null as adpt_id,
                null as adpt_line,
                null as spt_id,
                so.inv_id, 
                so.inv_number,
                so.inv_order_return,
                so.deposit_order_return,
                accinv_line.id as cn_line_id,
                so.parent_invoice_id as parent_invoice_id,
                null as cn_payment_id,
                ( (round(abs(coalesce(accinv_line.amount_subtotal,0)), 4) - round(abs(coalesce(accinv_line.price_subtotal,0)), 4)) 
                   - ( round(abs( coalesce(accinv_line.amount_subtotal_w_discount_incl,0) ), 4) - round(abs( coalesce(accinv_line.amount_subtotal_w_discount,0) ), 4) )
                ) - round(abs(coalesce(accinv_line.prorate_amount::numeric, 0)),4 ) as prorate_vat,
                null as sale_payment_type
                from  So_order so
                left join(
			select *
			from account_invoice_line accinv_line
                ------no promotion
                ------and  no DeliveryFee
			where accinv_line.promotion_name is null
			and NOT (name like 'Delivery %')    
			order by accinv_line.id
                )accinv_line on accinv_line.invoice_id = so.inv_id

                --------------------END P
                union all
                --------------------T

		 select 
			so_id,
			row_number() over (partition by inv_id order by amount_pay DESC) as row_no,
			null as originseqno,
			'T'::varchar as transsubtype,
			adpt_id,
			adpt_line,
			null as spt_id, --sp.spt_id as spt_id,
			inv_id, 
			inv_number,
			inv_order_return,
			deposit_order_return,
			null as cn_line_id,
			parent_invoice_id,
			cn_payment_id,
			null as prorate_vat,
			sale_payment_type
                from SoTender  

                --------------------END T
                union all
                --------------------A

                select so.id as so_id,
                row_number() over (partition by so.inv_id order by so.id) as row_no,
                null as originseqno,
                'A'::varchar as transsubtype,
                null as adpt_id,
                null as adpt_line,
                null as spt_id, --sp.spt_id as spt_id,
                so.inv_id, 
                so.inv_number,
                so.inv_order_return,
                so.deposit_order_return,
                null as cn_line_id,
                so.parent_invoice_id as parent_invoice_id,
                null as cn_payment_id,
                null as prorate_vat,
                null as sale_payment_type
                from
                So_order so
                ------------------END A
            order by so_id, inv_id, cn_line_id, transsubtype desc, row_no
            ),
	So_Batch as (
                        select
                            '1'::varchar as lnidentifier,
                            concat( 'OFMFCH', '_', sodt.inv_number, '_', '#No#', '_', to_char(now(), 'dd_HH24MISSMS') ) as sourcetransid,
                            concat( 'SOFC', pb.branch_code )as storeno,
                            ''::varchar as pos_no,
                            concat( accinv.number, '_', to_char(accinv.date_invoice + interval '7 hour', 'dd_HH24MI') ) as receiptno,
                            case
                                when sodt.inv_order_return = True 
                                then '07'
                                else '01'
                            end as transtype,
                --------------------P and C (Coupon)-------------------------
                case when pt.is_coupon = True
                    then 'C'::VARCHAR
                    else sodt.transsubtype 
                end as transsubtype,
                -------------------------------------------------------------
                            to_char(accinv.date_invoice + interval '7 hour', 'DDMMYYYY_HH24:MI:SS:MS') as transdate,
                            to_char(accinv.date_invoice + interval '7 hour', 'DDMMYYYY') as businessdate,
                            ''::varchar as invoicedate,
                            ''::varchar as deliverydate,
                            'N'::varchar as earnonlineflag,
                            coalesce(case when so.the_one_card_no = 'N/A' then '' else so.the_one_card_no end, '' ) as theonecardno,
                            coalesce(case when so.phone_number = 'N/A' then '' else so.phone_number end, '' ) as mobileno,
                            ''::varchar as userid,
                            sodt.row_no as itemseqno,
                            ------------------------product--------------------------------
                            coalesce(pt.sku_ofm, '') as productcode,
                            coalesce(pp.barcode, '') as productbarcode,
                            ------------------------product--detail------------------------------
                    round(abs(coalesce(accinv_line.quantity, 1)), 4) as quantity,
                    round(abs(accinv_line.price_unit), 4) as priceunit,
                            case
                                when accinv_line.promotion_id is not null 
                            then abs(round(abs(coalesce(accinv_line.amount_subtotal, 0)::numeric), 4) - round(abs((invl_free_product.price_total))::numeric, 4))
                                else round(abs(coalesce(accinv_line.amount_subtotal, 0)::numeric), 4)
                            end as pricetotal,
            case
                                when accinv_line.promotion_id is not null then abs(round(abs(accinv_line.price_unit::numeric), 4) - round(abs((invl_free_product.price_unit))::numeric, 4))
                                else round(abs(accinv_line.price_unit::numeric), 4)
                 end as netpriceunit,
                 case
		when sodt.transsubtype = 'T' 
			then    case 
				when so.sale_payment_type = 'credit' and accinv.state = 'open' --Credit Term Payment Stam Show
				    then abs(round(abs(accinv.amount_total_signed::numeric), 2))

				when so.sale_payment_type = 'credit' and accinv.state = 'paid' ---- Payment Receive
				    -- if SI = CN then RV = Faill. So i can stam so.payment_method show now
				    then coalesce( abs(round(abs(apl.paid_total::numeric), 4)), abs(round(abs(accinv.amount_total_signed::numeric), 2))  )

				when sodt.inv_order_return = True AND sodt.deposit_order_return = True  --ReturnDeposit  sodt.parent_invoice_id = null
				    then abs(round(abs(accinv.amount_total_signed::numeric), 4))
				when sodt.inv_order_return = True AND sodt.deposit_order_return = False  -- CN standart 
				    then abs(round(abs(apl.paid_total::numeric), 4))
                        else coalesce(abs(round(abs(adpt_line.paid_total::numeric), 2)), coalesce( abs(round(abs(apl.paid_total::numeric), 4)),0) )

                        --coalesce(abs(round(abs(accinv.amount_total_signed::numeric), 2)), abs(round(abs(accinv.amount_total_signed::numeric), 4)), abs(round(abs(apl.paid_total::numeric), 4)), abs(round(abs(adpt_line.paid_total::numeric), 2)))
                    end
                when sodt.transsubtype = 'A' 
                    then    round(abs(round(abs(accinv.amount_total_signed::numeric), 2)),4) - coalesce(so_delivery.price_total, 0 ) --DeliveryFee
		    else
			    case
				    when accinv_line.promotion_id is not null 
					then abs(round(abs(accinv_line.amount_subtotal::numeric), 4) - round(abs((invl_free_product.price_total))::numeric, 4))
				    else round(abs(accinv_line.amount_subtotal::numeric), 4) - coalesce(round(abs(accinv_line.prorate_amount::numeric), 4), 0)
			    end
	    end as netpricetotal,
                            case
                                when accinv_line.promotion_id is not null 
                            then abs(round(abs(accinv_line.prorate_amount::numeric), 4) - round(abs((invl_free_product.price_total))::numeric, 4))
                                when sodt.transsubtype = 'A' 
                            then 0.0000::numeric
                                else round(abs(accinv_line.prorate_amount::numeric), 4)
                            end as discounttotal,
                            case
                                when accinv_line.promotion_id is not null then round(abs(0), 4)
                                when sodt.transsubtype = 'A' then round(abs(accinv.amount_tax::numeric), 4)
                                else ( round(  (round(abs(accinv_line.amount_subtotal), 4) - round(abs(accinv_line.price_subtotal), 4)) / round(abs(accinv_line.quantity), 4), 4) )
                            -(  round(abs( coalesce(sodt.prorate_vat::numeric, 0) ), 4) )
                            end as vatamount,
                            case
                                when sodt.transsubtype = 'T' then
                                case
				    when so.sale_payment_type = 'credit' and accinv.state = 'open' --Credit Term Payment Stam Show
					then upper(apm_credit.name)::varchar
				    when so.sale_payment_type = 'credit' and accinv.state = 'paid' ---- Payment Receive
				    -- if SI = CN then RV = Faill. So i can stam so.payment_method show now
					then coalesce(upper( coalesce(aj.name, apl_aj.name, apm.name)  )::varchar, upper(apm_credit.name)::varchar)

				    when aj.type = 'bank' OR apl_aj.type = 'bank'
					then upper(coalesce(adpt_line.tender, apl.tender,''))::varchar
				    else upper( coalesce(aj.name, apl_aj.name, apm.name, '')  )::varchar  
				end
				else ''
                            end as tendertype,
                            case
                                when sodt.transsubtype = 'T' then
                                case
                                    when aj.is_credit_card is true OR apl_aj.is_credit_card is true     
					then coalesce(overlay(adpt_line.credit_card_no placing 'xxxxxx' from 7 for 6), overlay(apl.cheque_number placing 'xxxxxx' from 7 for 6) )
				    when so.sale_payment_type = 'credit' and accinv.state = 'open' and so.credit_term_card_no is not null --Credit Term Payment Stam Show 
					then coalesce(overlay(so.credit_term_card_no placing 'xxxxxx' from 7 for 6), '' )
						    else ''::varchar
                                end
                                else ''
                            end as tenderrefno,
                            case
                                when sodt.inv_order_return = True 
                    then concat ( coalesce(return_inv.name , '') || '_' || to_char(return_inv.date_invoice + interval '7 hour', 'dd_HH24MI') )
                                else ''
                            end as originalreceiptno,
                            case
                                when sodt.inv_order_return = True
                                then sodt.row_no
                                else null
                            end as originalitemsequenceno,
                            sodt.inv_number as displayreceiptno,
                            case
                                when sodt.inv_order_return = True
                                then
                            case
                                when round(abs(return_inv.amount_total_signed),0) = round(abs(so.amount_total),0) 
                                or round(abs(accinv.amount_total_signed),0) = round(abs(so.amount_total),0) ---ReturnDeposit
                                then 'Y'
                                else 'N'
                            end
                                else ''::varchar
                            end as returnallflag,
                            'so'::varchar as type_batch,
                            accinv.id as no_id,
                            so.branch_id,
                            case when sodt.transsubtype = 'T' and sodt.row_no  = 1  --DeliveryFee
				then coalesce(so_delivery.price_total, 0 )
				else 0
				end as deliveryfee_price



                        from
                            SoData sodt
                            -------------------account_invoice--------------------------------
                    left join account_invoice accinv on accinv.id = sodt.inv_id
                    left join account_invoice_line accinv_line on accinv_line.id = sodt.cn_line_id
                        left join sale_order so on so.id = sodt.so_id -- or so.id = sol.order_id 
                        left join pos_branch pb on pb.id = so.branch_id
                        left join product_product pp on pp.id = accinv_line.product_id  --pp.id = sol.product_id
                        left join product_template pt on pt.id = pp.product_tmpl_id
                     -------------------account_invoice--------------------------------
                         left join(
                            select
                                distinct return_inv.number as name,
                                return_inv.id as inv_id,
                                return_pb.branch_code as branch_code,
                                return_inv.date_invoice as date_invoice,
                                return_inv.amount_total_signed as amount_total_signed
                            from
                                account_invoice return_inv
                            left join stock_picking sp on sp.origin = return_inv.name
                            left join pos_branch return_pb on return_pb.id = return_inv.branch_id
                            order by return_inv.id 
                        )return_inv on return_inv.inv_id = sodt.parent_invoice_id
                        left join(
                                select
                                    invl_free_product.invoice_id,
                                    invl_free_product.promotion_id,
                                    invl_free_product.free_product_id,
                                    coalesce(invl_free_product.price_unit, 0::numeric) as price_unit,
                                    coalesce(invl_free_product.amount_subtotal, 0::numeric) as price_total, 
                                    coalesce(invl_free_product.price_subtotal, 0::numeric) as price_subtotal ,
                                    invl_free_product.prorate_amount
                                from account_invoice_line invl_free_product
                                where invl_free_product.free_product_id is not null
                            )invl_free_product on invl_free_product.invoice_id = accinv.id and invl_free_product.free_product_id = accinv_line.product_id 
                        and invl_free_product.promotion_id = accinv_line.promotion_id
                        and accinv_line.promotion = True
                     ---------------account Deposit line------------------------------
                        left join account_deposit_payment_line adpt_line on adpt_line.id = sodt.adpt_line AND  sodt.deposit_order_return = True
                        left join account_journal aj on aj.id = adpt_line.journal_id
		    ------------ CN account Payment line --------------------
                    left join account_payment_line apl on apl.id = sodt.cn_payment_id
                    left join account_payment_method_multi apm on apm.id = apl.payment_method_id
                    left join account_journal apl_aj on apl_aj.id = apm.journal_id
                    ------------Credit Term payment Type --------------------
                    left join account_payment_method_multi apm_credit on so.credit_term_tender = apm_credit.id
                    ----------------So_DeliveryFee--------------------
                    left join So_DeliveryFee so_delivery on so_delivery.id = sodt.so_id 
								and so_delivery.inv_id = sodt.inv_id
								and (so_delivery.tender = sodt.transsubtype or so_delivery.amount = sodt.transsubtype) 
            ------------Not Coupon Show--------------------------
            where pt.is_coupon is not True 
            -------------------------------------
                    order by sodt.so_id, sodt.inv_id, sodt.cn_line_id, sodt.transsubtype desc, sodt.row_no
            )
            ----------------END SO------------------------------------------            
            SELECT *,
		        0 as deliveryfee_price
            FROM Pos_batch

            UNION ALL

            SELECT *
            FROM So_Batch
        '''
        if detail_query_str:
            self.env.cr.execute(detail_query_str)
            detail_sale_pos = self.env.cr.dictfetchall()

            # current_transaction_line_count use for count line number for current transaction
            current_transaction_line_count = len(detail_sale_pos)

            # If record of this transaction will make total_rec greater than TRANSACTION_LINE_LIMIT
            # Will set all data to initiate and generate current
            if (total_rec + current_transaction_line_count) > TRANSACTION_LINE_LIMIT:
                self.write_transaction_to_file(batch_data, total_rec, batch_file_path_by_date, dat_file_name, now)
                total_rec = 0
                dat_file_count += 1
                batch_data = ''
                trans_seq = 1

            dat_sequence = "%04d" % dat_file_count
            dat_file_name = DAT_FILE_TITLE + '_' + \
                            now.strftime('%d%m%Y') + '_' + \
                            now.strftime('%H%M%S') + '.dat' + '.' + dat_sequence

            # transaction_data use for store string of current transaction line
            transaction_data = ''
            # key_sequence use for arrange field from dict data into required format
            key_sequence = [
                'lnidentifier',
                'sourcetransid',
                'storeno',
                'pos_no',
                'receiptno',
                'transtype',
                'transsubtype',
                'transdate',
                'businessdate',
                'invoicedate',
                'deliverydate',
                'earnonlineflag',
                'theonecardno',
                'mobileno',
                'userid',
                'itemseqno',
                'productcode',
                'productbarcode',
                'quantity',
                'priceunit',
                'pricetotal',
                'netpriceunit',
                'netpricetotal',
                'discounttotal',
                'vatamount',
                'tendertype',
                'tenderrefno',
                'originalreceiptno',
                'originalitemsequenceno',
                'displayreceiptno',
                'returnallflag'
            ]
            # ----pos_order = update pos_order----
            pos_no = set()
            # ----so_no = update account_invoice----
            so_no = set()
            no_id = ''
            row_no = 0
            DeliveryFee = 0

            for transaction in detail_sale_pos:
                # trasaction_arr to keep data into array format to easily join the DELIMITED_SYMBOL
                transaction_arr = []
                if no_id == transaction['no_id']:
                    row_no += 1
                else:
                    row_no = 1
                    no_id = transaction['no_id']
                    DeliveryFee = 0

                for key_sq in key_sequence:
                    if transaction[key_sq] or transaction[key_sq] == 0:
                        trans = str(transaction[key_sq])
                    else:
                        trans = ''
                    if key_sq == 'sourcetransid':
                        # Runing row no for on_id
                        stransid = trans.replace('#No#', ('%03d' % float(row_no)))
                        trans = stransid

                    if key_sq == 'netpricetotal' and transaction['transsubtype'] == 'T':
                        if transaction['itemseqno'] == 1:
                            DeliveryFee = transaction['deliveryfee_price']
                        if DeliveryFee > 0:
                            DF_payment = transaction['netpricetotal'] - DeliveryFee
                            DeliveryFee = DeliveryFee - transaction['netpricetotal']
                            transaction_arr.append(str(DF_payment))
                        else:
                            transaction_arr.append(trans)
                    else:
                        transaction_arr.append(trans)

                # pos and so add id
                if transaction['type_batch'] == 'pos':
                    pos_no.add(str(transaction['no_id']))
                elif transaction['type_batch'] == 'so':
                    so_no.add(str(transaction['no_id']))

                # Set format for tracsaction_data
                transaction_data = transaction_data + '\n' + DELIMITED_SYMBOL.join(transaction_arr) + DELIMITED_SYMBOL

                # Transaction counter
                trans_seq += 1
                total_rec += 1
                rec_count += 1

            batch_data += transaction_data
            # update pos and sale batch_done = TRUE
            if pos_no:
                params = ','.join(pos_no)
                pos_update = 'UPDATE pos_order set batch_done = True WHERE id in (%s)' % params
                self.env.cr.execute(pos_update)
            if so_no:
                params = ','.join(so_no)
                so_update = 'UPDATE account_invoice set batch_done = True WHERE id in (%s)' % params
                self.env.cr.execute(so_update)
            self._cr.commit()

        self.write_transaction_to_file(batch_data, total_rec, batch_file_path_by_date, dat_file_name, now)
        self.write_ctrl_to_file(dat_file_count, rec_count, batch_file_path_by_date, now)

    def write_transaction_to_file(self, batch_data, total_rec, batch_file_path_by_date, dat_file_name, datetime_now):

        # +7 datetime for localize
        now = datetime_now

        # Check file path is exists ? if not then create a new one
        if not os.path.exists(batch_file_path_by_date):
            os.makedirs(batch_file_path_by_date)

        # Get a file full path, use for send as a parameter to insert value into specific file
        dat_file_full_path = batch_file_path_by_date + '/' + dat_file_name

        batch_file = codecs.open(dat_file_full_path, 'a+', encoding='tis-620')

        header = '0' + DELIMITED_SYMBOL + str(total_rec)
        footer = '\n' + '9' + DELIMITED_SYMBOL + 'END'

        batch_file.write(
            header +
            batch_data +
            footer
        )

        batch_file.close()

    def write_ctrl_to_file(self, dat_file_count, rec_count, batch_file_path_by_date, datetime_now):

        # +7 datetime for localize
        now = datetime_now

        # Generate ctrl file
        ctrl_file_name = DAT_FILE_TITLE + '_' + now.strftime('%d%m%Y') + '_' + now.strftime('%H%M%S') + '.ctrl'
        ctrl_file = codecs.open(batch_file_path_by_date + '/' + ctrl_file_name, 'w+', encoding='tis-620')
        partner_code = 'OFM'
        requester = 'OFM-FCH'
        trans_channel = '005'

        # File Title
        batch_data = DAT_FILE_TITLE + DELIMITED_SYMBOL
        # PartnerCode
        batch_data += partner_code + DELIMITED_SYMBOL
        # TransChannel
        batch_data += trans_channel + DELIMITED_SYMBOL
        # TotalFile
        batch_data += str(dat_file_count) + DELIMITED_SYMBOL
        # TotalRec
        batch_data += str(rec_count) + DELIMITED_SYMBOL
        # BatchDate
        batch_date = now.strftime('%d%m%Y_%H:%M:%S')
        batch_date_millisec = "%03d" % (int(now.strftime('%f')) / 1000)
        batch_date = batch_date + ':' + str(batch_date_millisec)
        batch_data += str(batch_date) + DELIMITED_SYMBOL
        # Requester
        batch_data += requester + DELIMITED_SYMBOL
        # Attribute1 *for future use
        batch_data += DELIMITED_SYMBOL

        ctrl_file.write(batch_data)
        ctrl_file.close()