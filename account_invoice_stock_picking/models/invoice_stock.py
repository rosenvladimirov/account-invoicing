# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Saritha Sahadevan(<https://www.cybrosys.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <https://www.gnu.org/licenses/>.
#
##############################################################################
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    picking_count_ids = fields.Integer(string="Picking count", compute="_compute_picking_count_ids")

    @api.multi
    def _compute_picking_count_ids(self):
        for record in self:
            record.picking_count_ids = len(record.picking_ids.ids)

    @api.multi
    def action_stock_receive(self, invoice_lines=None):
        for order in self:
            company = self.env.user.company_id.id
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
            picking_type_id = warehouse_id.in_type_id
            moves = self.env['stock.move']
            picking = order.picking_ids
            if invoice_lines is None:
                invoice_lines = self.invoice_line_ids.filtered(lambda r: r.product_id.type in ['product', 'consu'])
            if not invoice_lines:
                raise UserError(_('Please create some invoice lines.'))
            if not self.number:
                raise UserError(_('Please Validate invoice.'))
            if not self.has_picking_ids:
                location_dest_id = picking_type_id.default_location_dest_id.id
                location_id = self.partner_id.property_stock_supplier.id
                pick = {
                    'picking_type_id': picking_type_id.id,
                    'partner_id': self.partner_id.id,
                    'origin': self.number,
                    'location_dest_id': location_dest_id,
                    'location_id': location_id,
                    'scheduled_date': order.date_invoice,
                    'date': order.date_invoice,
                }
                picking = self.env['stock.picking'].create(pick)
                self.picking_ids = [(6, 0, [picking.id])]
                for line in invoice_lines:
                    moves |= line.with_context(dict(self._context, force_period_date=order.date_invoice))._create_stock_moves(line, picking)
                move_ids = moves._action_confirm()
                move_ids._action_assign()
            return picking

    @api.multi
    def action_stock_transfer(self, invoice_lines=None):
        for order in self:
            company = self.env.user.company_id.id
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
            picking_type_id = warehouse_id.out_type_id
            moves = self.env['stock.move']
            picking = order.picking_ids
            if invoice_lines is None:
                invoice_lines = order.invoice_line_ids.filtered(lambda r: r.product_id.type in ['product', 'consu'])
            if not invoice_lines:
                raise UserError(_('Please create some invoice lines.'))
            if not self.number:
                raise UserError(_('Please Validate invoice.'))
            if not self.has_picking_ids:
                location_dest_id = self.partner_id.property_stock_customer.id
                location_id = picking_type_id.default_location_src_id.id
                pick = {
                    'picking_type_id': picking_type_id.id,
                    'partner_id': self.partner_id.id,
                    'origin': self.number,
                    'location_dest_id': location_dest_id,
                    'location_id': location_id,
                    'invoice_ids': [(4, self.id)],
                    'scheduled_date': order.date_invoice,
                    'date': order.date_invoice,
                }
                picking = self.env['stock.picking'].create(pick)
                self.picking_ids = [(6, 0, [picking.id])]
                for line in invoice_lines:
                    moves |= line.with_context(dict(self._context, force_period_date=order.date_invoice))._create_stock_moves_transfer(line, picking)
                move_ids = moves._action_confirm()
                move_ids._action_assign()
            return picking

    @api.multi
    def action_view_picking(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_ready')
        result = action.read()[0]
        result.pop('id', None)
        #_logger.info("CONTEXT %s" % result['context'])
        if result.get('context'):
            result['context'] = {}
        result['context'].update({'force_accounting_date': self.date_invoice})
        result['domain'] = [('id', 'in', self.picking_ids.ids)]
        if len(self.picking_ids.ids) > 0:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.picking_ids.ids[0]
        return result


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.multi
    def _create_stock_moves(self, line, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        price_unit = line.price_unit
        location_id = 'location_id' in line._fields and line.location_id.id or line.invoice_id.partner_id.property_stock_supplier.id
        location_dest_id = 'location_dest_id' in line._fields and line.location_dest_id.id or picking.picking_type_id.default_location_dest_id.id
        template = {
            'name': line.name or '',
            'product_id': line.product_id.id,
            'product_uom': line.uom_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'picking_id': picking.id,
            'move_dest_id': False,
            'state': 'draft',
            'company_id': line.invoice_id.company_id.id,
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

    def _create_stock_moves_transfer(self, line, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        price_unit = line.price_unit
        location_id = 'location_id' in line._fields and line.location_id.id or picking.picking_type_id.default_location_src_id.id
        location_dest_id = 'location_dest_id' in line._fields and line.location_dest_id.id or line.invoice_id.partner_id.property_stock_customer.id
        template = {
            'name': line.name or '',
            'product_id': line.product_id.id,
            'product_uom': line.uom_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'picking_id': picking.id,
            'move_dest_id': False,
            'state': 'draft',
            'company_id': 'company_id' in line._fields and line.company_id.id or line.invoice_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': picking.picking_type_id.id,
            'procurement_id': False,
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
