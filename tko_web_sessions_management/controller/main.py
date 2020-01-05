# -*- encoding: utf-8 -*-

import simplejson
import time
from odoo import SUPERUSER_ID
from odoo import fields, _
from datetime import datetime
from dateutil.relativedelta import *

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import Session
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import odoo

import logging


_logger = logging.getLogger(__name__)

class websession(http.Controller):
    @http.route(['/ajax/session/'], auth="public", website=True)
    def property_map(self, **kwargs):
        session = []
        if request.session.uid == None:
            session.append({'result': 'true'})
            content = simplejson.dumps(session)
            return request.make_response(content, [('Content-Type', 'application/json;charset=utf-8')])


class MySession(Session):

    @http.route('/web/session/authenticate', type='json', auth="none")
    def authenticate(self, db, login, password, base_location=None):
        request.session.authenticate(db, login, password)
        uid = request.env['ir.http'].session_info()

        if uid.get('uid', False):
            self.save_session(
                request.env.user.tz,
                request.httprequest.session.sid,
            )
        return uid

    def save_session(
            self,
            tz,
            sid,
            unsuccessful_message='',
    ):
        now = fields.datetime.now()
        session_obj = request.env['ir.sessions']
        cr = request.registry.cursor()

        # Get IP, check if it's behind a proxy
        ip = request.httprequest.headers.environ['REMOTE_ADDR']
        forwarded_for = ''
        if 'HTTP_X_FORWARDED_FOR' in request.httprequest.headers.environ and request.httprequest.headers.environ[
            'HTTP_X_FORWARDED_FOR']:
            forwarded_for = request.httprequest.headers.environ['HTTP_X_FORWARDED_FOR'].split(', ')
            if forwarded_for and forwarded_for[0]:
                ip = forwarded_for[0]

        # for GeoIP
        geo_ip_resolver = None
        ip_location = ''
        try:
            import GeoIP
            geo_ip_resolver = GeoIP.open(
                '/usr/share/GeoIP/GeoIP.dat',
                GeoIP.GEOIP_STANDARD)
        except ImportError:
            geo_ip_resolver = False
        if geo_ip_resolver:
            ip_location = (str(geo_ip_resolver.country_name_by_addr(ip)) or '')

        # autocommit: our single update request will be performed atomically.
        # (In this way, there is no opportunity to have two transactions
        # interleaving their cr.execute()..cr.commit() calls and have one
        # of them rolled back due to a concurrent access.)
        cr.autocommit(True)
        user = request.env.user
        logged_in = True
        uid = user.id
        if unsuccessful_message:
            uid = SUPERUSER_ID
            logged_in = False
            sessions = False
        else:
            sessions = session_obj.search([('session_id', '=', sid),
                                           ('ip', '=', ip),
                                           ('user_id', '=', uid),
                                           ('logged_in', '=', True)],
                                          )
        if not sessions:
            date_expiration = (now + relativedelta(seconds=user.session_default_seconds)).strftime(
                DEFAULT_SERVER_DATETIME_FORMAT)
            values = {
                'user_id': uid,
                'logged_in': logged_in,
                'session_id': sid,
                'session_seconds': user.session_default_seconds,
                'multiple_sessions_block': user.multiple_sessions_block,
                'date_login': now.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'date_expiration': date_expiration,
                'ip': ip,
                'ip_location': ip_location,
                'remote_tz': tz or 'GMT',
                'unsuccessful_message': unsuccessful_message,
            }
            session_obj.sudo().create(values)
            cr.commit()
        cr.close()


Session = MySession()
odoo.addons.web.controllers.main.Session.authenticate = Session.authenticate
