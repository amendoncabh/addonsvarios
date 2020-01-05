# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
# Copyright (C) 2011-Today Serpent Consulting Services Pvt. Ltd.
#                         (<http://www.serpentcs.com>)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from jasper_reports import jasper_report

from odoo import tools

from jasper_reports.JasperReports.jasper_server import JasperServer

# Determines the port where the JasperServer process should listen
# with its XML-RPC server for incoming calls


class Report(jasper_report.Report):

    def execute_report(self, data_file, output_file, sub_report_data_files):
        locale = self.context.get('lang', 'en_US')
        connection_parameters = {
            'output': self.output_format,
            # 'xml': data_file,
            'csv': data_file,
            'dsn': self.dsn(),
            'user': self.user_name(),
            'password': self.password(),
            'subreports': sub_report_data_files,
        }
        parameters = {
            'STANDARD_DIR': self.report.standard_directory(),
            'REPORT_LOCALE': locale,
            'IDS': ','.join(map(str, self.ids)),
        }
        if 'parameters' in self.data:
            parameters.update(self.data['parameters'])

        server = JasperServer(int(tools.config['jasperport']))
        # server.setPidFile(tools.config['jasperpid'])
        #        java path for jasper server
        company_rec = self.env['res.users'].browse(self.uid).company_id
        server.javapath = company_rec and company_rec.java_path or ''
        server.pidfile = tools.config['jasperpid']
        return server.execute(connection_parameters, self.report_path,
                              output_file, parameters)

jasper_report.Report = Report