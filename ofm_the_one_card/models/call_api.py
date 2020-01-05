#-*- coding: utf-8 -*-

import logging
import requests
import json
import psycopg2
from pytz import timezone

from datetime import datetime
from odoo.tools.translate import *
from odoo.tools.osutil import walksymlinks
from odoo import SUPERUSER_ID
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, except_orm

_logger = logging.getLogger(__name__)
_pr_model = 'pos.order'
_api_method_delete = 'delete'
_api_method_post = 'post'

tools.config['T1C_client_id'] = tools.config.get(
    't1c_client_id',
    #'c49c1f4f42274ea192cfacff96612e91'
)
tools.config['T1C_client_secret'] = tools.config.get(
    't1c_client_secret',
    #'18fA76eA38e64d00a4Ac11773f1E2e07'
)
tools.config['T1C_partnerCode'] = tools.config.get(
    't1c_partner_code',
    #'OFM'
)
tools.config['T1C_transactionChannel'] = tools.config.get(
    't1c_transaction_channel',
    #'005'
)
tools.config['T1CQryMemInSrv'] = tools.config.get(
    't1c_qry_mem_srv',
    #'https://uat-api.central.co.th/t1c/member/info/qry/1_0'
)
tools.config['T1CVfyMemSrv'] = tools.config.get(
    't1c_vfy_mem_srv',
    #'https://uat-api.central.co.th/t1c/verification/member/1_0'
)
tools.config['BSReqOTPSrv'] = tools.config.get(
    'bs_req_otp_srv',
    #'https://uat-api.central.co.th/bs/otp/3_0/generate'
)
tools.config['BSVfyOTPSrv'] = tools.config.get(
    'bs_vfy_otp_srv',
    #'https://uat-api.central.co.th/bs/otp/3_0/verify'
)
tools.config['T1CRedeemTenderSrv'] = tools.config.get(
    't1c_redeem_tender_srv',
    #'https://uat-api.central.co.th/t1c/point/redemption/1_0/tender'
)
tools.config['T1CCnclRedeemSrv'] = tools.config.get(
    't1c_cncl_redeem_srv',
    #'https://uat-api.central.co.th/t1c/point/redemption/1_0/cancel'
)

tools.config['T1C_api_method'] = {
    'T1CQryMemInSrv': 'POST',
    'T1CVfyMemSrv': 'POST',
    'BSReqOTPSrv': 'POST',
    'BSVfyOTPSrv': 'POST',
    'T1CRedeemTenderSrv': 'POST',
    'T1CCnclRedeemSrv': 'DELETE',
}

tools.config['t1c_config_file'] = {
    'client_id': 'T1C_client_id',
    'client_secret': 'T1C_client_secret',
    'partnerCode': 'T1C_partnerCode',
    'transactionChannel': 'T1C_transactionChannel',
    'T1CQryMemInSrv': 'T1CQryMemInSrv',
    'T1CVfyMemSrv': 'T1CVfyMemSrv',
    'BSReqOTPSrv': 'BSReqOTPSrv',
    'BSVfyOTPSrv': 'BSVfyOTPSrv',
    'T1CRedeemTenderSrv': 'T1CRedeemTenderSrv',
    'T1CCnclRedeemSrv': 'T1CCnclRedeemSrv'
}


class TRCallAPI(models.Model):
    _inherit = 'tr.call.api'

    def get_time_milliseconds(self, time):
        milliseconds = time.microsecond / 1000
        milliseconds = round(milliseconds)
        return str(int(milliseconds))

    def get_formatted_time(self, time):
        milliseconds = self.get_time_milliseconds(time)
        formatted_time = time.strftime("%d%m%Y_%H:%M:%S:")
        formatted_time += milliseconds
        return formatted_time

    def create_trans_id(self, **kwargs):
        order = kwargs['order']
        formatted_time = kwargs['formatted_time']
        branch_code = str(order.branch_id.branch_code)
        invoice_no = str(order.inv_no)
        zp_request_the_one_card = self.zero_pad(kwargs['request_t1c'], 3) # todo: get the real value

        return '_'.join(['OFM', branch_code, invoice_no, zp_request_the_one_card, formatted_time])

    def zero_pad(self, num, size):
        s = "" + str(num)
        while len(s) < size:
            s = "0" + s
        return s

    @api.model
    def get_the_one_card_api(self):
        header_key = ['client_id', 'client_secret', 'partnerCode', 'transactionChannel']
        api_service_key = [
            'T1CQryMemInSrv', 'T1CVfyMemSrv', 'BSReqOTPSrv',
            'BSVfyOTPSrv', 'T1CRedeemTenderSrv', 'T1CCnclRedeemSrv'
        ]
        result_dict = {}
        for key in header_key:
            result_dict[key] = tools.config[tools.config['t1c_config_file'][key]]
        for key in api_service_key:
            result_dict[key] = {
                "url": tools.config[tools.config['t1c_config_file'][key]],
                "method": tools.config['T1C_api_method'][tools.config['t1c_config_file'][key]]
            }
        return result_dict

    def t1c_create_header(self, order, request_t1c, request_time):
        formatted_time = self.get_formatted_time(request_time)
        source_trans_id = self.create_trans_id(
            formatted_time=formatted_time, 
            order=order, 
            request_t1c=request_t1c)
        # import pdb; pdb.set_trace()
        ir_config_paramater = self.env['ir.config_parameter']
        the_1_config = self.get_the_one_card_api()
        client_id = the_1_config['client_id']
        client_secret = the_1_config['client_secret']
        partner_code = the_1_config['partnerCode']
        transaction_channel = the_1_config['transactionChannel']

        return {
            'SourceTransID': source_trans_id,
            'RequestTime': formatted_time,
            'LanguagePreference': 'TH',
            'client_id': client_id,
            'client_secret': client_secret,
            'PartnerCode': partner_code,
            'TransactionChannel': transaction_channel,
            'Content-Type': 'application/json',
        }

    def t1c_request_api(self, api_name, api_req_header, api_req_data):

        api_url = tools.config[api_name]

        api_method = tools.config['T1C_api_method'][api_name]
        
        if api_method == 'DELETE':
            request_response = requests.delete(api_url, data=json.dumps(api_req_data), headers=api_req_header)
        elif api_method == 'POST':
            request_response = requests.post(api_url, data=json.dumps(api_req_data), headers=api_req_header)
        else:
            return False

        self.create_log_call_api(api_method, api_name, api_url, api_req_header, api_req_data, request_response.content)

        if not ((200 <= request_response.status_code < 300) and request_response.content):
            msg_error = str(request_response.status_code)
            msg_error += ': ' + str(request_response.reason)
            msg_error += '\n\n' + str(request_response.content)
            
            self.create_log_call_api(api_method, api_name, api_url, api_req_header, api_req_data, msg_error)

        return request_response
