# -*- coding: utf-8 -*-
# from odoo import http


# class SaleReportes(http.Controller):
#     @http.route('/sale_reportes/sale_reportes', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_reportes/sale_reportes/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_reportes.listing', {
#             'root': '/sale_reportes/sale_reportes',
#             'objects': http.request.env['sale_reportes.sale_reportes'].search([]),
#         })

#     @http.route('/sale_reportes/sale_reportes/objects/<model("sale_reportes.sale_reportes"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_reportes.object', {
#             'object': obj
#         })
