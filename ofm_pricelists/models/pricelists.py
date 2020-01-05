from odoo import api, fields, models, _
import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta


class Pricelists(models.Model):
    _name = "pricelists"
    _inherit = ['mail.thread']
    _order = 'sequence'

    @api.model
    def _default_sequence(self):
        self.env.cr.execute("select COALESCE(sequence,0) from pricelists order by sequence desc limit 1")

        sequence_returned = self.env.cr.fetchone()

        if sequence_returned is None:
            sequence_returned = 0
        else:
            sequence_returned = sequence_returned[0] + 1

        return sequence_returned

    @api.model
    def _default_start_date(self):
        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc  # get user timezone
        date_start = tz.localize(datetime.today())  # get today date
        date_start = date_start.replace(hour=0, minute=0, second=0)  # Set to 00:00:00 localtime
        date_start = date_start.astimezone(pytz.utc)  # Convert to UTC
        return date_start

    @api.model
    def _default_end_date(self):
        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc  # get user timezone
        date_end = tz.localize(datetime.today() + relativedelta(months=1))  # get today date
        date_end = date_end.replace(hour=23, minute=59, second=59)  # Set to 23:59:59 localtime
        date_end = date_end.astimezone(pytz.utc)  # Convert to UTC
        return date_end

    @api.model
    def _default_pricelists_name(self):
        return 'Price-lists ' + str(self._default_sequence())

    sequence = fields.Integer(
        string="Sequence",
        default=_default_sequence,
        readonly=True,
    )

    name = fields.Char(
        string="Price-lists Name",
        required=True,
        default=_default_pricelists_name,
        track_visibility='onchange',
    )

    branch_ids = fields.Many2many(
        comodel_name="pos.branch",
        string="Branch",
        index=False,
        track_visibility='onchange',
    )

    is_except_branch = fields.Boolean(
        string="Except Branch",
        default=False,
        track_visibility='onchange',
    )

    active = fields.Boolean(
        string="Active",
        default=True,
        track_visibility='onchange',
    )

    start_date = fields.Datetime(
        string="Start Date",
        required=True,
        default=_default_start_date,
        track_visibility='onchange',
    )

    end_date = fields.Datetime(
        string="End Date",
        required=True,
        default=_default_end_date,
        track_visibility='onchange',
    )

    pricelists_line_ids = fields.One2many(
        comodel_name='pricelists.line',
        inverse_name='pricelists_id',
        string='Price-lists Items',
        ondelete='cascade',
        index=True,
    )

    @api.onchange('start_date')
    def onchange_start_date(self):
        default_start_date = self._default_start_date()
        if self.start_date < default_start_date.strftime('%Y-%m-%d %H:%M:%S'):
            self.start_date = default_start_date
        if (self.start_date > self.end_date) and self.end_date:
            self.start_date = None

    @api.onchange('end_date')
    def onchange_end_date(self):
        if (self.start_date > self.end_date) and self.start_date:
            self.end_date = None

    @api.onchange('branch_ids',
                  'is_except_branch')
    def _check_flag_except(self):
        if not self.branch_ids and self.is_except_branch is True:
            self.is_except_branch = False


