# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    has_sale_orders = fields.Boolean(compute='_compute_has_sale_orders', string='Has Saleorders?',)

    @api.multi
    @api.depends('invoice_line_ids', 'invoice_line_ids.sale_line_ids')
    def _compute_has_sale_orders(self):
        for inv in self:
            sale_order = False
            for line in inv.invoice_line_ids:
                if not sale_order:
                    sale_order = line.sale_line_ids.mapped('order_id')
                else:
                    sale_order |= line.sale_line_ids.mapped('order_id')
            if sale_order:
                inv.has_sale_orders = len(sale_order.ids) > 0
            else:
                inv.has_sale_orders = False

    @api.multi
    def action_view_sale_order(self):
        sale_order = False
        for line in self.invoice_line_ids:
            if not sale_order:
                sale_order = line.sale_line_ids.mapped('order_id')
            else:
                sale_order |= line.sale_line_ids.mapped('order_id')

        action = self.env.ref('sale.action_orders').read()[0]
        if len(sale_order) > 1:
            action['domain'] = [('id', 'in', sale_order.ids)]
        elif len(sale_order) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = sale_order.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action