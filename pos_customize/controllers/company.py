# -*- coding: utf-8 -*-

import functools
import imghdr
import json
import logging
import os
import sys
from cStringIO import StringIO

import jinja2

try:
    import xlwt
except ImportError:
    xlwt = None

import odoo
import odoo.modules.registry
from odoo.modules import get_resource_path
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.web', "views")

env = jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = json.dumps

# 1 week cache for asset bundles as advised by Google Page Speed
BUNDLE_MAXAGE = 60 * 60 * 24 * 7

#----------------------------------------------------------
# OpenERP Web helpers
#----------------------------------------------------------

db_list = http.db_list

db_monodb = http.db_monodb


class BinaryPos(http.Controller):

 
    @http.route([
                '/web/binary_pos/pos_company_logo',
                ], type='http', auth="none", cors="*")
    def pos_company_logo(self, dbname=None, company_id=None, ** kw):
    
        imgname = 'logo'
        imgext = '.png'
        placeholder = functools.partial(get_resource_path, 'web', 'static', 'src', 'img')
        uid = None
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = odoo.SUPERUSER_ID
            
#        if not company_id:
#            company_id = 1

        if not dbname:
            response = http.send_file(placeholder(imgname + imgext))
        else:
            try:
                # create an empty registry
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    cr.execute("""select image,write_date from pos_company c where id=%s
                               """, (company_id, ))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_base64 = str(row[0]).decode('base64')
                        image_data = StringIO(image_base64)
                        imgext = '.' + (imghdr.what(None, h=image_base64) or 'png')
                        response = http.send_file(image_data, filename=imgname + imgext, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname + imgext))

        return response
