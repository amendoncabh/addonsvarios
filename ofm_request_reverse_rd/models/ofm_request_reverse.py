# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models
from odoo import fields
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class OFMRequestReverse(models.Model):
    _name = "ofm.request.reverse"

    create_date = fields.Datetime(
        string='Creation Date',
        readonly=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='User Request',
        readonly=True,
    )
    branch_id = fields.Many2one(
        comodel_name='pos.branch',
        string='Branch',
        readonly=True,
    )
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='RD No.',
        readonly=True,
    )
    picking_status = fields.Selection(
        related="picking_id.state",
        string='Picking Status',
        readonly=True,
    )
    return_reason_id = fields.Many2one(
        comodel_name="return.reason",
        related="picking_id.return_reason_id",
        string="Reason",
        readonly=1,
    )
    reason_reject = fields.Char(
        string='Reason Reject',
        readonly=True
    )

    rtv_type = fields.Selection(
        selection=[
            ('change', 'Re-Delivery'),
            ('cn', 'Credit Note')
        ],
        string='RTV Type',
        readonly='True',
    )

    state = fields.Selection(
        selection=[
            ('waiting', 'Waiting'),
            ('approved', 'Approve'),
            ('rejected', 'Reject')
        ],
        string='Status',
        default='waiting',
        readonly=True,
    )

    @api.multi
    def action_view_reverse_picking(self):
        for record in self:
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': record.picking_id.id,
                'target': 'current',
            }
        return True

    @api.multi
    def action_approve_reverse_picking(self):
        for record in self:
            if record.state == 'waiting':
                record.state = 'approved'
                record.picking_id.update({
                    'not_approve_request': False,
                    'state': 'assigned',
                    'rtv_type': record.rtv_type,
                })
                record.picking_id.force_assign()
        return True

    @api.multi
    def action_approve_wizard(self):
        for record in self:
            view = record.env.ref('ofm_request_reverse_rd.view_ofm_request_reverse_approve')
            # TDE FIXME: same reamrk as above actually
            return {
                'name': _('Are you sure you want to Confirm this?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'ofm.request.reverse.approve',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': record.env.context,
            }

    @api.multi
    def action_reject_wizard(self):
        for record in self:
            view = record.env.ref('ofm_request_reverse_rd.view_ofm_request_reverse_reject_reject')
            # TDE FIXME: same reamrk as above actually
            return {
                'name': _('Reject?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'ofm.request.reverse.reject',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': record.env.context,
            }

    @api.multi
    def action_reject_reverse_picking(self):
        for record in self:
            if record.state == 'waiting':
                record.state = 'rejected'
                record.picking_id.action_cancel()
                record.picking_id.update({
                    'state': 'rejected',
                    'reason_reject': record.reason_reject
                })
        return True
