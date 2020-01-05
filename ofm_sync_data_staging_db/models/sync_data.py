# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
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
from datetime import datetime
import requests
from odoo import models, tools, _
from odoo.exceptions import ValidationError, except_orm

_logger = logging.getLogger(__name__)

tools.config['ofm_host'] = tools.config.get(
    'ofm_host',
    'dbstaging.cx5xb1tlygzz.ap-southeast-1.rds.amazonaws.com'
)
tools.config['ofm_db_user'] = tools.config.get(
    'ofm_db_user',
    'adminstg'
)
tools.config['ofm_db_pass'] = tools.config.get(
    'ofm_db_pass',
    'Od00stg!!'
)
tools.config['ofm_db_name'] = tools.config.get(
    'ofm_db_name',
    'dbstaging_uat'
)
tools.config['ofm_db_port'] = tools.config.get(
    'ofm_db_port',
    '5432'
)
tools.config['is_update_interface_control'] = tools.config.get(
    'is_update_interface_control',
    False
)
# Methods to export the translation file

class OFMSyncData(models.Model):
    _name = "ofm.sync.data"
    _description = "Sync Data From Url"

    def query_data_from_db_staging_ofm(self, cur, query_str):
        try:
            cur.execute(query_str)
            rows = cur.fetchall()
            _logger.debug("Query database successfully")
        except ValidationError, e:
            raise e
        except Exception, e:
            raise ValidationError("%s\n\n%s" % (_("Error while Query database"), tools.ustr(e)))
        return rows

    def query_data_from_db_staging_ofm_to_dict(self, cur, query_str):
        try:
            cur.execute(query_str)
            result = cur.fetchall()
            rows = [dict(record) for record in result]
            _logger.debug("Query database successfully")
        except ValidationError, e:
            raise e
        except Exception, e:
            raise ValidationError("%s\n\n%s" % (_("Error while Query database"), tools.ustr(e)))
        return rows

    def query_update_data_to_db_staging_ofm(self, conn, cur, query_str):
        try:
            cur.execute(query_str)
            conn.commit()
            cur.close()
            _logger.debug("Query database successfully")
        except ValidationError, e:
            raise e
        except Exception, e:
            raise ValidationError("%s\n\n%s" % (_("Error while Query database"), tools.ustr(e)))

    def connect_to_db_staging_ofm(self, conn):
        try:
            cur = conn.cursor()
            _logger.debug("Opened database successfully")
        except ValidationError, e:
            raise e
        except Exception, e:
            raise ValidationError("%s\n\n%s" % (_("Error while Opened database"), tools.ustr(e)))
        return cur

    def connect_to_db_staging_ofm_to_dict(self, conn):
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            _logger.debug("Opened database successfully")
        except ValidationError, e:
            raise e
        except Exception, e:
            raise ValidationError("%s\n\n%s" % (_("Error while Opened database"), tools.ustr(e)))
        return cur

    def open_connection(self):

        host = tools.config['ofm_host']
        db_user = tools.config['ofm_db_user']
        db_pass = tools.config['ofm_db_pass']
        db_name = tools.config['ofm_db_name']
        db_port = tools.config['ofm_db_port']

        conn = psycopg2.connect(
            database=db_name
            , user=db_user
            , password=db_pass
            , host=host
            , port=db_port
        )

        return conn

    def close_connection(self, conn):
        conn.close()

    def get_invoice_from_staging_header(self, purchase_order_id, document_type):
        conn = self.open_connection()

        cur = self.connect_to_db_staging_ofm(conn)

        if purchase_order_id.state == 'purchase':
            prno = purchase_order_id.purchase_request_no
        else:
            prno = purchase_order_id.name

        if purchase_order_id.type_to_ofm == 'store':
            type_to_ofm = 'manual'
        elif purchase_order_id.type_to_ofm == 'fulfillment':
            type_to_ofm = 'suggest'
        else:
            type_to_ofm = purchase_order_id.type_to_ofm

        prchannel = "and prchannel = '{0}'".format(type_to_ofm)

        query_str = """
            select prno, 
                storecode, 
                invno, 
                invdate, 
                invtime, 
                sono, 
                paymentcode, 
                ptrmday, 
                vatamt,
                vat,
                dlidate,
                dliamt,
                vatprodnetamt,
                deliverfee,
                paymenttype,
                paymentname,
                transferdate,
                supdlifeeitem,
                supdlifeeorder,
                batch_id,
                prchannel,
                documenttype
            from tbfranchiseinvoicehead
            where prno = '{0}'
                and documenttype = '{1}'
                {2}
        """.format(
            prno,
            document_type,
            prchannel
        )

        if all([
            purchase_order_id,
            document_type == 'Return'
        ]):
            amount_vendor_cn_reference = 0
            if purchase_order_id.invoice_ids:
                cn_no = ' and invno not in ('
                for invoice_id in purchase_order_id.invoice_ids:
                    if invoice_id.vendor_cn_reference:
                        amount_vendor_cn_reference += 1
                        cn_no += '\'' + invoice_id.vendor_cn_reference + '\','

                cn_no = cn_no[:len(cn_no)-1]
                cn_no += ')'

            if amount_vendor_cn_reference > 0:
                query_str += cn_no

        inv_header = self.query_data_from_db_staging_ofm(cur, query_str)
        inv_header_update = {}

        for header in inv_header:
            invdate = datetime.strptime(header[3], '%Y-%m-%d %H:%M:%S').date()
            invtime = datetime.strptime(header[4], '%H:%M:%S').time()

            inv_header_update = {
                'vendor_invoice_no': header[2],
                'vendor_invoice_date': datetime.combine(invdate, invtime),
                'dliamt_ofm': header[11],
                'dlidate_ofm': header[10],
                'deliverfee_ofm': header[13],
                'supdlifeeitem_ofm': header[17],
                'supdlifeeorder_ofm': header[18]
            }

        self.close_connection(conn)

        return inv_header_update

    def get_invoice_from_staging_detail(self, purchase_order_id, vendor_invoice_no):
        conn = self.open_connection()

        cur = self.connect_to_db_staging_ofm(conn)

        query_str = """
            select invno, 
                seqno, 
                pid, 
                productname, 
                qty, 
                unitprice, 
                discountrate, 
                discamt, 
                saleunit,
                createby, 
                createon, 
                updateby, 
                updateon, 
                bestdealflag, 
                isvat, 
                deliverfee,
                suppilerdeliverfee,
                batch_id
            from tbfranchiseinvoicedetl
            where invno = '{0}'
        """.format(vendor_invoice_no)

        inv_detail = self.query_data_from_db_staging_ofm(cur, query_str)
        inv_detail_update = []

        for detail in inv_detail:
            product_ids = self.env['product.product'].search([
                ('default_code', '=', detail[2]),
                ('active', '=', True)
            ])

            for product_id in product_ids:
                ofm_order_line_id = purchase_order_id.ofm_purchase_order_line_ids.filtered(
                    lambda line_rec: line_rec.product_id.id == product_id.id
                )

                taxes_id = []
                for taxes in ofm_order_line_id.taxes_id:
                    taxes_id.append(
                        taxes.id
                    )

                taxes = [
                    [
                        6,
                        False,
                        taxes_id
                    ]
                ]

                inv_detail_update.append(
                    [
                        0,
                        False,
                        {
                            'account_analytic_id': ofm_order_line_id.account_analytic_id.id,
                            'date_planned': ofm_order_line_id.date_planned,
                            'name': product_id.product_tmpl_id.name,
                            'price_unit': detail[5],
                            'product_id': product_id.id,
                            'product_qty': detail[4],
                            'product_uom': product_id.product_tmpl_id.uom_id.id,
                            'state': purchase_order_id.state,
                            'order_id': purchase_order_id.id,
                            'taxes_id': taxes,
                        }
                    ]
                )

        self.close_connection(conn)

        return inv_detail_update

    def get_invoice_from_staging(self, purchase_order_id, document_type):
        log_inv_header_datetime = datetime.now()
        inv_header = self.get_invoice_from_staging_header(purchase_order_id, document_type)

        log_inv_detail_datetime = datetime.now()
        if inv_header.get('vendor_invoice_no', False):
            inv_detail = self.get_invoice_from_staging_detail(purchase_order_id, inv_header.get('vendor_invoice_no'))
        else:
            inv_detail = {}

        _logger.info("""
            Document Type: %s
            Purchase Order ID: %s
            Invoice/CN Header Get Datetime: %s
            Invoice/CN Header Get Data: %s
            Invoice/CN Detail Get Datetime: %s
            Invoice/CN Detail Get Data: %s
            """ % (
                document_type,
                purchase_order_id,
                log_inv_header_datetime,
                inv_header,
                log_inv_detail_datetime,
                inv_detail,
            )
        )

        if all([
            document_type == 'Invoice',
            all([
                len(inv_header) > 0,
                len(inv_detail) > 0,
            ]),
        ]):
            inv_header.update(
                {
                    'order_line': inv_detail
                }
            )

        return {
            'inv_header': inv_header,
            'inv_detail': inv_detail,
        }

    def get_date_interface(self):
        tr_convert = self.env['tr.convert']
        date_now = datetime.now(timezone('UTC'))
        date_now = tr_convert.convert_datetime_to_bangkok(date_now).strftime('%Y-%m-%d %H:%M:%S')

        return date_now

    def update_interface_control_db_staging_ofm(self, db_name, odoo_record_amount, odoo_start_date):
        if tools.config['is_update_interface_control']:
            odoo_record_amount = str(odoo_record_amount)
            date_now = self.get_date_interface()
            odoo_end_date = date_now
            date_now_bkk = date_now[:10] + ' ' + '00:00:00'

            conn = self.open_connection()
            cur = self.connect_to_db_staging_ofm(conn)

            query_get_data_params = (
                db_name,
                date_now_bkk,
                date_now_bkk,
            )

            query_get_data = """
                SELECT batch_id,
                    source_name,
                    ofm_startdate,
                    ofm_enddate,
                    ofm_recordamout,
                    coalesce(odoo_startdate, '1900-01-01 00:00:00') as odoo_startdate,
                    coalesce(odoo_recordamount, 0) as odoo_recordamount
                FROM tbinterface_control 
                WHERE source_name = '%s' and 
                    ofm_startdate::date = '%s'::date and 
                    ofm_enddate::date = '%s'::date
            """ % query_get_data_params

            tbinterface_control = self.query_data_from_db_staging_ofm(cur, query_get_data)
            query_str = False

            if len(tbinterface_control) > 0:
                if tbinterface_control[0][5] == '1900-01-01 00:00:00':
                    batch_id = str(tbinterface_control[0][0])

                    update_params = (
                        odoo_start_date,
                        odoo_end_date,
                        odoo_record_amount,
                        batch_id,
                        db_name,
                    )

                    query_str = """
                        UPDATE tbinterface_control  
                        SET odoo_startdate = '%s', 
                             odoo_enddate = '%s', 
                             odoo_recordamount = '%s' 
                        WHERE batch_id = '%s' and 
                            source_name = '%s'
                        RETURNING batch_id, source_name
                    """ % update_params
            else:
                last_batach_params = (
                    db_name,
                )

                query_last_batch_id = """
                    SELECT coalesce(max(batch_id), 0) as last_batch_id 
                    FROM tbinterface_control 
                    WHERE source_name = '%s'
                """ % last_batach_params

                last_batch_id = self.query_data_from_db_staging_ofm(cur, query_last_batch_id)

                if len(last_batch_id) > 0:
                    last_batch_id = str(int(last_batch_id[0][0]) + 1)

                params = (
                    last_batch_id,
                    db_name,
                    odoo_start_date,
                    odoo_end_date,
                    odoo_record_amount,
                )

                query_str = """
                    INSERT INTO tbinterface_control 
                        (batch_id, source_name, ofm_startdate, ofm_enddate, odoo_startdate, odoo_enddate, odoo_recordamount) 
                    VALUES
                        ('%s','%s', '1900-01-01 00:00:00', '1900-01-01 00:00:00', '%s', '%s', '%s')
                    RETURNING batch_id, source_name
                """ % params

            if query_str:
                self.query_update_data_to_db_staging_ofm(conn, cur, query_str)

            self.close_connection(conn)
