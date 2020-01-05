# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from openerp.exceptions import except_orm, Warning, RedirectWarning,UserError
import datetime



class InternalUse(models.Model):
    _name = "internal.use"
    _inherit = ['mail.thread']
    _description = "Internal Use"
    _order = 'id desc'
    _rec_name = 'number'

    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))

    name = fields.Char(
        string = 'Internal Reference',
        readonly = True,
        states = {'draft': [('readonly', False)]}
    )

    number = fields.Char(
        readonly = True,
        default = 'Draft'
    )

    state = fields.Selection(
        [('draft', 'Draft'),
        ('confirm', 'To approve'),
        ('done', 'Validate'),
        ('cancel', 'Cancelled')],
        default = 'draft',
        track_visibility = 'onchange'
    )

    inventory_date = fields.Date(
        string = 'Finish Date',
        default = fields.Datetime.now(),
        required = True,
        readonly = True
    )

    date_done = fields.Date(
        string = 'Start Date',
        default = fields.Datetime.now(),
        required = True,
        readonly = True
    )

    company_id = fields.Many2one(
        'res.company',
        string = 'Company',
        required = True,
        track_visibility='onchange',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string = 'Branch',
        required = True,
        track_visibility = 'onchange',
        readonly = True,
        states = {'draft': [('readonly', False)]}
    )

    location_id = fields.Many2one(
        'stock.location',
        string = 'Inventory Location',
        default = _default_location_id,
        required = True,
        track_visibility = 'onchange',
        readonly = True,
        states = {'draft': [('readonly', False)]}
    )

    user_id = fields.Many2one(
        'res.users',
        string = 'User',
        required = True,
        readonly = True,
        track_visibility = 'onchange',
        default = lambda self: self.env.user
    )

    internal_use_line_ids = fields.One2many(
        'internal.use.line',
        'internal_use_id',
        states = {'done': [('readonly', True)]}
    )

    move_ids = fields.One2many(
        'stock.move', 'internal_use_id', string='Created Moves',
        states={'done': [('readonly', True)]})

    account_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Stock Journal"
    )

    @api.one
    def action_cancel(self):
        self.state = 'cancel'
        return

    @api.one
    def action_to_approve(self):
        vals = {'number':self.get_iu_no()[0]}
        self.write(vals)
        self.state = 'confirm'
        return

    @api.one
    def get_iu_no(self):
        if not all([
            self.branch_id,
            self.branch_id.warehouse_id,
        ]):
            return 'Draft'

        ctx = dict(self._context)
        ctx.update({'res_model': 'internal.use'})

        prefix = 'IU-' + self.branch_id.branch_code + '%(y)s%(month)s'
        iu_no = self.branch_id.with_context(ctx).next_sequence(self.inventory_date, prefix, 5) or '/'
        return iu_no

    @api.multi
    def post_inventory(self):
        # The inventory is posted as a single step which means quants cannot be moved from an internal location to another using an inventory
        # as they will be moved to inventory loss, and other quants will be created to the encoded quant location. This is a normal behavior
        # as quants cannot be reuse from inventory location (users can still manually move the products before/after the inventory if they want).
        self.mapped('move_ids').filtered(lambda move: move.state != 'done').action_done()
    
    @api.one
    def action_done(self):
        negative = next((line for line in self.mapped('internal_use_line_ids') if line.product_qty < 0), False)
        if negative:
            raise UserError(_('You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s') % (negative.product_id.name, negative.product_qty))
        self.action_check()
        self.write({
            'state': 'done',
            'date_done': fields.Datetime.now(),
        })
        self.post_inventory()
        return True

    @api.multi
    def action_check(self):
        """ Checks the inventory and computes the stock move to do """
        # tde todo: clean after _generate_moves
        for inventory in self:
            # first remove the existing stock moves linked to this inventory
            inventory.mapped('move_ids').unlink()
            for line in inventory.internal_use_line_ids:
                # compare the checked quantities on inventory lines to the theorical one
                stock_move = line._generate_moves()         

    @api.multi
    def write(self, values):
        masege_obj = self.env['mail.message']
        body=''
        if 'internal_use_line_ids' in values:
            for val in values['internal_use_line_ids']:
                if val[0] != 5:
                    line = self.env['internal.use.line'].browse(val[1])
                    if not val[0] and not val[1] and val[2]:
                        if 'product_id' in val[2]:
                            product = self.env['product.product'].browse(val[2]['product_id'])
                            body += '&bull; ' + 'Add product: ' + product.product_tmpl_id.name
                            if 'product_qty' in val[2]:
                                body += ' with quntity: ' + str(val[2]['product_qty'])
                            if 'reason_id' in val[2]:
                                reason_id = self.env['internal.use.reason'].browse(val[2]['reason_id'])
                                body += ' for ' + reason_id.name
                            body += '</p>'
                    elif val[2]:
                        if 'product_id' in val[2]:
                            product = self.env['product.product'].browse(val[2]['product_id'])
                            condition=''
                            if 'product_qty' in val[2]:
                                condition = ' with quantity: ' + str(val[2]['product_qty'])
                            body += '&bull; ' + 'Change product: ' + line.product_name + ' &rArr; ' + product.product_tmpl_id.name + condition + '<p/>'
                        if 'product_qty' in val[2]:
                            body += '&bull; ' + 'Edit quantity of ' + line.product_name + ':  ' + str(line.product_qty) + ' &rArr; ' + str(val[2]['product_qty']) + '<p/>'
                        if 'reason_id' in val[2]:
                            reason_id = self.env['internal.use.reason'].browse(val[2]['reason_id'])
                            body += '&bull; ' + 'Edit reason of ' + line.product_name + ':  ' + line.reason_id.name + ' &rArr; ' + reason_id.name + '<p/>'
        if body != '':
            body = "<div style='background-color: rgb(228 ,228 ,228);'>{}</div>".format(body)
            message_qty_before = len(masege_obj.search
                                    ([('model', '=', 'internal.use'),('res_id', '=', self.id)]))
            res = super(InternalUse, self).write(values)
            message_qty_after = len(masege_obj.search
                                    ([('model', '=', 'internal.use'), ('res_id', '=', self.id)]))
            if message_qty_before != message_qty_after:
                masege_id = masege_obj.search([
                ('model', '=', 'internal.use'),
                ('res_id', '=', self.id), ], limit=1)
                masege_id.write({'body': body})
            else:
                messg_vals = {
                        'model': 'internal.use',
                        'res_id': self.id,
                        'parent_id': False,
                        'body': body,
                        'date': datetime.datetime.now()
                    }
                masege_obj.create(messg_vals)
        else:
            res = super(InternalUse, self).write(values)
        
        return res


