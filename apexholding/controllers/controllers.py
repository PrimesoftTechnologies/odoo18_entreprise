# -*- coding: utf-8 -*-
# from odoo import http


# class Apexholding(http.Controller):
#     @http.route('/apexholding/apexholding', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apexholding/apexholding/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('apexholding.listing', {
#             'root': '/apexholding/apexholding',
#             'objects': http.request.env['apexholding.apexholding'].search([]),
#         })

#     @http.route('/apexholding/apexholding/objects/<model("apexholding.apexholding"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apexholding.object', {
#             'object': obj
#         })

