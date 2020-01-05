# -*- coding: utf-8 -*-
#----------------------------------------------------------
# Inherit OpenERP HTTP layer
#----------------------------------------------------------

import logging
import werkzeug.contrib.sessions
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.local
import werkzeug.routing
import werkzeug.wrappers
import werkzeug.wsgi

from odoo.http import JsonRequest

import json

_logger = logging.getLogger(__name__)


def __init__(self, *args):
    super(JsonRequest, self).__init__(*args)

    self.jsonp_handler = None

    args = self.httprequest.args
    jsonp = args.get('jsonp')
    self.jsonp = jsonp
    request = None
    request_id = args.get('id')

    if jsonp and self.httprequest.method == 'POST':
        # jsonp 2 steps step1 POST: save call
        def handler():
            self.session['jsonp_request_%s' % (request_id,)] = self.httprequest.form['r']
            self.session.modified = True
            headers=[('Content-Type', 'text/plain; charset=utf-8')]
            r = werkzeug.wrappers.Response(request_id, headers=headers)
            return r
        self.jsonp_handler = handler
        return
    elif jsonp and args.get('r'):
        # jsonp method GET
        request = args.get('r')
    elif jsonp and request_id:
        # jsonp 2 steps step2 GET: run and return result
        request = self.session.pop('jsonp_request_%s' % (request_id,), '{}')
    else:
        # regular jsonrpc2
        request = self.httprequest.stream.read()

    # Read POST content or POST Form Data named "request"
    _logger.info('\nfrom ip:%s session_uid:%s session_user: %s session_db: %s \n'
                 'session_token: %s path %s \nreceived parameter:\n%s \nheader:\n%s',
                 self.httprequest.remote_addr, self.httprequest.session.uid, self.httprequest.session.login,
                 self.httprequest.session.db, self.httprequest.session.session_token,
                 self.httprequest.path, request, self.httprequest.headers)
    try:
        self.jsonrequest = json.loads(request)
    except ValueError:
        msg = 'Invalid JSON data: %r' % (request,)
        _logger.info('%s: %s', self.httprequest.path, msg)
        raise werkzeug.exceptions.BadRequest(msg)

    self.params = dict(self.jsonrequest.get("params", {}))
    self.context = self.params.pop('context', dict(self.session.context))


JsonRequest.__init__ = __init__
