# -*- coding: utf-8 -*-

# class MiePos(http.Controller):
#     @http.route('/mie_pos/mie_pos/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mie_pos/mie_pos/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mie_pos.listing', {
#             'root': '/mie_pos/mie_pos',
#             'objects': http.request.env['mie_pos.mie_pos'].search([]),
#         })

#     @http.route('/mie_pos/mie_pos/objects/<model("mie_pos.mie_pos"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mie_pos.object', {
#             'object': obj
#         })