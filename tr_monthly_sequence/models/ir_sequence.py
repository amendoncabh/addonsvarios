# -*- coding: utf-8 -*-
##############################################################################
#
#    Auto reset sequence by year,month,day
#    Copyright 2013 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
import time
from datetime import datetime, timedelta
from time import mktime

from openerp import fields, models, api, _

_logger = logging.getLogger(__name__)


class IrSequence(models.Model):

    _inherit = 'ir.sequence'

    line_ids = fields.One2many(
        'ir.sequence.line',
        'seq_id',
        string='Sequence line history',
    )
    use_monthly = fields.Boolean(
        string='Use monthly sequence',
    )


    @api.model
    def _getMonthlySequence(self):

        def _interpolate(s, d):
            return (s % d) if s else ''

        def _interpolation_dict():
            if 'date' in self._context and self._context['date']:
                context_temp = self._context['date']
            else:
                context_temp = self._context['ir_sequence_date']

            if context_temp:
                t = context_temp
                if t.find(':') != -1 and t.find('.') == -1:
                    t = time.strptime(t, "%Y-%m-%d %H:%M:%S")
                    dt = datetime.fromtimestamp(mktime(t))
                    dt = dt + timedelta(hours=7)
                    t = dt.timetuple()
                elif t.find('.') != -1:
                    t = time.strptime(t, "%Y-%m-%d %H:%M:%S.%f")
                    dt = datetime.fromtimestamp(mktime(t))
                    dt = dt + timedelta(hours=7)
                    t = dt.timetuple()
                else:
                    t = time.strptime(t, "%Y-%m-%d")
            else:
                t = time.localtime()  # Actually, the server is always in UTC.

            return {
                'year': time.strftime('%Y', t),
                'month': time.strftime('%m', t),
                'day': time.strftime('%d', t),
                'y': time.strftime('%y', t),
                'doy': time.strftime('%j', t),
                'woy': time.strftime('%W', t),
                'weekday': time.strftime('%w', t),
                'h24': time.strftime('%H', t),
                'h12': time.strftime('%I', t),
                'min': time.strftime('%M', t),
                'sec': time.strftime('%S', t),
                'range_year': time.strftime('%Y', t),
            }

        if 'date' in self._context or 'ir_sequence_date' in self._context:
            for seq in self:
                d = _interpolation_dict()
                try:
                    interpolated_prefix = _interpolate(seq['prefix'], d)
                    interpolated_suffix = _interpolate(seq['suffix'], d)
                except ValueError:
                    raise UserWarning(_('Warning'), _('Invalid prefix or suffix for sequence \'%s\'') % (seq.get('name')))

                new = True
                for seq_line in seq.line_ids:
                    # print seq_line
                    if not hasattr(seq_line, 'prefix'):
                        return interpolated_prefix + \
                               '%%0%sd' % seq['padding'] % seq['number_next'] \
                               + interpolated_suffix
                    if seq_line.prefix == interpolated_prefix:
                        number = seq_line.number_next
                        new = False
                        date_now = datetime.now()
                        user_id = self.env.user.id
                        parameter = (
                            seq_line.number_next+1,
                            seq_line.number_next,
                            date_now,
                            user_id,
                            seq_line.id
                        )
                        self.env.cr.execute("""
                            UPDATE ir_sequence_line
                            SET number_next = %s, number_current = %s
                            ,write_date = %s, write_uid = %s
                            where id = %s
                            RETURNING id
                                """, parameter)
                        self.env.cr.fetchone()[0]

                if new is True:
                    number = 1
                    seq_line_obj = self.env['ir.sequence.line']
                    seq_line_obj.create({
                        'seq_id': seq.id,
                        'prefix': interpolated_prefix,
                        'number_current': 1,
                        'number_next': 2,
                    })
                next = interpolated_prefix + '%%0%sd' % seq['padding'] % number + interpolated_suffix
        else:
            for seq in self:
                next = seq._next_do()
        return next

    @api.model
    def _next(self):
        if not self.use_monthly:
            res = self._getMonthlySequence()
        else:
            res = super(IrSequence, self)._next()
        return res


class IrSequenceLine(models.Model):
    _name = 'ir.sequence.line'
    _description = "Sequence Line History"

    seq_id = fields.Many2one(
        'ir.sequence',
        string='Sequence',
    )
    prefix = fields.Char(
        string='Prefix',
    )
    number_current = fields.Integer(
        string='Current Number',
    )
    number_next = fields.Integer(
        string='Next Number',
    )