class InternalUseLine(models.Model):
    _name = "internal.use.line"
    _description = "Internal Use Line"

    internal_use_id = fields.Many2one(
        'internal.use',
        string = 'Internal Use'
    )
    company_id = fields.Many2one(
        'res.company',
        string = 'Company',
        related = 'internal_use_id.company_id'
    )
    reason_id = fields.Many2one(
        'internal.use.reason',
        string = 'Reason',
        required = True,
    )
    product_id = fields.Many2one(
        'product.product',
        string = 'Product',
        required = True
    )
    product_name = fields.Char(
        string = 'Product',
        related = 'product_id.name'
    )
    product_qty = fields.Integer(
        string = 'Quantity',
        required = True,
    )
    product_uom_id = fields.Many2one(
        'product.uom',
        string = 'Unit of Measure',
        compute = "_compute_uom",
        store = True
    )
    royalty_fee = fields.Float(
        string='Royalty Fee',
        readonly=True
    )

    @api.onchange('product_qty')
    def onchange_product_qty(self):
        cost = self.env['average.price'].search([('product_id', '=', self.product_id.id),('branch_id', '=', self.internal_use_id.branch_id.id)], order="id desc", limit=1)
        self.royalty_fee = cost.cost * self.product_qty * 0.05

    @api.one
    @api.depends('product_id')
    def _compute_uom(self):
        self.product_uom_id = self.product_id.product_tmpl_id.uom_id

    @api.multi
    def write(self, vals):
        if 'product_qty' in vals:
            self.check_available()
        line = super(InternalUseLine, self).write(vals)
        return line

    @api.multi
    def create(self, vals):
        if 'product_qty' in vals and 'product_id' in vals and 'internal_use_id' in vals:
            use_id = self.env['internal.use'].browse(vals['internal_use_id'])
            product_id = self.env['product.product'].browse(vals['product_id'])
            self.check_create_available(product_id, use_id.location_id, vals['product_qty'])
        line = super(InternalUseLine, self).create(vals)
        return line
            
    def check_create_available(self, product_id, location_id, qty):
        availability = product_id.with_context({
                'compute_child': False,
                'location': location_id.id,
            })._product_available()
        pd_qty = availability[product_id.id]['qty_available']
        if qty < 0:
            raise UserError(_('You cannot set a negative product quantity in an unternal use line:\n\t%s - qty: %s') % (product_id.name, qty))
        elif qty > pd_qty:
            raise UserError(_('You cannot set quantity more than onhand quantity \n\t%s - onhand quantity: %s') % (product_id.name, pd_qty))

    
    def check_available(self):
        availability = self.product_id.with_context({
                'compute_child': False,
                'location': self.internal_use_id.location_id.id,
            })._product_available()
        qty = availability[self.product_id.id]['qty_available']
        if self.product_qty < 0:
            raise UserError(_('You cannot set a negative product quantity in an unternal use line:\n\t%s - qty: %s') % (self.product_id.name, self.product_qty))
        elif self.product_qty > qty:
            raise UserError(_('You cannot set quantity more than onhand quantity \n\t%s - onhand quantity: %s') % (self.product_id.name, qty))

    def _get_quants(self):
        return self.env['stock.quant'].search([
            ('company_id', '=', self.internal_use_id.company_id.id),
            ('location_id', '=', self.internal_use_id.location_id.id),
            ('product_id', '=', self.product_id.id)
        ])

    def _get_move_values(self, qty, location_id, location_dest_id):
        self.ensure_one()
        return {
            'name': _('INT:') + (self.internal_use_id.name or ''),
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': qty,
            'date': self.internal_use_id.inventory_date,
            'company_id': self.internal_use_id.company_id.id,
            'internal_use_id': self.internal_use_id.id,
            'state': 'confirmed',
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'credit_account_id': self.reason_id.credit_account_id.id,
            'debit_account_id': self.reason_id.debit_account_id.id,
            'origin': self.internal_use_id.number,
        }

    def _fixup_negative_quants(self):
        """ This will handle the irreconciable quants created by a force availability followed by a
        return. When generating the moves of an inventory line, we look for quants of this line's
        product created to compensate a force availability. If there are some and if the quant
        which it is propagated from is still in the same location, we move it to the inventory
        adjustment location before getting it back. Getting the quantity from the inventory
        location will allow the negative quant to be compensated.
        """
        self.ensure_one()
        temp = self._get_quants().filtered(lambda q: q.propagated_from_id.location_id.id == self.internal_use_id.location_id.id)
        for quant in temp:
            # send the quantity to the inventory adjustment location
            move_out_vals = self._get_move_values(quant.qty, self.internal_use_id.location_id.id, self.product_id.property_stock_inventory.id)
            move_out = self.env['stock.move'].create(move_out_vals)
            self.env['stock.quant'].quants_reserve([(quant, quant.qty)], move_out)
            move_out.action_done()

            # get back the quantity from the inventory adjustment location
            move_in_vals = self._get_move_values(quant.qty, self.product_id.property_stock_inventory.id, self.internal_use_id.location_id.id)
            move_in = self.env['stock.move'].create(move_in_vals)
            move_in.action_done()

    def _generate_moves(self):
        moves = self.env['stock.move']
        Quant = self.env['stock.quant']
        for line in self:
            line._fixup_negative_quants()
            diff = line.product_qty
            vals = line._get_move_values(abs(diff), line.internal_use_id.location_id.id, line.product_id.property_stock_inventory.id)
            move = moves.create(vals)
        return moves
