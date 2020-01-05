# -*- coding: utf-8 -*-

from datetime import datetime
from pytz import timezone
from odoo import models


class TrConvert(models.Model):
    _name = 'tr.convert'

    def convert_datetime_to_bangkok(self, datetime_utc):
        datetime_format = '%Y-%m-%d %H:%M:%S.%f'
        local_tz = timezone('Asia/Bangkok')
        utc_tz = timezone('UTC')
        if isinstance(datetime_utc, str):
            if len(datetime_utc.split('.')) == 1:
                datetime_utc = datetime_utc + '.1'
            datetime_utc = datetime.strptime(datetime_utc, datetime_format)

        if datetime_utc.tzinfo:
            datetime_bangkok = datetime_utc.replace(tzinfo=utc_tz).astimezone(local_tz)
        else:
            datetime_bangkok = local_tz.localize(datetime_utc)

        return datetime_bangkok