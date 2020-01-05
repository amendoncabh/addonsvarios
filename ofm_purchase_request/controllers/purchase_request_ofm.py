# -*- coding: utf-8 -*-
from datetime import datetime

from odoo.http import Controller, route, request
import logging
import time

_logger = logging.getLogger(__name__)


class PurchaseRequestOFMAPI(Controller):

    def update_shipping_address(self, ship_id, ship_ref):
        message_shipping = ''

        if all([
            ship_ref,
            ship_id,
        ]):
            partner_id = request.env['res.partner'].sudo().browse(ship_ref)

            if 'vendor_ship_id' in partner_id._fields:
                if partner_id:
                    if partner_id.vendor_ship_id != ship_id:
                        partner_id.update({
                            'vendor_ship_id': ship_id,
                        })

                        message_shipping = 'Success'
                    else:
                        partner_id.update({
                            'is_update_shipping': False,
                        })

                        message_shipping = 'Update Shipping Address success because OFM sent ship_id.'
                else:
                    message_shipping = 'No Shipping Address'
            else:
                return False
        elif all([
            not ship_ref,
            ship_id,
        ]):
            message_shipping = 'No Ship Ref'
        elif all([
            ship_ref,
            not ship_id,
        ]):
            message_shipping = 'No Ship ID'

        return message_shipping

    @route('/pr/update_status', type='json', auth='user')
    def api_pr_update_status(self, pr_list):
        date_start = datetime.now()
        is_log_parameter_input = request.env['ir.config_parameter'].search([
            ('key', '=', 'is_log_parameter_input')
        ]).value

        if is_log_parameter_input:
            _logger.info("purchase_order : parameter_input --> " + str(pr_list))

        is_check_state = False
        response_return = []
        count_success = 0
        count_error = 0

        for pr in pr_list:
            message_shipping = ''
            response_code = ''
            response_message = ''
            status_odoo = ''
            pr_no = pr.get('pr_no')
            status = pr.get('status')
            so_no = pr.get('so_no', False)
            ship_id = pr.get('ship_id', False)
            ship_ref = pr.get('ship_ref', False)

            try:
                purchase_order = request.env['purchase.order'].sudo().search([
                    ('name', '=', pr_no),
                ])

                if not purchase_order:
                    response_code = '500'
                    response_message = pr_no + ' not found.'
                else:
                    if so_no:
                        purchase_order.update({
                            'vendor_so_no': so_no,
                        })

                    if status.lower() == 'pending':
                        is_check_state = purchase_order.button_pending()
                        status_odoo = 'Pending'
                    elif status.lower() == 'confirmed':
                        is_check_state = purchase_order.button_confirm()
                        status_odoo = 'Completed'
                    elif status.lower() == 'deleted':
                        ctx = dict(purchase_order._context)
                        ctx.update({'from_api':True})
                        is_check_state = purchase_order.with_context(ctx).button_cancel()
                        status_odoo = 'Cancelled'
                    elif status.lower() == 'fail':
                        is_check_state = purchase_order.button_draft()
                        status_odoo = 'PR'

                    if all([
                        is_check_state,
                        status_odoo != ''
                    ]):
                        response_code = '200'
                        response_message = 'Success'
                        message_shipping = self.update_shipping_address(ship_id, ship_ref)
                    else:
                        response_code = '500'
                        response_message = 'Status: '
                        response_message += status
                        response_message += ', not permit update status or not match.'
            except Exception as e:
                response_code = '500'
                response_message = e.message if e.message != '' else e.name
            finally:
                response = {
                    "pr_no": pr_no,
                    "status": status,
                    "status_odoo": status_odoo,
                    "code": response_code,
                    "message": response_message
                }

                if all([
                    message_shipping,
                    any([
                        ship_id,
                        ship_ref,
                    ])
                ]):
                    response.update({
                        "ship_id": ship_id,
                        "ship_update_status": message_shipping
                    })

                if response_code == '200':
                    request.env.cr.commit()
                    count_success += 1
                else:
                    count_error += 1

                _logger.info(str(response))
                response_return.append(response)
                time.sleep(1)

        date_end = datetime.now()
        _logger.info(
            "purchase_order : api_update_status PR Amount: {0} Start Time: {1} End Time: {2} Success {3} Error {4}".format(
                len(pr_list),
                date_start,
                date_end,
                count_success,
                count_error,
            )
        )

        return response_return

    @route('/rtv/update_status', type='json', auth='user')
    def api_rtv_update_status(self, rt_list):
        response_code = ''
        response_message = ''
        status_odoo = ''
        response_return = []
        rtv_no = ''

        for rt in rt_list:
            rt_no = rt.get('rt_no')
            status = rt.get('status')

            try:
                stock_picking = request.env['stock.picking'].sudo().search([
                    ('name', '=', rt_no),
                ])
                stock_picking_id = stock_picking.id
                invoice_id = request.env['account.invoice'].sudo().search([
                    ('picking_id', '=', stock_picking_id)
                ])

                if not stock_picking:
                    response_code = '500'
                    response_message = rt_no + ' not found.'
                else:
                    if status.lower() == 'confirmed':
                        invoice_id.action_invoice_open()
                        rtv_no = invoice_id.number
                        status_odoo = 'open'
                    else:
                        response_code = '500'
                        response_message = rt_no + ' can\'t update status because ' \
                                                   'current status not permit update status ' + status + '.'

                response_code = '200'
                response_message = 'Success'
            except Exception as e:
                response_code = '500'
                response_message = e.message
            finally:
                response = {
                    "rtv_no": rtv_no,
                    "status": status,
                    "status_odoo": status_odoo,
                    "code": response_code,
                    "message": response_message
                }

                if response_code == '200':
                    _logger.info("account_invoice : api_update_status --> " + str(response))
                else:
                    _logger.error("account_invoice : api_update_status --> " + str(response))

                response_return.append(response)

        return response_return