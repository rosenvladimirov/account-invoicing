#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_set_id = fields.Many2one('product.set', string='Product set')
    product_set_line_id = fields.Many2one('product.set.line', string='Product set line')

    # display_type = fields.Selection(selection_add=[
    #     ('product_set', 'Product set'),
    # ])

    def _sale_prepare_sale_line_values(self, order, price):
        values = super()._sale_prepare_sale_line_values(order, price)
        values.update({
          'product_set_id': self.product_set_id.id,
          'product_set_line_id': self.product_set_line_id.id,
        })
        return values
    
    @api.model_create_multi
    def create(self, vals_list):
        inx = None
        move_id = False
        sequence = 0
        for sequence_inx, vals in enumerate(vals_list):
            move_id = self.env['account.move'].search([('id', '=', vals['move_id'])], limit=1)
            if move_id.invoice_line_ids:
                sequence = move_id.invoice_line_ids[-1].sequence
                vals.update({'sequence': sequence + 2 + sequence_inx})
                product_set_id = move_id.invoice_line_ids[-1].product_set_id
                if product_set_id:
                    product_ids = product_set_id.set_line_ids
                    if vals.get('product_id') in product_ids.mapped('product_id').ids:
                        vals.update({
                            'product_set_id': product_set_id.id,
                            'product_set_line_id': product_ids.mapped('product_id').
                            filtered(lambda p: p.id == vals.get('product_id')).id,
                        })
                    elif vals.get('product_id') and inx is None:
                        inx = sequence_inx
        if inx is not None:
            vals_list.insert(inx, {
                'display_type': 'line_section',
                'name': 'Uncategorized',
                'move_id': move_id.id,
                'sequence': sequence + inx,
            })
        return super().create(vals_list)
