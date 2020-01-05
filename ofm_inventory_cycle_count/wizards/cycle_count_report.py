# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo import api, fields, models, _
from datetime import datetime

class CycleCountReport(models.TransientModel):
    _name = 'cycle.count.report.wizard'

    select_diff = fields.Selection(
        [('non-diff', 'List all product'),  
        ('diff', 'List different product only')], 
        string="Product list", 
        required=True, 
        default='non-diff'
    )
    output_type = fields.Selection(
        [('pdf', 'PDF'), 
        ('xls', 'Excel')], 
        string="Output type", 
        required=True, 
        default='pdf'
    )
    start_date = fields.Date(
        'Start Date', 
        default=datetime.now()
    )
    end_date = fields.Date(
        'End Date', 
        default=datetime.now()
    )
    cycle_count_ids = fields.Many2many(
        comodel_name='stock.inventory.cycle.count',
        string='Cycle Count Job'
    )
    company_id = fields.Many2one(
        'res.company',
        string = 'Company'
    )
    branch_id = fields.Many2one(
        'pos.branch',
        string = 'Branch',
        domain="[('pos_company_id', '=', company_id)]"
    )

    @api.multi
    def action_print_report(self, data):
        self.ensure_one()
        report_name = 'cycle.count.jasper'
        condition = " "
        condition2 = " "
        params = {
            'start_date': str(self.start_date),
            'end_date': str(self.end_date),
            'company_id': str(self.company_id.id),
            'branch_id': str(self.branch_id.id)
        }
        if self.select_diff == 'diff':
            condition += 'and ccl.diff != 0'
        if self.cycle_count_ids:
            condition2 += 'cc.id in ($P!{0}) and '.format('{cycle_count_ids}')
            params.update({
                'cycle_count_ids': ','.join(map(str, self.cycle_count_ids.ids)),
            })

        sql = """with company_logo as (SELECT value || '/web/binary/company_logo?dbname=' || current_database() AS company_logo,
(now() + INTERVAL '7 hour')::timestamp AS print_date
FROM ir_config_parameter
WHERE key = 'report.image.url'),
company_info as (
	select rec.name ||
       case when cc.branch_id = '00000'
	    then ' สำนักงานใหญ่ '
	    else ' สาขา '|| pob.name ||' สาขาที่ '|| pob.branch_id
       end as company_name,
       coalesce(pob.street,'') || ' ' ||
       coalesce(pob.moo,'') || ' ' ||
       coalesce(pob.alley,'') || ' ' ||
       coalesce(pob.street2,'') || ' ' ||
       coalesce(case when pv.name like '%กรุงเทพ%' then 'แขวง' else 'ตำบล' end|| tmb.name, '') || ' ' ||
       coalesce(case when pv.name like '%กรุงเทพ%' then 'เขต' else 'อำเภอ' end|| amp.name, '') || ' ' ||
       coalesce(case when pv.name like '%กรุงเทพ%'
		     then pv.name
		     else ('จังหวัด' || pv.name)
		end, '') || ' ' ||
       coalesce(zp.name,'') ||
       coalesce(' โทร : ' || pob.phone, '') ||
       ' เลขประจำตัวผู้เสียภาษีอากร: ' || rpn.vat company_addr,
       ccl.value as ccl_value,
       product_code,
       product_name,
       cc.number as number,
       theoretical_qty,
       product_qty,
       diff,
       product_uom_name,
       cc.branch_name as branch_name,
       cc.company_id as cc_company_id,
	   cc.id as cc_id,
       date(cc.write_date) as cc_write_date,
       ccl.counted_number as ccl_counted_number
from stock_inventory_cycle_count cc 
inner join stock_inventory_cycle_count_line ccl	on cc.id = ccl.inventory_id {0}
inner join res_company rec on cc.company_id = rec.id
inner join pos_branch pob on cc.branch_id = pob.id
inner JOIN res_partner rpn ON rec.partner_id = rpn.id
inner JOIN province pv ON pob.province_id = pv.id
inner JOIN amphur amp ON pob.amphur_id = amp.id
inner JOIN tambon tmb ON pob.tambon_id = tmb.id
inner JOIN zip zp ON pob.zip_id = zp.id
where {1}
    DATE(cc.finish_date + interval '7 hours') BETWEEN $P{2}::date AND $P{3}::date
	and (cc.company_id = $P{4}::integer
		  or COALESCE($P{4}, '') = '')
    and (cc.branch_id = $P{5}::integer
        or COALESCE($P{5}, '') = '')
    and cc.state in ('progress','confirm','done')
)
select company_logo,
    print_date,
    product_code,
    product_name,
    number,
    ccl_counted_number,
    theoretical_qty,
    product_qty,
    diff,
    product_uom_name,
    branch_name,
    company_name,
    company_addr,
    coalesce(ccl_value,0) as ccl_value,
    cc_id,
    cc_write_date
from company_info 
cross join company_logo
order by cc_id,
product_code""".format(
    condition,
    condition2,
    '{start_date}',
    '{end_date}',
    '{company_id}',
    '{branch_id}'
)
        params.update({
            'sql': sql
        })
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': {'records': [], 'parameters': params},
        }

    @api.multi
    def action_print_form(self, data):
        self.ensure_one()
        report_name = 'cycle.count.form.jasper'
        condition = " "
        if self.select_diff == 'diff':
            condition += 'and ccl.diff != 0'

        sql = """with company_logo as (SELECT value || '/web/binary/company_logo?dbname=' || current_database() AS company_logo,
(now() + INTERVAL '7 hour')::timestamp AS print_date
FROM ir_config_parameter
WHERE key = 'report.image.url'),
company_info as (
	select rec.name ||
       case when cc.branch_id = '00000'
	    then ' สำนักงานใหญ่ '
	    else ' สาขา '|| pob.name ||' สาขาที่ '|| pob.branch_id
       end as company_name,
       coalesce(pob.street,'') || ' ' ||
       coalesce(pob.moo,'') || ' ' ||
       coalesce(pob.alley,'') || ' ' ||
       coalesce(pob.street2,'') || ' ' ||
       coalesce(case when pv.name like '%กรุงเทพ%' then 'แขวง' else 'ตำบล' end|| tmb.name, '') || ' ' ||
       coalesce(case when pv.name like '%กรุงเทพ%' then 'เขต' else 'อำเภอ' end|| amp.name, '') || ' ' ||
       coalesce(case when pv.name like '%กรุงเทพ%'
		     then pv.name
		     else ('จังหวัด' || pv.name)
		end, '') || ' ' ||
       coalesce(zp.name,'') ||
       coalesce(' โทร : ' || pob.phone, '') ||
       ' เลขประจำตัวผู้เสียภาษีอากร: ' || rpn.vat company_addr,
       ccl.value as ccl_value,
       product_code,
       product_name,
       cc.number as number,
       theoretical_qty,
       product_qty,
       diff,
       product_uom_name,
       cc.branch_name as branch_name,
       cc.company_id as cc_company_id,
	   cc.id as cc_id,
       ccl.last_count as ccl_last_count,
       ccl.counted_number as ccl_counted_number,
       date(cc.create_date) as cc_create_date,
       ccl.barcode as ccl_barcode
from stock_inventory_cycle_count cc 
inner join stock_inventory_cycle_count_line ccl	on cc.id = ccl.inventory_id {0}
inner join res_company rec on cc.company_id = rec.id
inner join pos_branch pob on cc.branch_id = pob.id
inner JOIN res_partner rpn ON rec.partner_id = rpn.id
inner JOIN province pv ON pob.province_id = pv.id
inner JOIN amphur amp ON pob.amphur_id = amp.id
inner JOIN tambon tmb ON pob.tambon_id = tmb.id
inner JOIN zip zp ON pob.zip_id = zp.id
where cc.id = $P!{1}
)
select company_logo,
    print_date,
    product_code,
    product_name,
    number,
    ccl_counted_number,
    theoretical_qty,
    product_qty,
    diff,
    product_uom_name,
    branch_name,
    company_name,
    company_addr,
    coalesce(ccl_value,0) as ccl_value,
    cc_id,
    ccl_last_count,
    cc_create_date,
    ccl_barcode
from company_info 
cross join company_logo
order by cc_id,
product_code""".format(
    condition,
    '{cycle_count_id}'
)
        params = {
            'cycle_count_id': data['active_id'],
            'sql': sql
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': {'records': [], 'parameters': params},
        }

    @api.multi
    def action_print_template(self, data):
        self.ensure_one()
        if self.env.user.has_group('ofm_inventory_cycle_count.group_stock_staff'):
            report_name = 'cycle.count.template.staff.jasper'
        else:
            report_name = 'cycle.count.template.jasper'
        condition = " "
        if self.select_diff == 'diff':
            condition += 'and ccl.diff != 0'

        sql = """select ccl.value as ccl_value,
       product_code,
       product_name,
       cc.number as number,
       theoretical_qty,
       product_qty,
       diff,
       product_uom_name,
       cc.branch_name as branch_name,
       cc.company_id as cc_company_id,
	   cc.id as cc_id,
       ccl.last_count as ccl_last_count,
       ccl.counted_number as ccl_counted_number
from stock_inventory_cycle_count cc 
inner join stock_inventory_cycle_count_line ccl	on cc.id = ccl.inventory_id {0}
inner join res_company rec on cc.company_id = rec.id
inner join pos_branch pob on cc.branch_id = pob.id
inner JOIN res_partner rpn ON rec.partner_id = rpn.id
where cc.id = $P!{1}
order by cc_id,
product_code""".format(
    condition,
    '{cycle_count_id}'
)
        params = {
            'cycle_count_id': data['active_id'],
            'sql': sql
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': {'records': [], 'parameters': params},
        }
