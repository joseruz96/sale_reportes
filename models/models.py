# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import xlsxwriter
from io import BytesIO
import base64

# class sale_reportes(models.Model):
#     _name = 'sale_reportes.sale_reportes'
#     _description = 'sale_reportes.sale_reportes'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

class ReporteGeneralVentaDespacho(models.Model):
    _name = "sale_reportes.reporte_general_venta_despacho"
    
    fechaInicio = fields.Datetime("Fecha Incio")
    fechaTermino = fields.Datetime("Fecha Término")

    def reporte(self):

        
        # Crear un objeto BytesIO para guardar el archivo Excel en memoria
        output = BytesIO()

        # Crear un libro de trabajo en Excel
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Reporte Despachos')
        # Formato del encabezado: negrita con fondo azul
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#0070C0',  # Azul
            'font_color': '#FFFFFF',  # Blanco
            'align': 'center',
            'valign': 'vcenter',
        })

        # Definir los encabezados del archivo Excel
        headers = [
            'Fecha Despacho', 'N° Guía', 'Cliente', 'Destino', 'OC',
            'Nombre Paquete', 'ID Producto', 'Nombre Producto', 
            'Cantidad Producto', 'Precio', 'Total',
            'Chofer', 'Patente Camión'
        ]
        worksheet.write_row(0, 0, headers, header_format)
        
        # Habilitar los filtros para la hoja
        worksheet.autofilter(0, 0, 0, len(headers) - 1)

        # Fila inicial para los datos
        row = 1
        
         # Buscar despachos asociados a la venta
        despachos = self.env['stock.picking'].search([
            ('date_done', '>=', self.fechaInicio),
            ('date_done', '<=', self.fechaTermino),
            ('location_id.distribucion_location', '=', True),
            ('state', '=', 'done'),
            ('picking_type_id.code', '=', 'outgoing'),
            ('returned', '=', False),
            ('folio_despacho', '!=', False)
        ])
        
        if despachos:
            for despacho in despachos:
                # Obtener los paquetes del despacho
                venta = self.env['stock.picking'].search([
                    ('name', '=', despacho.origin),
                ], limit=1)
                if despacho.package_level_ids_details:
                    for row_paquete in despacho.package_level_ids_details:
                        paquete = row_paquete.package_id
                        if paquete:
                            # Extraer la información requerida
                            paquete_nombre = paquete.name or "Sin nombre"
                            quant = paquete.quant_ids and paquete.quant_ids[0] or None
                            if quant:
                                id_producto = quant.product_id.id
                                sku = quant.product_id.default_code
                                nombre_producto = quant.product_id.name
                                cantidad_producto = quant.quantity
                            else:
                                sku = "N/A"
                                nombre_producto = "N/A"
                                cantidad_producto = 0
                            
                            precio = False
                            for line in venta.order_line:
                                print("line.product_id.id",line.product_id.id)
                                print("id_producto.id",id_producto)
                                if line.product_id.id == id_producto:
                                    precio = line.price_unit
                                    print("precio",precio)
                                    break

                            chofer = despacho.chofer or "Desconocido"
                            patente_camion = despacho.patente_camion or "Desconocida"

                            # Escribir los datos en la hoja de Excel
                            worksheet.write_row(row, 0, [
                                despacho.date_done, despacho.folio_despacho, despacho.partner_id.name, despacho.partner_child_id.name,
                                venta.origin,
                                paquete_nombre, sku, nombre_producto,
                                cantidad_producto, precio or 0, precio * cantidad_producto,
                                chofer, patente_camion
                            ])
                            row += 1
                                
        # Ajustar el ancho de las columnas para una mejor visualización
        worksheet.set_column(0, len(headers) - 1, 15)

        # Cerrar el libro de trabajo para finalizar la creación del archivo
        workbook.close()

        # Volver al principio del archivo para enviarlo como respuesta
        output.seek(0)

        # Codificar en base64
        file_data = base64.b64encode(output.read()).decode('utf-8')

        # Crear el archivo como un adjunto en Odoo
        attachment = self.env['ir.attachment'].create({
            'name': 'Reporte_Venta_Despacho.xlsx',
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Devolver el archivo como un enlace de descarga
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }
        
class DetalleGeneralVentaDespacho(models.Model):
    _name = "sale_reportes.detalle_general_venta_despacho"
    
    fechaDespacho = fields.Datetime()
    guiaDespachoSII = fields.Char()
    nombreCliente = fields.Char()
    documentoOC = fields.Char()
    nombreProducto = fields.Char()
    cantidadProducto = fields.Integer()
    precioUnitario = fields.Float()
    nombreTransportista = fields.Char()
    nombreChofer = fields.Char()
    patenteCamion = fields.Char()
            
            
