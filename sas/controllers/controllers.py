# -*- coding: utf-8 -*-
# from odoo import http


# class Sas(http.Controller):
#     @http.route('/sas/sas', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sas/sas/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sas.listing', {
#             'root': '/sas/sas',
#             'objects': http.request.env['sas.sas'].search([]),
#         })

#     @http.route('/sas/sas/objects/<model("sas.sas"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sas.object', {
#             'object': obj
#         })

