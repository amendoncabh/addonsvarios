# -*- coding: utf-8 -*-

from functools import partial
from itertools import chain
from odoo import SUPERUSER_ID
from odoo import api
from odoo import fields
from odoo import models
from odoo import tools
import threading
import psycopg2
import odoo
import logging
from odoo.osv import osv
from odoo import tools
from datetime import datetime, timedelta
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.exceptions import Warning
from odoo.exceptions import except_orm, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.translate import _
from collections import OrderedDict
from datetime import datetime, timedelta
from odoo.tools import float_round, float_is_zero, float_compare
from odoo.api import Environment
import time
import json
import ast

tools.config['cors_proxy_host'] = tools.config.get('cors_proxy_host', 'localhost')
tools.config['cors_proxy_port'] = tools.config.get('cors_proxy_port', '3000')


def check_int_value(val):
    try:
        int(val)
        return True
    except ValueError:
        return False


class PosOrder(models.Model):
    _inherit = 'pos.order'

    the_one_card_no = fields.Char(
        string="The One Card No.",
        readonly=True,
    )
    # Check member language pref. then select name to display
    member_name = fields.Char(
        string='Member Name',
        readonly=True,
    )
    phone_number = fields.Char(
        string='Member Phone Number',
        readonly=True,
    )
    # national_id = field.Char(
    #     string='National ID',
    #     readonly=True,
    # )
    points_expiry_this_year = fields.Integer(
        string='Point Expiry This Year',
        readonly=True,
    )
    points_balance = fields.Integer(
        string='Points Balance',
        readonly=True,
    )
    membercard = fields.Text(
        string='Membercard dict',
        readonly=True,
    )
    t1c_set = fields.Boolean(
        string='t1c set flag',
        readonly=True,
    )
    pos_offline = fields.Boolean(
        string='POS online flag',
        readonly=True,
    )

    show_cancel_t1cp = fields.Boolean(
        string='Show Cancel T1CP',
        compute="_compute_show_cancel_t1cp"
    )

    @api.depends('statement_ids')
    def _compute_show_cancel_t1cp(self):
        for order in self:
            if order.is_void_order:
                paymentlines = order.statement_ids
                for paymentline in paymentlines:
                    if paymentline.t1cp_receipt_no and not paymentline.api_cancel_success:
                        order.show_cancel_t1cp = True
                        break
            else:
                order.show_cancel_t1cp = False

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)

        if 'expire_this_year' in ui_order['membercard'] and \
                not check_int_value(ui_order['membercard']['expire_this_year']):
            ui_order['membercard']['expire_this_year'] = 0

        if 'balance_points' in ui_order['membercard'] and \
                not check_int_value(ui_order['membercard']['balance_points']):
            ui_order['membercard']['balance_points'] = 0

        if ui_order['t1c_set'] is True and ui_order['pos_offline'] is not True:
            res.update({
                'the_one_card_no': ui_order['membercard']['the_one_card_no'],
                'phone_number': ui_order['membercard']['phone'],
                'points_expiry_this_year': ui_order['membercard']['expire_this_year'],
                'points_balance': ui_order['membercard']['balance_points'],
                'member_name': ui_order['membercard']['member_name'],
                'membercard': ui_order['membercard'],
                't1c_set': ui_order['t1c_set'],
                'pos_offline': ui_order['pos_offline'],
            })
        elif ui_order['t1c_set'] is True and ui_order['pos_offline'] is True:
            res.update({
                'the_one_card_no': ui_order['membercard']['the_one_card_no'],
                'phone_number': ui_order['membercard']['phone'],
                't1c_set': ui_order['t1c_set'],
                'pos_offline': ui_order['pos_offline'],
            })

        return res


    @api.model
    def _payment_fields(self, ui_paymentline):
        res = super(PosOrder, self)._payment_fields(ui_paymentline)
        res.update({
            't1cc_barcode': ui_paymentline['t1cc_barcode'],
            't1cp_receipt_no': ui_paymentline['t1cp_receipt_no'],
            'transactions': ui_paymentline['transactions'],
            'api_to_be_cancelled': ui_paymentline.get('api_to_be_cancelled',False),
            'api_cancel_success': ui_paymentline.get('api_cancel_success',False),
        })
        return res

    @api.model
    def _prepare_bank_statement_line_payment_values(self, data):
        res = super(PosOrder, self)._prepare_bank_statement_line_payment_values(data)
        if 't1cc_barcode' in data:
            res.update({
                't1cc_barcode': data['t1cc_barcode'],
                't1cp_receipt_no': data['t1cp_receipt_no'],
                'transactions': data['transactions'],
                'api_to_be_cancelled': data['api_to_be_cancelled'],
                'api_cancel_success': data['api_cancel_success'],
            })
        return res
    
    
    #T1C functions ==============================================
    @api.model
    def get_cors_proxy(self):
        return tools.config['cors_proxy_host'] + ':' + tools.config['cors_proxy_port']

    @api.multi
    def button_cancel_t1cp(self):
        # import pdb; pdb.set_trace()
        response = self.cancel_batch_t1cp([self.id])
        response_object = json.loads(response)
        if response_object['failed']:
            self.env.user.notify_warning(
                "Response",
                "The following T1CP receipt no. failed to cancel: " + ','.join(response_object['failed']),
            )
        else:
            self.env.user.notify_warning(
                "Response",
                "All T1CP payment lines have successfully cancelled.",
            )
        

    @api.model
    def cancel_batch_t1cp(self, order_ids):
        # import pdb; pdb.set_trace()
        orders = self.browse(order_ids)
        call_api = self.env['tr.call.api']
         
        requests_made = { 'successful': {}, 'failed': [], }
        
        for order in orders:
            requests_made['successful'][str(order.id)] = []
            # requests_made['failed'][str(order.id)] = []

            for paymentline in order.statement_ids:
                if paymentline.t1cp_receipt_no:
                    paymentline.write({'api_to_be_cancelled': 1})

                    if paymentline.api_to_be_cancelled and not paymentline.api_cancel_success:
                        # import pdb; pdb.set_trace()
                        api_name = 'T1CCnclRedeemSrv'
                        t1cp_receipt_no = str(paymentline.t1cp_receipt_no)

                        #time and header
                        moment = datetime.now()
                        header = call_api.t1c_create_header(order, "0", moment)
                        business_date = moment.strftime("%d%m%Y")

                        #t1c information
                        the_1_card_config = call_api.get_the_one_card_api()
                        t1c_url = the_1_card_config[api_name]['url']
                        t1c_method = the_1_card_config[api_name]['method']

                        #order information
                        branch = str(order.branch_id.branch_code)
                        receipt_no = str(order.inv_no)
                        pos_no = str(order.session_id.config_id.pos_no)
                        store_no = "SOFC" + str(branch)

                        #member information
                        membercard = ast.literal_eval(order.membercard)
                        phone_no = str(membercard['phone'].replace('N/A', '')) or ''
                        card_no = str(membercard['the_one_card_no'].replace('N/A', '')) or ''
                        national_id = ''
                        phone_no = '' if card_no else phone_no

                        # transactions to cancel
                        # import pdb; pdb.set_trace()
                        transactions = json.loads(paymentline.transactions)
                        if type(transactions) is not list:
                            transactions = json.loads(transactions)
                        product_items = []
                        # import pdb; pdb.set_trace()
                        for transaction in transactions:
                            product_items.append({
                                "productName" : str(transaction['productName']),
                                "transactionNo" : str(transaction['transactionNo'])
                            })

                        #create body
                        body = {
                            "phoneNo": phone_no, #phone_no will be an empty string if card_no is set
                            "cardNo": card_no,
                            "nationalID": national_id, #national_id will be an empty string
                            "businessDate": business_date,
                            "productItems": product_items,
                            "receiptNo": receipt_no,
                            "posNo": pos_no,
                            "storeNo": store_no,
                            "siebelRedeemReceiptNo": t1cp_receipt_no,
                        }

                        response = call_api.t1c_request_api(api_name, header, body)

                        if response:
                            # import pdb; pdb.set_trace()
                            response_content_object = json.loads(response.content)
                            if str(response_content_object['integrationStatusCode']) == "0":
                                requests_made['successful'][str(order.id)].append(response_content_object)
                                paymentline.write({'api_cancel_success': 1})
                            else:
                                requests_made['failed'].append(receipt_no)
                                paymentline.write({'api_cancel_success': 0})
                        else:
                            requests_made['failed'].append(receipt_no)
                            paymentline.write({'api_cancel_success': 0})
     
        return json.dumps(requests_made)

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    discount_amount = fields.Float(
        store=True
    )
    price_subtotal = fields.Float(
        store=True
    )
    price_subtotal_incl = fields.Float(
        store=True
    )
    price_subtotal_wo_discount = fields.Float(
        store=True
    )
    price_subtotal_wo_discount_incl = fields.Float(
        store=True
    )

# class PosTheOneCard(models.Model):
