# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)


class AccountInvoicePicking(models.TransientModel):
    _name = "account.invoice.picking"
    _description = "Transfer invoice to picking"

    invoice_lines = fields.One2many("account.invoice.picking.line", "invoice_piking_id", string="Invoice lines")
    invoice_id = fields.Many2one("account.invoice", string="Invoice")
    journal_id = fields.Many2one('account.journal', string='Journal')
    location_dest_id = fields.Many2one('stock.location', "Destination Location")

    @api.model
    def default_get(self, fields):
        res = super(AccountInvoicePicking, self).default_get(fields)
        company_id = self.env.user.company_id.id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
        if self._context.get('type') == 'in_invoice':
            picking_type_id = warehouse_id.in_type_id
        elif self._context.get('type') == 'out_invoice':
            picking_type_id = warehouse_id.out_type_id

        if self.invoice_id:
            inv = self.invoice_id
        else:
            inv = self.env["account.invoice"].browse(self.env.context['active_id'])
        invoice_lines = []
        for line in inv.invoice_line_ids.filtered(lambda r: r.product_id.type in ['product', 'consu']):
            line_new = {}
            line_new['location_id'] = inv.partner_id.property_stock_supplier.id
            line_new['location_dest_id'] = picking_type_id.default_location_dest_id.id
            line_new['company_id'] = company_id
            line_new['invoice_line_id'] = line.id
            line_new['warehouse_id'] = picking_type_id.warehouse_id.id
            line_new['name'] = line.name
            line_new['product_id'] = line.product_id.id
            line_new['uom_id'] = line.uom_id.id
            line_new['price_unit'] = line.price_unit
            line_new['quantity'] = line.quantity
            invoice_lines.append(line_new)
        res.update({
            'invoice_lines': [(0, 0, x) for x in invoice_lines],
            'invoice_id': inv.id,
            'location_dest_id': picking_type_id.default_location_dest_id.id,
        })
        #_logger.info("DEFAULT GET %s:%s" % (res, picking_type_id.default_location_dest_id.id))
        return res

    @api.multi
    def action_stock_receive(self):
        for invoice in self.invoice_id:
            #_logger.info("CONTEXT %s" % self._context)
            picking = invoice.with_context(dict(self._context, journal_type="general")).action_stock_receive(self.invoice_lines)
        return self._get_picking_action(picking)

    @api.multi
    def action_stock_transfer(self):
        for invoice in self.invoice_id:
            picking = invoice.with_context(dict(self._context, journal_type="general")).action_stock_transfer(self.invoice_lines)
        return self._get_picking_action(picking)

    def _get_picking_action(self, pickinig):
        action = self.env.ref("stock.action_picking_tree_all").read()[0]
        form_view = self.env.ref("stock.view_picking_form").id
        if len(pickinig.ids) > 1:
            pickinig_id = pickinig[0].id
        else:
            pickinig_id = pickinig.id
        action.update({
            "domain": [('id', 'in', pickinig.ids)],
            "view_mode": "form",
            "views": [(form_view, "form")],
            "res_id": pickinig_id,
        })
        return action

    @api.onchange('location_dest_id')
    def onchange_location_dest_id(self):
        if self.location_dest_id:
            self.invoice_lines.update({'location_dest_id': self.location_dest_id.id})


class AccountInvoicePickingLine(models.TransientModel):
    _name = "account.invoice.picking.line"
    _description = "Transfer invoice lines to picking"

    invoice_piking_id = fields.Many2one("account.invoice.picking", "Invoice lines")
    invoice_line_id = fields.Many2one("account.invoice.line", "Invoice line")
    name = fields.Text(string='Description', related="invoice_line_id.name", readonly=True,)
    product_id = fields.Many2one('product.product', string='Product', related="invoice_line_id.product_id", readonly=True,)
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', related="invoice_line_id.uom_id", readonly=True,)
    price_unit = fields.Float(string='Unit Price', related="invoice_line_id.price_unit", digits=dp.get_precision('Product Price'), readonly=True,)
    location_id = fields.Many2one('stock.location', "Source Location")
    location_dest_id = fields.Many2one('stock.location', "Destination Location")
    company_id = fields.Many2one('res.company', 'Company')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'))

    @api.multi
    def _create_stock_moves(self, line, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        price_unit = line.price_unit
        template = {
            'name': line.name or '',
            'product_id': line.company_id and line.product_id.id,
            'product_uom': line.uom_id and line.uom_id.id,
            'location_id': line.location_id and line.location_id.id,
            'location_dest_id': line.location_id and line.location_dest_id.id,
            'picking_id': picking.id,
            'move_dest_id': False,
            'state': 'draft',
            'company_id': line.company_id and line.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': picking.picking_type_id.id,
            'procurement_id': False,
            'procure_method': 'make_to_stock',
            'invoice_line_id': 'invoice_line_id' in line._fields and line.invoice_line_id.id or line.id,
            'route_ids': 1 and [
                (6, 0, [x.id for x in self.env['stock.location.route'].search([('id', 'in', (2, 3))])])] or [],
            'warehouse_id': picking.picking_type_id.warehouse_id.id,
            'date_expected': picking.scheduled_date,
            'create_date': picking.date,
        }
        diff_quantity = line.quantity
        tmp = template.copy()
        tmp.update({
            'product_uom_qty': diff_quantity,
        })
        template['product_uom_qty'] = diff_quantity
        done += moves.create(template)
        return done

