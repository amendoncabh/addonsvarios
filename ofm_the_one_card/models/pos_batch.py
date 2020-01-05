# -*- coding: tis-620 -*-

from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta
import os
import codecs
from pytz import timezone

# Global parameter
delimited_symbol = '|'
DELIMITED_SYMBOL = '|'
TRANSACTION_LINE_LIMIT = 100000
DAT_FILE_TITLE = 'BCH_OFMFCH_T1C_NRTSales'
PARTNER_CODE = 'OFMFCH'
BRANCH_CODE = 'SOFC'
TRANS_CHANNEL = '005'


class PosOrder(models.Model):
    _inherit = 'pos.order'

    batch_done = fields.Boolean(
        string='Batch Done',
        default=False,
    )


class PosBatch(models.TransientModel):
    _name = 'pos.batch'

    def _set_default_na(self, val):
        if val == 'N/A':
            val = ''
        return val

    @api.multi
    def batch_file_generate(self):
        # Rearrange order_date in proper format to set a filter
        # To set date filter as a range of time on selected date
        orders = self.env['pos.order'].search([
            ('state', '!=', 'draft'),
            ('batch_done', '=', False),
        ], order='id')

        # Parameter for use in loop
        # dat_file_count use for count for a batch file to summarise on .ctrl file
        dat_file_count = 1
        # rec_count use for count all record in selected date to summarise on .ctrl file
        rec_count = 0
        # total_rec use for count record for current order and will reset when end of order
        total_rec = 0
        # record_set use for flag to call function and store total_rec properly ('P' -> 'T' -> 'A')
        record_set = False
        # continue_new_file use for check if line of file is greater than TRANSACTION_LINE_LIMIT
        # continue_new_file will tell dat_file_count to count up and change file sequence (.XXXX)
        continue_new_file = False
        # transaction_line_count use for count transaction line of current batch file
        # it will stamp on the header
        transaction_line_count = 0
        # data_not_exist flag use for trigger function when there is no data on selected date
        # batch file will created with no transaction line
        data_not_exist = False

        now = datetime.now(timezone('Asia/Bangkok'))

        if orders:
            for order in orders:

                source_transid_seq = 0

                # Count total line for this order
                # To check transaction line must not greater than TRANSACTION_LINE_LIMIT
                # +1 is stand for amount total for this order
                total_line_this_file = len(order.lines) + len(order.statement_ids) + 1

                # If order have a change_rounding then add 1 more line
                if order.change_rounding:
                    total_line_this_file += 1

                # If transaction is greater than TRANSACTION_LINE_LIMIT
                # dat file will count up a file extension (.0001, .0002 ... .XXXX) by increase dat_file_count
                if (transaction_line_count + total_line_this_file) > TRANSACTION_LINE_LIMIT:
                    dat_file_count += 1
                    # continue_new_file flag to set a header and footer for current dat file
                    continue_new_file = True

                # If continue_new_file happened
                # Then add a header and footer to current file and reset line count for new file
                if continue_new_file:
                    self.batch_file_header(dat_file_full_path, transaction_line_count)
                    self.batch_file_footer(dat_file_full_path)
                    transaction_line_count = 0
                    continue_new_file = False

                # To set dat_file_count by prepend zero if its no value (Format: XXXX)
                dat_sequence = "%04d" % dat_file_count
                dat_file_name =  DAT_FILE_TITLE + '_' + \
                                 now.strftime('%d%m%Y') + '_' + \
                                 now.strftime('%H%M%S') + '.dat' + '.' + dat_sequence

                # Get batch_path from .cfg file 'batch_file_path' parameter to define
                batch_path = tools.config['batch_file_path']

                # Check file path is exists ? if not then create a new one
                if not os.path.exists(batch_path):
                    os.makedirs(batch_path)

                # Get a file full path, use for send as a parameter to insert value into specific file
                dat_file_full_path = batch_path + '/' + dat_file_name

                batch_file = codecs.open(dat_file_full_path, 'a+', encoding='tis-620')

                # START - Product : TransSubType = 'P' ------------------- Sales product
                item_seq = 0
                # To collect discount & vat by line
                discount_grand_total = 0
                vat_grand_total = 0
                for line in order.lines.sorted(key=lambda r: r.original_line_id):
                    if not line.promotion_name or line.promotion_name == '':
                        item_seq, source_transid_seq, discount_grand_total, vat_grand_total = self.batch_add_sales_product(
                            batch_file,
                            order,
                            line,
                            item_seq,
                            source_transid_seq,
                            discount_grand_total,
                            vat_grand_total
                        )
                        record_set = True
                if record_set:
                    total_rec += item_seq
                    record_set = False
                # END - Product : TransSubType = 'P'

                # START - Tender line : TransSubtype = 'T' ------------------- Tender
                item_seq = 0
                return_amount = 0
                for statement in order.statement_ids.sorted(key=lambda r: r.id, reverse=True):
                    if 'return' in statement.name:
                        return_amount += statement.amount
                    else:
                        item_seq, source_transid_seq = self.batch_add_tender(batch_file, order, statement, item_seq, return_amount, source_transid_seq)
                    record_set = True
                if order.change_rounding > 0:
                    item_seq, source_transid_seq = self.batch_add_tender(
                        batch_file,
                        order,
                        statement,
                        item_seq,
                        return_amount,
                        source_transid_seq,
                        True
                    )
                if record_set:
                    total_rec += item_seq
                    record_set = False
                # END - Tender line : TransSubtype = 'T'

                # START - Amount line : TransSubtype = 'A' ------------------- Amount
                item_seq = 0
                item_seq, source_transid_seq = self.batch_add_amount(
                    batch_file,
                    order,
                    item_seq,
                    source_transid_seq,
                    discount_grand_total,
                    vat_grand_total
                )
                total_rec += item_seq
                # END - Amount line : TransSubtype = 'A'

                # total_rec use for count record for current order
                rec_count += total_rec
                # transaction_line_count user for record transaction in current batch file
                # if current batch file has a line greater than TRANSACTION_LINE_LIMIT
                transaction_line_count += total_rec
                # reset total_rec for next order
                total_rec = 0

                #*****************************************order.batch_done = True
        else:
            # To set dat_file_count by prepend zero if its no value (Format: XXXX)
            dat_sequence = "%04d" % dat_file_count
            dat_file_name = DAT_FILE_TITLE + '_' + \
                            now.strftime('%d%m%Y') + '_' + \
                            now.strftime('%H%M%S') + '.dat' + '.' + dat_sequence

            # Get batch_path from .cfg file 'batch_file_path' parameter to define
            batch_path = tools.config['batch_file_path']

            # Check file path is exists ? if not then create a new one
            if not os.path.exists(batch_path):
                os.makedirs(batch_path)

            # Get a file full path, use for send as a parameter to insert value into specific file
            dat_file_full_path = batch_path + '/' + dat_file_name

            batch_file = codecs.open(dat_file_full_path, 'w+', encoding='tis-620')

            # Write once to let file usable for next line
            batch_file.write('')
            self.batch_file_header(dat_file_full_path, total_rec)
            self.batch_file_footer(dat_file_full_path)
            data_not_exist = True

        if not continue_new_file and not data_not_exist:
            if rec_count < TRANSACTION_LINE_LIMIT:
                self.batch_file_header(dat_file_full_path, rec_count)
                self.batch_file_footer(dat_file_full_path)
            else:
                self.batch_file_header(dat_file_full_path, transaction_line_count)
                self.batch_file_footer(dat_file_full_path)
        self.batch_file_ctrl(dat_file_count, rec_count, batch_path, now)


    @api.model
    def batch_file_footer(self, dat_file_full_path):

        batch_file = open(dat_file_full_path, 'a')
        # End of file
        batch_file.write(
            '9' +
            DELIMITED_SYMBOL +
            'END'
        )
        batch_file.close()


    @api.model
    def batch_file_header(self, dat_file_full_path, total_rec):

        # Read everything in the file
        batch_file = open(dat_file_full_path, 'r+')
        old = batch_file.read()
        # Set cursor at the start point of file
        batch_file.seek(0)

        # '0'|{total_rec} -> '0' is default for first line header
        header_data = '0' + DELIMITED_SYMBOL + str(total_rec)
        # TotalRec
        batch_file.write(
            header_data +
            '\n' +
            old
        )


    @api.model
    def batch_file_ctrl(self, dat_file_count, rec_count, batch_path, datetime_now):

        # +7 datetime for localize
        now = datetime_now

        # Generate ctrl file
        ctrl_file_name = DAT_FILE_TITLE + '_' + now.strftime('%d%m%Y') + '_' + now.strftime('%H%M%S') + '.ctrl'
        ctrl_file = codecs.open(batch_path + '/' + ctrl_file_name, 'w+', encoding='tis-620')
        partner_code = 'OFM'
        requester = 'OFM-FCH'

        # File Title
        batch_data = DAT_FILE_TITLE + DELIMITED_SYMBOL
        # PartnerCode
        batch_data += partner_code + DELIMITED_SYMBOL
        # TransChannel
        batch_data += TRANS_CHANNEL + DELIMITED_SYMBOL
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


    # @api.model
    # def batch_add_coupon(self, batch_file, order, line, item_seq):
    #
    #     now = datetime.now()
    #
    #     item_seq += 1
    #     source_transid_seq += 1
    #     # now = datetime.now()
    #     # split order.date_order for rearrangement
    #     do_datetime = order.date_order.split(' ')
    #     do_fulldate = do_datetime[0]
    #     do_fulltime = do_datetime[1]
    #
    #     do_splitdate = do_fulldate.split('-')
    #     do_year = do_splitdate[0]
    #     do_month = do_splitdate[1]
    #     do_date = do_splitdate[2]
    #
    #     do_splittime = do_fulltime.split(':')
    #     do_hour = do_splittime[0]
    #     do_minute = do_splittime[1]
    #     do_second = do_splittime[2]
    #
    #     # LNIdentifier
    #     batch_file.write(
    #         '1' +
    #         delimited_symbol
    #     )
    #     # SourceTransID
    #     source_trans_id_millisec =  "%03d" % (int(now.strftime('%f')) / 1000)
    #     batch_file.write(
    #         'OFM_' +
    #         order.session_id.config_id.branch_id.branch_code +
    #         '_' +
    #         order.inv_no +
    #         '_' + str(item_seq) +
    #         '_' +
    #         now.strftime('%d%m%Y') +
    #         '_' +
    #         now.strftime('%H:%M:%S') +
    #         ':' + str(source_trans_id_millisec) +
    #         delimited_symbol
    #     )
    #     # StoreNo
    #     batch_file.write(
    #         'SOFC' +
    #         order.session_id.config_id.branch_id.branch_code +
    #         delimited_symbol
    #     )
    #     # POSNo
    #     batch_file.write(
    #         order.session_id.config_id.pos_no +
    #         delimited_symbol
    #     )
    #     # ReceiptNo
    #     receipt_datetime = order.date_order
    #     receipt_datetime = receipt_datetime.split()
    #     receipt_date = receipt_datetime[0].replace('-', '')
    #     receipt_time = receipt_datetime[1].replace(':', '')[0:4]
    #     batch_file.write(
    #         order.session_id.config_id.branch_id.branch_id +
    #         order.session_id.config_id.pos_no +
    #         order.inv_no +
    #         receipt_date +
    #         receipt_time +
    #         delimited_symbol
    #     )
    #     # TransType
    #     trans_type = ''
    #     if order.is_return_order == True:
    #         trans_type = '07'
    #     elif order.is_void_order == True:
    #         trans_type = '09'
    #     else:
    #         trans_type = '01'
    #     batch_file.write(
    #         trans_type +
    #         delimited_symbol
    #     )
    #     # TransSubtype
    #     batch_file.write(
    #         'C' +
    #         delimited_symbol
    #     )
    #     # TransDate
    #     trans_date = do_date + do_month + do_year + '_' + do_fulltime + ':000'
    #     batch_file.write(
    #         trans_date +
    #         delimited_symbol
    #     )
    #     # BusinessDate
    #     business_date = do_date + do_month + do_year
    #     batch_file.write(
    #         business_date +
    #         delimited_symbol
    #     )
    #     # InvoiceDate (For online/Call center Only) - Leave blank
    #     batch_file.write(
    #         delimited_symbol
    #     )
    #     # DeliveryDate (For online/Call center Only) - Leave blank
    #     batch_file.write(
    #         delimited_symbol
    #     )
    #     # EarnOnlineFlag
    #     batch_file.write(
    #         'N' +
    #         delimited_symbol
    #     )
    #     # T1CCardNo
    #     batch_file.write(
    #         (order.the_one_card_no or '') +
    #         delimited_symbol
    #     )
    #     # MobileNo
    #     batch_file.write(
    #         (order.phone_number or '') +
    #         delimited_symbol
    #     )
    #     # UserID
    #     batch_file.write(
    #         # str(order.user_id.id) +
    #         delimited_symbol
    #     )
    #
    #     # LineIDS
    #     # ItemSeqNo
    #     batch_file.write(
    #         str(item_seq) +
    #         delimited_symbol
    #     )
    #     # ProductCode
    #     batch_file.write(
    #         (str(line.product_id.product_tmpl_id.sku_ofm) or '') +
    #         delimited_symbol
    #     )
    #     # ProductBarcode
    #     batch_file.write(
    #         (line.product_id.barcode or '') +
    #         delimited_symbol
    #     )
    #     # Quantity
    #     batch_file.write(
    #         str(line.qty) +
    #         delimited_symbol
    #     )
    #     # PriceUnit
    #     batch_file.write(
    #         str(line.price_unit) +
    #         delimited_symbol
    #     )
    #     # PriceTotal
    #     batch_file.write(
    #         str(line.price_subtotal_wo_discount_incl) +
    #         delimited_symbol
    #     )
    #     # NetPriceUnit
    #     net_price_unit = line.price_unit - line.discount_amount
    #     batch_file.write(
    #         str(net_price_unit) +
    #         delimited_symbol
    #     )
    #     # NetPriceTotal
    #     batch_file.write(
    #         str(line.price_subtotal_incl) +
    #         delimited_symbol
    #     )
    #     # DiscountTotal
    #     batch_file.write(
    #         str(line.discount_amount) +
    #         delimited_symbol
    #     )
    #     # VatAmount
    #     # tax_percent_amount = 0
    #     # for tax in line.tax_ids:
    #     #     tax_percent_amount += tax.amount
    #     # price_before_vat = line.price_unit - ((line.price_unit*100)/107)
    #     # vat_amount = price_before_vat * (tax_percent_amount/100)
    #     vat_amount = (line.price_subtotal_incl - line.price_subtotal) / line.qty
    #     vat_amount = round(vat_amount, 4)
    #     # "%0.4f" format for padding 0 to denumerator
    #     vat_amount = "%0.4f" % vat_amount
    #     batch_file.write(
    #         str(vat_amount) +
    #         delimited_symbol
    #     )
    #     # TenderType ****
    #     batch_file.write(
    #         delimited_symbol
    #     )
    #     # TenderRefNo ****
    #     batch_file.write(
    #         delimited_symbol
    #     )
    #     # OriginalReceiptNo
    #     original_receipt_no = ''
    #     if order.is_return_order == True or order.is_void_order == True:
    #         original_receipt_no = order.return_order_id.inv_no
    #         receipt_datetime = order.return_order_id.date_order
    #         receipt_datetime = receipt_datetime.split()
    #         receipt_date = receipt_datetime[0].replace('-', '')
    #         receipt_time = receipt_datetime[1].replace(':', '')[0:4]
    #         batch_file.write(
    #             order.return_order_id.session_id.config_id.branch_id.branch_id +
    #             order.return_order_id.session_id.config_id.pos_no +
    #             original_receipt_no +
    #             receipt_date +
    #             receipt_time +
    #             delimited_symbol
    #         )
    #     else:
    #         batch_file.write(
    #             delimited_symbol
    #         )
    #     # OriginalItemSequenceNo ****
    #     batch_file.write(
    #         str(item_seq) +
    #         delimited_symbol
    #     )
    #     # DisplayReceiptNo
    #     batch_file.write(
    #         order.inv_no +
    #         delimited_symbol
    #     )
    #     # ReturnAllFlag
    #     return_all_flag = ''
    #     if order.return_status == 'Fully-Returned':
    #         return_all_flag = 'Y'
    #     elif order.return_status == 'Partially-Returned':
    #         return_all_flag = 'N'
    #     batch_file.write(
    #         return_all_flag +
    #         delimited_symbol
    #     )
    #     # SBLCnclRedeemTxnID ****
    #     # batch_file.write(
    #     #     delimited_symbol
    #     # )
    #     # Last line of each item
    #     batch_file.write('\n')
    #
    #
    #     return item_seq, source_transid_seq


    @api.model
    def batch_add_sales_product(self, batch_file, order, line, item_seq, source_transid_seq, discount_grand_total, vat_grand_total):

        # +7 datetime for localize
        now = datetime.now(timezone('Asia/Bangkok'))
        now_millisec = "%03d" % (int(now.strftime('%f')) / 1000)
        tr_convert = self.env['tr.convert']

        source_transid_seq += 1
        item_seq += 1

        sql_query = '''
            SELECT 
            COALESCE(pb.branch_code, ''),
            COALESCE(po.inv_no, ''),
            COALESCE(pc.pos_no, ''),
            po.date_order,
            po.is_return_order,
            po.is_void_order,
            COALESCE(po.the_one_card_no, ''),
            COALESCE(po.phone_number, ''),
            COALESCE(pt.sku_ofm, ''),
            COALESCE(pp.barcode, ''),
            pol.prorate_amount,
            pol.promotion_id,
            pol.product_id,
            pol.qty,
            pol.price_unit,
            pol.price_subtotal_wo_discount_incl,
            pol.price_subtotal_incl,
            pol.price_subtotal
            FROM pos_order po
            LEFT JOIN pos_order_line pol
            ON po.id = pol.order_id
            LEFT JOIN pos_session ps
            ON ps.id = po.session_id
            LEFT JOIN pos_config pc
            ON pc.id = ps.config_id
            LEFT JOIN pos_branch pb
            ON pb.id = pc.branch_id
            LEFT JOIN product_product pp
            ON pp.id = pol.product_id
            LEFT JOIN product_template pt
            ON pt.id = pp.product_tmpl_id
            WHERE pol.id = 
            ''' + str(line.id)

        self._cr.execute(sql_query)

        row = self._cr.fetchone()
        # split order.date_order for rearrangement
        do_datetime = str(tr_convert.convert_datetime_to_bangkok(row[3]))
        do_datetime = do_datetime.split(' ')
        do_fulldate = do_datetime[0]
        do_fulltime = do_datetime[1]
        do_fulltime = do_fulltime[:8]

        do_splitdate = do_fulldate.split('-')
        do_year = do_splitdate[0]
        do_month = do_splitdate[1]
        do_date = do_splitdate[2]

        # LNIndentifier
        batch_data = '1' + DELIMITED_SYMBOL
        # SourceTransID
        transid_seq = "%03d" % source_transid_seq
        batch_data += PARTNER_CODE + '_' + \
                      BRANCH_CODE + row[0] + '_' + \
                      row[1] + '_' + \
                      str(transid_seq) + '_' + \
                      now.strftime('%d') + '_' + \
                      now.strftime('%H%M%S') + now_millisec + \
                      DELIMITED_SYMBOL
        # StoreNo
        batch_data += BRANCH_CODE + row[0] + DELIMITED_SYMBOL
        # POSNo
        batch_data += row[2] + DELIMITED_SYMBOL
        # ReceiptNo
        receipt_datetime = str(tr_convert.convert_datetime_to_bangkok(row[3]))
        receipt_datetime = receipt_datetime.split()
        receipt_date = receipt_datetime[0].replace('-', '')[6:8]
        receipt_time = receipt_datetime[1].replace(':', '')[0:4]
        batch_data += BRANCH_CODE + row[0] + \
                      row[1] + \
                      receipt_date + \
                      receipt_time + \
                      DELIMITED_SYMBOL
        # TransType
        trans_type = ''
        if row[4] == True:
            trans_type = '07'
        elif row[5] == True:
            trans_type = '09'
        else:
            trans_type = '01'
        batch_data += trans_type + DELIMITED_SYMBOL
        # TransSubType
        # For this function sales_product all of type always 'P'
        batch_data += 'P' + DELIMITED_SYMBOL
        # TransDate
        # Append by :000 for millisecond cause of 'order_date' was no millisec data stored
        batch_data += do_date + do_month + do_year + '_' + \
                      do_fulltime + ':000' + \
                      DELIMITED_SYMBOL
        # BusinessDate
        batch_data += do_date + do_month + do_year + \
                      DELIMITED_SYMBOL
        # InvoiceDate (For online/Call center Only) - Leave blank
        batch_data += DELIMITED_SYMBOL
        # DeliveryDate (For online/Call center Only) - Leave blank
        batch_data += DELIMITED_SYMBOL
        # EarnOnlineFlag
        # always 'N' for current phase
        batch_data += 'N' + DELIMITED_SYMBOL
        # T1CCardNo
        batch_data += self._set_default_na(row[6]) + DELIMITED_SYMBOL
        # MobileNo
        batch_data += self._set_default_na(row[7]) + DELIMITED_SYMBOL
        # UserID - leave blank
        batch_data += DELIMITED_SYMBOL
        # LineIDS
        batch_data += str(item_seq) + DELIMITED_SYMBOL
        # ProductCode
        batch_data += row[8] + DELIMITED_SYMBOL
        # ProductBarcode
        batch_data += row[9] + DELIMITED_SYMBOL

        # discount_amount Declare for calculate
        free_product = False
        discount_amount_wo_discount = int(row[10])
        if row[11]:
            posl = self.env['pos.order.line'].search([
                ('promotion_id', '=', row[11]),
                ('product_id', '!=', 4235),
                ('order_id', '=', order.id),
                ('promotion', '=', True),
            ])
            if posl.product_id.id == int(row[12]):
                discount_amount_wo_discount = abs(posl.price_subtotal_wo_discount_incl)
                discount_price_unit = abs(posl.price_unit)
                discount_subtotal_incl = abs(posl.price_subtotal_incl)
                free_product = True

            # pol.qty, 13
            # pol.price_unit, 14
            # pol.price_subtotal_wo_discount_incl, 15
            # pol.price_subtotal_incl, 16
            # pol.price_subtotal 17
        # Quantity
        batch_data += str(abs(float(row[13]))) + DELIMITED_SYMBOL
        # PriceUnit
        price_unit = round(abs(float(row[14])), 4)
        batch_data += str(price_unit) + DELIMITED_SYMBOL
        # PriceTotal
        price_total = round(abs(float(row[15])), 4)
        # if free_product:
        #     price_total -= discount_amount_wo_discount
        batch_data += str(abs(price_total)) + DELIMITED_SYMBOL
        # NetPriceUnit
        dc_price_unit = abs(float(row[10]))
        if free_product:
            dc_price_unit = discount_price_unit
        net_price_unit = float(row[14]) - dc_price_unit
        net_price_unit = round(abs(net_price_unit), 4)
        batch_data += str(abs(net_price_unit)) + DELIMITED_SYMBOL
        # NetPriceTotal
        net_price_total = abs(float(row[16]))
        if free_product:
            net_price_total -= discount_subtotal_incl
        net_price_total = round(abs(net_price_total), 4)
        batch_data += str(abs(net_price_total)) + DELIMITED_SYMBOL
        # DiscountTotal
        discount_total = abs(float(row[10]))
        if free_product:
            discount_total = discount_subtotal_incl
        discount_total = round(abs(discount_total), 4)
        discount_grand_total += abs(discount_total)
        batch_data += str(abs(discount_total)) + DELIMITED_SYMBOL
        # VatAmount
        vat_amount = (float(row[16]) - float(row[17]))
        if free_product:
            vat_amount = 0
        vat_grand_total += round(abs(vat_amount), 4)
        vat_amount_line = vat_amount / float(row[13])
        vat_amount_line = round(vat_amount_line, 4)
        # "%0.4f" format for padding 0 to denumerator
        vat_amount_line = "%0.4f" % abs(vat_amount_line)
        batch_data += str(vat_amount_line) + DELIMITED_SYMBOL
        # TenderType
        batch_data += DELIMITED_SYMBOL
        # TenderRefNo
        batch_data += DELIMITED_SYMBOL
        # OriginalReceiptNo
        if row[4] == True or row[5] == True:
            if order.return_order_id:
                sql_query = '''
                    SELECT 
                    po.inv_no,
                    po.date_order,
                    pb.branch_code
                    FROM pos_order po
                    LEFT JOIN pos_session ps
                    ON ps.id = po.session_id
                    LEFT JOIN pos_config pc
                    ON pc.id = ps.config_id
                    LEFT JOIN pos_branch pb
                    ON pb.id = pc.branch_id
                    WHERE po.id =
                ''' + str(order.return_order_id.id)
                self._cr.execute(sql_query)
                return_order_row = self._cr.fetchone()
                receipt_datetime = str(tr_convert.convert_datetime_to_bangkok(return_order_row[1]))
                receipt_datetime = receipt_datetime.split()
                receipt_date = receipt_datetime[0].replace('-', '')[6:8]
                receipt_time = receipt_datetime[1].replace(':', '')[0:4]
                batch_data += BRANCH_CODE + return_order_row[2] + \
                              return_order_row[0] + \
                              receipt_date + \
                              receipt_time
        batch_data += DELIMITED_SYMBOL
        # OriginalItemSequenceNo
        batch_data += str(item_seq) + DELIMITED_SYMBOL
        # DisplayReceiptNo
        batch_data += row[1] + DELIMITED_SYMBOL
        # ReturnAllFlag
        return_all_flag = ''
        if order.is_return_order:
            if abs(order.amount_total) == abs(order.return_order_id.amount_total):
                return_all_flag = 'Y'
            else:
                return_all_flag = 'N'
        batch_data += return_all_flag + DELIMITED_SYMBOL

        batch_file.write(batch_data + '\n')

        return item_seq, source_transid_seq, discount_grand_total, vat_grand_total


    @api.model
    def batch_add_tender(self, batch_file, order, statement, item_seq, return_amount, source_transid_seq, rounding=False):

        # +7 datetime for localize
        now = datetime.now(timezone('Asia/Bangkok'))
        now_millisec = "%03d" % (int(now.strftime('%f')) / 1000)
        tr_convert = self.env['tr.convert']

        source_transid_seq += 1
        item_seq += 1

        sql_query = '''
                    SELECT 
                    COALESCE(pb.branch_code, ''),
                    COALESCE(po.inv_no, ''),
                    COALESCE(pc.pos_no, ''),
                    po.date_order,
                    po.is_return_order,
                    po.is_void_order,
                    COALESCE(po.the_one_card_no, ''),
                    COALESCE(po.phone_number, ''),
                    COALESCE(pt.sku_ofm, ''),
                    COALESCE(pp.barcode, ''),
                    pol.discount_amount,
                    pol.promotion_id,
                    pol.product_id,
                    pol.qty,
                    pol.price_unit,
                    pol.price_subtotal_wo_discount_incl,
                    pol.price_subtotal_incl,
                    pol.price_subtotal
                    FROM pos_order po
                    LEFT JOIN pos_order_line pol
                    ON po.id = pol.order_id
                    LEFT JOIN pos_session ps
                    ON ps.id = po.session_id
                    LEFT JOIN pos_config pc
                    ON pc.id = ps.config_id
                    LEFT JOIN pos_branch pb
                    ON pb.id = pc.branch_id
                    LEFT JOIN product_product pp
                    ON pp.id = pol.product_id
                    LEFT JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id
                    WHERE po.id = 
                    ''' + str(order.id)

        self._cr.execute(sql_query)
        row = self._cr.fetchone()

        # split order.date_order for rearrangement
        do_datetime = str(tr_convert.convert_datetime_to_bangkok(row[3]))
        do_datetime = do_datetime.split(' ')
        do_fulldate = do_datetime[0]
        do_fulltime = do_datetime[1]
        do_fulltime = do_fulltime[:8]

        do_splitdate = do_fulldate.split('-')
        do_year = do_splitdate[0]
        do_month = do_splitdate[1]
        do_date = do_splitdate[2]

        # LNIdentifier
        batch_data = '1' + DELIMITED_SYMBOL
        # SourceTransID
        transid_seq = "%03d" % source_transid_seq
        batch_data += PARTNER_CODE + '_' + \
                      BRANCH_CODE + row[0] + '_' + \
                      row[1] + '_' + \
                      str(transid_seq) + '_' + \
                      now.strftime('%d') + '_' + \
                      now.strftime('%H%M%S') + now_millisec + \
                      DELIMITED_SYMBOL
        # StoreNo
        batch_data += BRANCH_CODE + row[0] + \
                      DELIMITED_SYMBOL
        # POSNo
        batch_data += row[2] + DELIMITED_SYMBOL
        # ReceiptNo
        receipt_datetime = str(tr_convert.convert_datetime_to_bangkok(row[3]))
        receipt_datetime = receipt_datetime.split()
        receipt_date = receipt_datetime[0].replace('-', '')[6:8]
        receipt_time = receipt_datetime[1].replace(':', '')[0:4]
        batch_data += BRANCH_CODE + row[0] + \
                      row[1] + \
                      receipt_date + \
                      receipt_time + \
                      DELIMITED_SYMBOL
        # TransType
        trans_type = ''
        if row[4] == True:
            trans_type = '07'
        elif row[5] == True:
            trans_type = '09'
        else:
            trans_type = '01'
        batch_data += trans_type + DELIMITED_SYMBOL
        # TransSubType
        # For this function tender all of type always 'T'
        batch_data += 'T' + DELIMITED_SYMBOL
        # TransDate
        # Append by :000 for millisecond cause of 'order_date' was no millisec data stored
        batch_data += do_date + \
                      do_month + \
                      do_year + '_' + \
                      do_fulltime + ':000' + DELIMITED_SYMBOL
        # BusinessDate
        batch_data += do_date + \
                      do_month + \
                      do_year + DELIMITED_SYMBOL
        # InvoiceDate (For online/Call center Only) - Leave blank
        batch_data += DELIMITED_SYMBOL
        # DeliveryDate (For online/Call center Only) - Leave blank
        batch_data += DELIMITED_SYMBOL
        # EarnOnlineFlag
        batch_data += 'N' + DELIMITED_SYMBOL
        # T1CCardNo
        batch_data += self._set_default_na(row[6]) + DELIMITED_SYMBOL
        # MobileNo
        batch_data += self._set_default_na(row[7]) + DELIMITED_SYMBOL
        # UserID
        batch_data += DELIMITED_SYMBOL
        # LineIDS
        batch_data += str(item_seq) + DELIMITED_SYMBOL
        # ProductCode
        batch_data += DELIMITED_SYMBOL
        # ProductBarcode
        batch_data += DELIMITED_SYMBOL
        # Quantity
        batch_data += '1.0000' + DELIMITED_SYMBOL
        # PriceUnit
        batch_data += '0.0000' + DELIMITED_SYMBOL
        # PriceTotal
        batch_data += '0.0000' + DELIMITED_SYMBOL
        # NetPriceUnit
        batch_data += '0.0000' + DELIMITED_SYMBOL

        sql_query = '''
            SELECT 
            absl.amount,
            aj.type,
            UPPER(absl.credit_card_type),
            UPPER(aj.name),
            aj.is_credit_card,
            absl.credit_card_no
            FROM account_bank_statement_line absl
            LEFT JOIN account_journal aj
            ON aj.id = absl.journal_id
            WHERE absl.id = 
        ''' + str(statement.id)

        self._cr.execute(sql_query)
        statement_row = self._cr.fetchone()
        # NetPriceTotal
        net_price_total = 0
        if statement_row[1] == 'cash':
            net_price_total = float(statement_row[0]) + return_amount
        else:
            net_price_total = float(statement_row[0])
        if rounding:
            net_price_total = order.change_rounding
        batch_data += str(abs(net_price_total)) + DELIMITED_SYMBOL
        # DiscountTotal
        batch_data += '0.0000' + DELIMITED_SYMBOL
        # VatAmount
        batch_data += '0.0000' + DELIMITED_SYMBOL
        # TenderType
        tender_type = ''
        if statement_row[1] == 'bank':
            tender_type = statement_row[2]
        else:
            tender_type = statement_row[3]
        if rounding:
            tender_type = 'Rounding'
        batch_data += str(tender_type) + DELIMITED_SYMBOL
        # TenderRefNo
        tender_ref_no = ''
        if statement_row[4]:
            credit_card_front = statement_row[5][:6]
            credit_card_back = statement_row[5][-4:]
            credit_card_replace = 'x' * (len(statement.credit_card_no) - 10)
            tender_ref_no = credit_card_front + credit_card_replace + credit_card_back
            batch_data += tender_ref_no + DELIMITED_SYMBOL
        else:
            batch_data += DELIMITED_SYMBOL
        # OriginalReceiptNo
        original_receipt_no = ''
        # OriginalReceiptNo
        if row[4] == True or row[5] == True:
            if order.return_order_id:
                sql_query = '''
                    SELECT 
                    po.inv_no,
                    po.date_order,
                    pb.branch_code
                    FROM pos_order po
                    LEFT JOIN pos_session ps
                    ON ps.id = po.session_id
                    LEFT JOIN pos_config pc
                    ON pc.id = ps.config_id
                    LEFT JOIN pos_branch pb
                    ON pb.id = pc.branch_id
                    WHERE po.id =
                ''' + str(order.return_order_id.id)
                self._cr.execute(sql_query)
                return_order_row = self._cr.fetchone()
                receipt_datetime = str(tr_convert.convert_datetime_to_bangkok(return_order_row[1]))
                receipt_datetime = receipt_datetime.split()
                receipt_date = receipt_datetime[0].replace('-', '')[6:8]
                receipt_time = receipt_datetime[1].replace(':', '')[0:4]
                batch_data += BRANCH_CODE + return_order_row[2] + \
                              return_order_row[0] + \
                              receipt_date + \
                              receipt_time
        batch_data += DELIMITED_SYMBOL
        # OriginalItemSequenceNo
        batch_data += str(item_seq) + DELIMITED_SYMBOL
        # DisplayReceiptNo
        batch_data += row[1] + DELIMITED_SYMBOL
        # ReturnAllFlag
        return_all_flag = ''
        if order.is_return_order:
            if abs(order.amount_total) == abs(order.return_order_id.amount_total):
                return_all_flag = 'Y'
            else:
                return_all_flag = 'N'
        batch_data += return_all_flag + DELIMITED_SYMBOL

        batch_file.write(batch_data + '\n')

        return item_seq, source_transid_seq


    @api.model
    def batch_add_amount(self, batch_file, order, item_seq, source_transid_seq, discount_grand_total, vat_grand_total):

        # +7 datetime for localize
        now = datetime.now(timezone('Asia/Bangkok'))
        now_millisec = "%03d" % (int(now.strftime('%f')) / 1000)
        tr_convert = self.env['tr.convert']

        source_transid_seq += 1
        item_seq += 1

        sql_query = '''
            SELECT 
            COALESCE(pb.branch_code, ''),
            COALESCE(po.inv_no, ''),
            COALESCE(pc.pos_no, ''),
            po.date_order,
            po.is_return_order,
            po.is_void_order,
            COALESCE(po.the_one_card_no, ''),
            COALESCE(po.phone_number, ''),
            COALESCE(pt.sku_ofm, ''),
            COALESCE(pp.barcode, ''),
            pol.discount_amount,
            pol.promotion_id,
            pol.product_id,
            pol.qty,
            pol.price_unit,
            pol.price_subtotal_wo_discount_incl,
            pol.price_subtotal_incl,
            pol.price_subtotal,
            po.amount_total
            FROM pos_order po
            LEFT JOIN pos_order_line pol
            ON po.id = pol.order_id
            LEFT JOIN pos_session ps
            ON ps.id = po.session_id
            LEFT JOIN pos_config pc
            ON pc.id = ps.config_id
            LEFT JOIN pos_branch pb
            ON pb.id = pc.branch_id
            LEFT JOIN product_product pp
            ON pp.id = pol.product_id
            LEFT JOIN product_template pt
            ON pt.id = pp.product_tmpl_id
            WHERE po.id = 
        ''' + str(order.id)

        self._cr.execute(sql_query)
        row = self._cr.fetchone()
        do_datetime = str(tr_convert.convert_datetime_to_bangkok(row[3]))
        do_datetime = do_datetime.split(' ')
        do_fulldate = do_datetime[0]
        do_fulltime = do_datetime[1]
        do_fulltime = do_fulltime[:8]

        do_splitdate = do_fulldate.split('-')
        do_year = do_splitdate[0]
        do_month = do_splitdate[1]
        do_date = do_splitdate[2]

        # LNIdentifier
        batch_data = '1' + DELIMITED_SYMBOL
        # SourceTransID
        transid_seq = "%03d" % source_transid_seq
        batch_data += PARTNER_CODE + '_' + \
                      BRANCH_CODE + row[0] + '_' + \
                      row[1] + '_' + \
                      str(transid_seq) + '_' + \
                      now.strftime('%d') + '_' + \
                      now.strftime('%H%M%S') + now_millisec + \
                      DELIMITED_SYMBOL
        # StoreNo
        batch_data += BRANCH_CODE + row[0] + DELIMITED_SYMBOL
        # POSNo
        batch_data += row[2] + DELIMITED_SYMBOL
        # ReceiptNo
        receipt_datetime = str(tr_convert.convert_datetime_to_bangkok(row[3]))
        receipt_datetime = receipt_datetime.split()
        receipt_date = receipt_datetime[0].replace('-', '')[6:8]
        receipt_time = receipt_datetime[1].replace(':', '')[0:4]
        batch_data += BRANCH_CODE + row[0] + \
                      row[1] + \
                      receipt_date + \
                      receipt_time + \
                      DELIMITED_SYMBOL
        # TransType
        trans_type = ''
        if row[4] == True:
            trans_type = '07'
        elif row[5] == True:
            trans_type = '09'
        else:
            trans_type = '01'
        batch_data += trans_type + DELIMITED_SYMBOL
        # TransSubType
        # For this function amount all of type always 'A'
        batch_data += 'A' + DELIMITED_SYMBOL
        # TransDate
        # Append by :000 for millisecond cause of 'order_date' was no millisec data stored
        batch_data += do_date + \
                      do_month + \
                      do_year + '_' + \
                      do_fulltime + ':000' + DELIMITED_SYMBOL
        # BusinessDate
        batch_data += do_date + \
                      do_month + \
                      do_year + DELIMITED_SYMBOL
        # InvoiceDate (For online/Call center Only) - Leave blank
        batch_data += DELIMITED_SYMBOL
        # DeliveryDate (For online/Call center Only) - Leave blank
        batch_data += DELIMITED_SYMBOL
        # EarnOnlineFlag
        batch_data += 'N' + DELIMITED_SYMBOL
        # T1CCardNo
        batch_data += self._set_default_na(row[6]) + DELIMITED_SYMBOL
        # MobileNo
        batch_data += self._set_default_na(row[7]) + DELIMITED_SYMBOL
        # UserID
        batch_data += DELIMITED_SYMBOL
        # LineIDS
        batch_data += str(item_seq) + DELIMITED_SYMBOL
        # ProductCode
        batch_data += DELIMITED_SYMBOL
        # ProductBarcode
        batch_data += DELIMITED_SYMBOL
        # Quantity
        batch_data += '1' + DELIMITED_SYMBOL
        # PriceUnit
        batch_data += DELIMITED_SYMBOL
        # PriceTotal
        batch_data += DELIMITED_SYMBOL
        # NetPriceUnit
        batch_data += DELIMITED_SYMBOL
        # NetPriceTotal
        batch_data += str(abs(float(row[18]))) + DELIMITED_SYMBOL
        # DiscountTotal
        # discount_grand_total = round(discount_grand_total, 4)
        batch_data += '' + DELIMITED_SYMBOL
        # VatAmount
        vat_amount = "%0.4f" % abs(vat_grand_total)
        batch_data += str(vat_amount) + DELIMITED_SYMBOL
        # TenderType
        batch_data += DELIMITED_SYMBOL
        # TenderRefNo
        batch_data += DELIMITED_SYMBOL
        # OriginalReceiptNo
        if row[4] == True or row[5] == True:
            if order.return_order_id:
                sql_query = '''
                    SELECT 
                    po.inv_no,
                    po.date_order,
                    pb.branch_code
                    FROM pos_order po
                    LEFT JOIN pos_session ps
                    ON ps.id = po.session_id
                    LEFT JOIN pos_config pc
                    ON pc.id = ps.config_id
                    LEFT JOIN pos_branch pb
                    ON pb.id = pc.branch_id
                    WHERE po.id =
                ''' + str(order.return_order_id.id)
                self._cr.execute(sql_query)
                return_order_row = self._cr.fetchone()
                receipt_datetime = str(tr_convert.convert_datetime_to_bangkok(return_order_row[1]))
                receipt_datetime = receipt_datetime.split()
                receipt_date = receipt_datetime[0].replace('-', '')[6:8]
                receipt_time = receipt_datetime[1].replace(':', '')[0:4]
                batch_data += BRANCH_CODE + return_order_row[2] + \
                              return_order_row[0] + \
                              receipt_date + \
                              receipt_time
        batch_data += DELIMITED_SYMBOL
        # OriginalItemSequenceNo
        batch_data += str(item_seq) + DELIMITED_SYMBOL
        # DisplayReceiptNo
        batch_data += row[1] + DELIMITED_SYMBOL
        # ReturnAllFlag
        return_all_flag = ''
        if order.is_return_order:
            if abs(order.amount_total) == abs(order.return_order_id.amount_total):
                return_all_flag = 'Y'
            else:
                return_all_flag = 'N'
        batch_data += return_all_flag + DELIMITED_SYMBOL

        batch_file.write(batch_data + '\n')

        return item_seq, source_transid_seq