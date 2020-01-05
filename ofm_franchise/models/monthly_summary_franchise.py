# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class MonthlySummaryFranchise(models.Model):
    _name = "monthly.summary.franchise"
    _order = 'name desc'
    _rec_name = 'name'

    name = fields.Char(
        store=True,
        readonly=True,
        copy=False,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        index=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
        index=True,
        readonly=True,
        related='company_id.currency_id',
        track_visibility='always',
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Salesperson',
        index=True,
        track_visibility='onchange',
        default=lambda self: self.env.user,
    )

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
        readonly=True,
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
        readonly=True,
        default='2019',
    )

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Store Name",
        required=True,
        index=True,
        readonly=True,
    )

    date = fields.Datetime(
        string='Create Date',
        readonly=True,
        default=lambda self: fields.datetime.now()
    )

    state = fields.Selection(
        string="Status",
        selection=[
            ('draft', 'Draft'),
            ('in_process', 'In Process'),
            ('complete', 'Complete'),
            ('cancel', 'Cancelled'),
        ],
        required=True,
        default='draft',
        readonly=True,
    )

    store_code = fields.Char(
        string="Store Code",
        required=True,
        readonly=True,
    )

    attachment_ids = fields.One2many(
        comodel_name='ir.attachment',
        inverse_name='res_id',
        string='Attachments',
        domain=lambda self: [('res_model', '=', self._name)],
        auto_join=True, )

    monthly_summary_franchise_assets_ids = fields.One2many(
        comodel_name="monthly.summary.franchise.coa",
        inverse_name="monthly_summary_franchise_id",
        string="Assets",
        domain=[('coa_type', '=', 'assets')],
        required=False,
    )

    assets_amount_total = fields.Monetary(
        string='Assets Amount Total',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    monthly_summary_franchise_liabilities_ids = fields.One2many(
        comodel_name="monthly.summary.franchise.coa",
        inverse_name="monthly_summary_franchise_id",
        string="Liabilities",
        domain=[('coa_type', '=', 'liabilities')],
        required=False,
    )

    liabilities_amount_total = fields.Monetary(
        string='Liabilities Amount Total',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    monthly_summary_franchise_revenues_ids = fields.One2many(
        comodel_name="monthly.summary.franchise.coa",
        inverse_name="monthly_summary_franchise_id",
        string="Revenues",
        domain=[('coa_type', '=', 'revenues')],
        required=False,
    )

    revenues_amount_total = fields.Monetary(
        string='Revenues Amount Total',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    monthly_summary_franchise_cog_ids = fields.One2many(
        comodel_name="monthly.summary.franchise.coa",
        inverse_name="monthly_summary_franchise_id",
        string="Cost Of Goods",
        domain=[('coa_type', '=', 'cog')],
        required=False,
    )

    cog_amount_total = fields.Monetary(
        string='Cost Of Goods Amount Total',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    monthly_summary_franchise_expenses_ids = fields.One2many(
        comodel_name="monthly.summary.franchise.coa",
        inverse_name="monthly_summary_franchise_id",
        string="Expenses",
        domain=[('coa_type', '=', 'expenses')],
        required=False,
    )

    expenses_amount_total = fields.Monetary(
        string='Expenses Amount Total',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    amount_total = fields.Monetary(
        string='Amount Total',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    amount_wht_col_see = fields.Monetary(
        string='WHT (COL - See)',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    amount_wht_sor_see = fields.Monetary(
        string='WHT (See - See)',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    amount_wht_see_col = fields.Monetary(
        string='WHT (See - COL)',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    amount_wht_see_sor = fields.Monetary(
        string='WHT (See - Sor)',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    amount_wht_kerry_see = fields.Monetary(
        string='WHT (Kerry - See)',
        compute='_compute_amount',
        readonly=True,
        store=True,
    )

    @api.multi
    @api.depends('monthly_summary_franchise_assets_ids.amount_total',
                 'monthly_summary_franchise_liabilities_ids.amount_total',
                 'monthly_summary_franchise_revenues_ids.amount_total',
                 'monthly_summary_franchise_cog_ids.amount_total',
                 'monthly_summary_franchise_expenses_ids.amount_total', )
    def _compute_amount(self):
        for item in self:
            coa_ids = item.monthly_summary_franchise_assets_ids + \
                      item.monthly_summary_franchise_liabilities_ids + \
                      item.monthly_summary_franchise_revenues_ids + \
                      item.monthly_summary_franchise_cog_ids + \
                      item.monthly_summary_franchise_expenses_ids
            item.assets_amount_total = sum(line.amount_total for line in item.monthly_summary_franchise_assets_ids)
            item.liabilities_amount_total = sum(
                line.amount_total for line in item.monthly_summary_franchise_liabilities_ids)
            item.revenues_amount_total = sum(line.amount_total for line in item.monthly_summary_franchise_revenues_ids)
            item.cog_amount_total = sum(line.amount_total for line in item.monthly_summary_franchise_cog_ids)
            item.expenses_amount_total = 0.0
            for line in item.monthly_summary_franchise_expenses_ids:
                if line.number in (5.3 ,5.4, 5.5):
                    item.expenses_amount_total += line.amount_total
            item.amount_total = sum(coa_ids.mapped('amount_total'))

            # WHT
            item.amount_wht_col_see = abs(sum(
                coa_ids.filtered(lambda a: a.coa_from == 'col' and a.coa_to == 'see').mapped('wht_amount')))
            item.amount_wht_sor_see = abs(sum(
                coa_ids.filtered(lambda a: a.coa_from == 'sor' and a.coa_to == 'see').mapped('wht_amount')))
            item.amount_wht_see_col = abs(sum(
                coa_ids.filtered(lambda a: a.coa_from == 'see' and a.coa_to == 'col').mapped('wht_amount')))
            item.amount_wht_see_sor = abs(sum(
                coa_ids.filtered(lambda a: a.coa_from == 'see' and a.coa_to == 'sor').mapped('wht_amount')))
            item.amount_wht_kerry_see = abs(sum(
                coa_ids.filtered(lambda a: a.coa_from == 'kerry' and a.coa_to == 'see').mapped('wht_amount')))

    @api.multi
    def action_cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def action_in_process(self):
        return self.write({'state': 'in_process'})

    @api.multi
    def action_complete(self):
        return self.write({'state': 'complete'})

    @api.multi
    def action_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def print_monthly_summary_franchise(self):
        for record in self:
            return record.env['report'].get_action(record, 'monthly.summary.franchise.report.jasper')


class MonthlySummaryFranchiseCOA(models.Model):
    _name = "monthly.summary.franchise.coa"

    monthly_summary_franchise_id = fields.Many2one(
        comodel_name="monthly.summary.franchise",
        string="Monthly Summary Franchise",
        required=True,
        index=True,
        ondelete="cascade",
        readonly=True,
    )

    number = fields.Float(
        string="Code",
        digits=(2, 1),
        required=True,
        readonly=True,
    )

    name = fields.Char(
        string='Name',
        store=True,
        readonly=True,
        copy=True,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        index=True,
        readonly=True,
        related='monthly_summary_franchise_id.company_id',
        track_visibility='always',
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
        index=True,
        readonly=True,
        related='company_id.currency_id',
        track_visibility='always',
    )

    amount = fields.Monetary(
        string='Amount',
        copy=True,
        default=0.00,
    )

    amount_total = fields.Monetary(
        string='Amount Total',
        copy=True,
        default=0.00,
    )

    amount_original = fields.Monetary(
        string='Amount Original',
        readonly=True,
        copy=True,
        default=0.00,
    )

    coa_type = fields.Selection(
        string="COA Type",
        selection=[
            ('assets', 'Assets'),
            ('liabilities', 'Liabilities'),
            ('revenues', 'Revenues'),
            ('cog', 'Cost Of Goods'),
            ('expenses', 'Expenses'),
        ],
        required=True,
        readonly=True,
    )

    coa_from = fields.Selection(
        string="From",
        selection=[
            ('col', 'COL'),
            ('sor', 'Sor'),
            ('see', 'See'),
            ('kerry', 'Kerry'),
        ],
        readonly=True,
    )

    coa_to = fields.Selection(
        string="To",
        selection=[
            ('col', 'COL'),
            ('sor', 'Sor'),
            ('see', 'See'),
            ('kerry', 'Kerry'),
        ],
        readonly=True,
    )

    state = fields.Selection(
        string="Status",
        related='monthly_summary_franchise_id.state',
        readonly=True,
    )

    vat = fields.Float(
        string='VAT',
        copy=True,
        default=0.00,
    )

    wht = fields.Float(
        string='WHT',
        copy=True,
        default=0.00,
    )

    vat_amount = fields.Monetary(
        string='VAT Amount',
        copy=True,
        default=0.00,
    )

    wht_amount = fields.Monetary(
        string='WHT Amount',
        copy=True,
        default=0.00,
    )

