#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        values = super()._prepare_invoice_line(**optional_values)
        self.ensure_one()
        values.update({
            'product_set_id': self.product_set_id.id,
            'product_set_line_id': self.product_set_line_id.id,
        })
        return values
