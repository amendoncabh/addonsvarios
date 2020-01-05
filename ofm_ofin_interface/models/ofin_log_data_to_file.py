# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, tools
from datetime import datetime
from pytz import timezone

class OfinLogDataToFile(models.Model):
    _name = 'ofin.log.data.to.file'

    res_id = fields.Integer(
        'Res ID',
    )

    res_model = fields.Char(
        'Res Model',
    )

    log_amount = fields.Integer(
        'Log Amount',
    )

    file_name_ref = fields.Char(
        'File Name Reference',
    )

    date_log_transaction = fields.Date(
        'Log Date',
    )
    branch_code = fields.Char(
        'Branch Code'
    )