class PricelistsLine(models.Model):
    _name = "pricelists.line"
    _inherit = ['mail.thread']
    _order = 'pricelists_id, id DESC'

    pricelists_id = fields.Many2one(
        comodel_name="pricelists",
        string="Price-lists Name",
        index=True,
        ondelete='cascade',
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
        track_visibility='onchange',
    )

    price_exc_vat = fields.Float(
        string="Price (Exc. Vat)",
        required=True,
        readonly=True,
        compute="_get_price_exc_vat",
        default=0,
        track_visibility='onchange',
    )

    price_inc_vat = fields.Float(
        string="Price (Inc. Vat)",
        store=True,
        readonly=False,
        default=0,
        track_visibility='onchange',
    )

    retail_price_exc_vat = fields.Float(
        string="Retail Price (Exc. Vat)",
        store=True,
        readonly=True,
        compute="_get_retail_price_exc_vat",
        default=0,
        track_visibility='onchange',
    )

    retail_price_inc_vat = fields.Float(
        string="Retail Price (Inc. Vat)",
        store=True,
        readonly=True,
        compute="_get_retail_price_inc_vat",
        default=0,
        track_visibility='onchange',
    )

    promo_price_exc_vat = fields.Float(
        string="Promotion Price (Exc. Vat)",
        store=True,
        readonly=True,
        compute="_get_promotion_price_exc_vat",
        default=0,
        track_visibility='onchange',
    )

    promo_price_inc_vat = fields.Float(
        string="Promotion Price (Inc. Vat)",
        store=True,
        readonly=True,
        compute="_get_promotion_price_inc_vat",
        default=0,
        track_visibility='onchange',
    )

    different_price = fields.Float(
        string="Diff Price",
        store=True,
        readonly=True,
        compute="_get_different_price",
        default=0,
        track_visibility='onchange',
    )

    active = fields.Boolean(
        string="Active",
        readonly=True,
        related="pricelists_id.active",
    )

    @api.depends('price_inc_vat',
                 'product_id.product_tmpl_id.taxes_id')
    @api.multi
    def _get_price_exc_vat(self):
        for item in self:
            tax_amount = 0
            for tax in item.product_id.taxes_id:
                tax_amount = tax.amount if tax_amount < tax.amount else tax_amount

            item.price_exc_vat = (item.price_inc_vat * 100) / (tax_amount + 100)

    @api.depends('product_id',
                 'product_id.product_tmpl_id.list_price',
                 'product_id.product_tmpl_id.is_promotion')
    @api.multi
    def _get_retail_price_inc_vat(self):
        for item in self:
            item.retail_price_inc_vat = item.product_id.price_normal

    @api.depends('product_id',
                 'product_id.product_tmpl_id.taxes_id',
                 'product_id.product_tmpl_id.list_price',
                 'product_id.product_tmpl_id.is_promotion')
    @api.multi
    def _get_retail_price_exc_vat(self):
        for item in self:
            tax_amount = 0
            for tax in item.product_id.taxes_id:
                tax_amount = tax.amount if tax_amount < tax.amount else tax_amount

            item.retail_price_exc_vat = (item.retail_price_inc_vat * 100) / (tax_amount + 100)

    @api.depends('product_id',
                 'product_id.product_tmpl_id.list_price',
                 'product_id.product_tmpl_id.is_promotion')
    @api.multi
    def _get_promotion_price_inc_vat(self):
        for item in self:
            item.promo_price_inc_vat = item.product_id.price_promotion

    @api.depends('product_id',
                 'product_id.product_tmpl_id.taxes_id',
                 'product_id.product_tmpl_id.list_price',
                 'product_id.product_tmpl_id.is_promotion')
    @api.multi
    def _get_promotion_price_exc_vat(self):
        for item in self:
            tax_amount = 0
            for tax in item.product_id.taxes_id:
                tax_amount = tax.amount if tax_amount < tax.amount else tax_amount

            item.promo_price_exc_vat = (item.promo_price_inc_vat * 100) / (tax_amount + 100)

    @api.depends('price_inc_vat', 'retail_price_inc_vat')
    @api.multi
    def _get_different_price(self):
        for item in self:
            item.different_price = item.retail_price_inc_vat - item.price_inc_vat


class MailTracking(models.Model):
    _inherit = 'mail.tracking.value'
    _order = 'create_date desc'

    update_date = fields.Datetime(
        string="Update Date",
        required=False,
        related="mail_message_id.date",
        store=True,
    )

    update_by_id = fields.Many2one(
        'res.partner',
        string="Update By",
        required=False,
        related='mail_message_id.author_id',
        store=True,
    )

    pricelist_name = fields.Char(
        string="Price-lists Name",
        required=False,
        compute='_get_pricelist_name',
        store=True,
    )

    old_value = fields.Char(
        string="Old Values",
        required=False,
        compute='_get_value',
        store=True,
    )

    new_value = fields.Char(
        string="New Values",
        required=False,
        compute='_get_value',
        store=True,
    )

    @api.depends('old_value_char', 'new_value_char')
    @api.multi
    def _get_pricelist_name(self):
        pricelists_obj = self.env['pricelists']
        pricelists_line_obj = self.env['pricelists.line']

        for record in self:
            if record.mail_message_id.model == 'pricelists':
                record.pricelist_name = pricelists_obj.search([('id', '=', record.mail_message_id.res_id)]).name
            elif record.mail_message_id.model == 'pricelists.line':
                record.pricelist_name = pricelists_line_obj.search([
                    ('id', '=', record.mail_message_id.res_id)
                ]).pricelists_id.name

    @api.depends('old_value_integer',
                 'new_value_integer',
                 'old_value_char',
                 'new_value_char',
                 'old_value_float',
                 'new_value_float',
                 'old_value_datetime',
                 'new_value_datetime',)
    @api.multi
    def _get_value(self):
        Log_obj = self.filtered(
            lambda mail_tracking: mail_tracking.mail_message_id.model in ('pricelists.line', 'pricelists')
        )

        for record in Log_obj:
            if record.field_type == 'boolean':
                record.old_value = 'Yes' if record.old_value_integer == 1 else 'No'
                record.new_value = 'Yes' if record.new_value_integer == 1 else 'No'
            elif record.field_type in ('many2one', 'char'):
                record.old_value = record.old_value_char
                record.new_value = record.new_value_char
            elif record.field_type == 'float':
                record.old_value = record.old_value_float
                record.new_value = record.new_value_float
            elif record.field_type == 'datetime':
                record.old_value = record.old_value_datetime
                record.new_value = record.new_value_datetime

