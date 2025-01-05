# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import xlsxwriter
from io import BytesIO
import base64
import re

class ReporteVentasMes(models.Model):
    _name = 'sale_reportes.ventas_mes'
    _description = 'Reporte de Ventas'

    fechaInicio = fields.Date('Fecha de Inicio', required=True)
    fechaTermino = fields.Date('Fecha de Término', required=True)


class SaleReport(models.Model):
    _name = 'sale_reportes.tipo_producto'
    _description = 'Reporte de Ventas'

    start_date = fields.Date('Fecha de Inicio', required=True)
    end_date = fields.Date('Fecha de Término', required=True)
    excel_file = fields.Binary('Archivo Excel', readonly=True)
    file_name = fields.Char('Nombre del Archivo', readonly=True)
    
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
        
        headers = [
            'Folio', 'Doc', 'Descripción', 'Operación', 'Fecha', 'Cod.', 'Origen', 'GuiaDes', 'Patente', 'Rut', 'Dv', 'Cliente',
            'Tot.Pzas.', 'Tot.M3', 'Tot.Pulg.', 'Total', 'Excento', 'Fepco', 'IVA', 'Tot.Gen', 'Ult.Lin.', 'Nula', #TOTAL FACTURA
            'Linea', 'Cod.', 'Producto', 'Espesor', 'Ancho', 'Largo', 'SiNo', 'Cod.', 'C.Costo', 'Cod.', 'Mercado', 'Cant.', 'M3', 'Pulg.', 
            'M/M', '$/Unitario', 'Total', 'C.C.', 'C.T.', 'Nombre C.T', 'Cta.', 'Des.Cta.'
        ]
        worksheet.write_row(0, 0, headers, header_format)
        
        # Habilitar los filtros para la hoja
        worksheet.autofilter(0, 0, 0, len(headers) - 1)

        # Fila inicial para los datos
        row = 1
    
        documentos_tributarios = self.env['account.move'].search([
            ('invoice_date', '>=', self.start_date),
            ('invoice_date', '<=', self.end_date),
            ('folio_factura', '!=', False)
        ])
        
        for documento in documentos_tributarios:
            folio_despacho = 'Folio Despacho No Encontrado'    
            for line in documento.invoice_line_ids:
                if line.display_type == 'line_section':
                    resultado = re.search(r": (\d+)", line.name) 
                    if resultado:    
                        folio_despacho = resultado.group(1).strip()   
                        print("PRODUCTO", folio_despacho)
                else:                        
                    RUT, DV = documento.partner_id.vat.split("-")
                    quantity = sum(line.quantity for line in documento.invoice_line_ids)
                    subtotal = sum(line.price_subtotal for line in documento.invoice_line_ids)
                    iva = round(subtotal*0.19,0)
                    total = subtotal+iva
                    m3 = 0
                    pulgada = 0
                    if line.product_id.packaging_ids:
                        m3 = line.product_id.packaging_ids[0].m3
                        pulgada = line.product_id.packaging_ids[0].pulgada
                    worksheet.write_row(row, 0, [
                        documento.folio_factura, documento.document_type_code, documento.l10n_latam_document_type_id.name, '', documento.invoice_date, '', '', folio_despacho, '', RUT, DV, documento.partner_id.name,
                        quantity, '', '', subtotal, '', '',  iva, total, '', '', 
                        '', '', line.product_id.name, round(line.product_id.espesor,2), round(line.product_id.ancho,2), round(line.product_id.largo,2), '', '', '', '', '', line.quantity, m3, pulgada,
                        '', line.price_unit, line.price_subtotal, '', '', '', '', ''
                        
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


    def generate_sale_report(self):
        # Validar las fechas
        if not self.start_date or not self.end_date:
            raise ValueError('Debe especificar una fecha de inicio y una de término.')

        # Query para obtener los datos agrupados por cliente y tipo de producto
        query = """
            SELECT
                partner.name AS customer_name,
                SUM(CASE WHEN template."isAserradero" THEN line.product_uom_qty ELSE 0 END) AS aserradero_qty,
                SUM(CASE WHEN template."isSecado" THEN line.product_uom_qty ELSE 0 END) AS seco_qty,
                SUM(CASE WHEN template."isImpregnado" THEN line.product_uom_qty ELSE 0 END) AS impregnado_qty,
                SUM(CASE WHEN template."isRemanufactura" THEN line.product_uom_qty ELSE 0 END) AS remanufactura_qty,
                SUM(CASE WHEN template."isFinger" THEN line.product_uom_qty ELSE 0 END) AS finger_qty
            FROM
                sale_order_line AS line
            JOIN
                sale_order AS so ON line.order_id = so.id
            JOIN
                res_partner AS partner ON so.partner_id = partner.id
            JOIN
                product_product AS product ON line.product_id = product.id
            JOIN
                product_template AS template ON product.product_tmpl_id = template.id
            WHERE
                so.state IN ('sale')
                AND so.date_order >= %s
                AND so.date_order <= %s
            GROUP BY
                partner.name
            ORDER BY
                partner.name
        """
        self._cr.execute(query, (self.start_date, self.end_date))
        results = self._cr.fetchall()

        # Crear el archivo Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Reporte de Ventas')

        # Formato para encabezados y totales
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
        total_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})

        # Agregar encabezados
        headers = ['Cliente', 'Aserradero', 'Seco', 'Impregnado', 'Remanufactura', 'Finger', 'Total Cliente']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Agregar datos
        row = 1
        col_totals = [0] * 5  # Para acumular totales por columna
        for result in results:
            worksheet.write(row, 0, result[0])  # Nombre del cliente
            row_total = 0  # Para acumular el total por cliente
            for col in range(1, 6):
                value = result[col]
                worksheet.write(row, col, value)
                row_total += value
                col_totals[col - 1] += value
            worksheet.write(row, 6, row_total, total_format)  # Total por cliente
            row += 1

        # Agregar totales horizontales (última fila)
        worksheet.write(row, 0, 'Total Tipo', total_format)
        for col in range(1, 6):
            worksheet.write(row, col, col_totals[col - 1], total_format)
        worksheet.write(row, 6, sum(col_totals), total_format)  # Total general

        workbook.close()
        output.seek(0)

        # Guardar el archivo en el campo Binary
        excel_file = base64.b64encode(output.read())
        output.close()

        # Crear el registro con el archivo
        self.write({
            'excel_file': excel_file,
            'file_name': 'Reporte_de_Ventas.xlsx'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{self.file_name}',
            'target': 'self',
        }

class ReporteDespachoSubproductos(models.Model):
    _name = 'sale_reportes.despacho_subproductos'
    
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
            'Nombre Producto', 'Cantidad Producto', 'Precio', 'Total',
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
                venta = self.env['sale.order'].search([
                    ('name', '=', despacho.origin),
                ], limit=1)
                if despacho.move_line_ids_without_package:
                    for row_paquete in despacho.move_line_ids_without_package:
                        id_producto = row_paquete.product_id.id
                        sku = row_paquete.product_id.default_code
                        nombre_producto = row_paquete.product_id.name
                        cantidad_producto = row_paquete.qty_done
                        precio = row_paquete.price_unit
                        chofer = despacho.chofer or "Desconocido"
                        patente_camion = despacho.patente_camion or "Desconocida"
                        origin = ''
                        if venta:
                            origin = venta.origin
                        # Escribir los datos en la hoja de Excel
                        worksheet.write_row(row, 0, [
                            despacho.date_done, despacho.folio_despacho, despacho.partner_id.name, despacho.partner_child_id.name,
                            origin, nombre_producto,
                            cantidad_producto, precio or 0, precio * cantidad_producto,
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
                venta = self.env['sale.order'].search([
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
                            origin = ''
                            if venta:
                                origin = venta.origin
                            # Escribir los datos en la hoja de Excel
                            worksheet.write_row(row, 0, [
                                despacho.date_done, despacho.folio_despacho, despacho.partner_id.name, despacho.partner_child_id.name,
                                origin,
                                paquete_nombre, sku, nombre_producto,
                                cantidad_producto, precio or 0, precio * cantidad_producto,
                                chofer, patente_camion
                            ])
                            row += 1
                            
                elif despacho.move_line_ids_without_package:
                    for row_paquete in despacho.move_line_ids_without_package:
                        id_producto = row_paquete.product_id.id
                        sku = row_paquete.product_id.default_code
                        nombre_producto = row_paquete.product_id.name
                        cantidad_producto = row_paquete.qty_done
                        precio = row_paquete.price_unit
                        chofer = despacho.chofer or "Desconocido"
                        patente_camion = despacho.patente_camion or "Desconocida"
                        origin = ''
                        if venta:
                            origin = venta.origin
                        # Escribir los datos en la hoja de Excel
                        worksheet.write_row(row, 0, [
                            despacho.date_done, despacho.folio_despacho, despacho.partner_id.name, despacho.partner_child_id.name,
                            origin,
                            '', sku, nombre_producto,
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
            
            
