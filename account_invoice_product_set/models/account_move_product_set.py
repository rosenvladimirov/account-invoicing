#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class AccountMoveProductSet(models.Model):
    _name = 'account.move.product.set'
    _description = 'Invoice Product Sets'
    # _auto = False

    move_id = fields.Many2one('account.move', 'Invoice', required=True)
    product_set_section_id = fields.Many2one('account.move.line', 'Product Set Section')
    product_set_id = fields.Many2one('product.set', 'Product Set')
    quantity = fields.Float('Quantity', digits='Product Unit of Measure')
    price_unit = fields.Float('Unit Price', compute='_compute_price_unit', store=True, precompute=True)
    price_subtotal = fields.Monetary(string="Subtotal")
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id')

    @api.depends('quantity', 'price_subtotal')
    def _compute_price_unit(self):
        for line in self:
            quantity = line.quantity != 0.0 and line.quantity or 1.0
            line.update({
                'price_unit': line.price_subtotal / quantity,
            })

    def _get_account_move_product_set_value(self, move_id, product_set_id, price_subtotal, quantity):
        return {
            'move_id': move_id.id,
            'product_set_id': product_set_id.id,
            'price_subtotal': price_subtotal,
            'quantity': quantity,
        }
