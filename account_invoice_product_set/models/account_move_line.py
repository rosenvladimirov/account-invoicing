#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = ['account.move.line', 'product.set.mixin']

    product_set_section_id = fields.Many2one('account.move.line', string='Account Product Set Section')

    def _get_values_product_set_mixin(self, total_quantity):
        return self._get_update_product_set_section_values(total_quantity)

    @api.model_create_multi
    def create(self, vals_list):
        if not self._context.get('create_new_set'):
            inx = None
            move_id = False
            sequence = 0
            for sequence_inx, vals in enumerate(vals_list):
                move_id = self.env['account.move'].search([('id', '=', vals['move_id'])], limit=1)
                if move_id.invoice_line_ids:
                    last_section_id = move_id.invoice_line_ids[-1]
                    sequence = last_section_id.sequence
                    vals.update({'sequence': sequence + 2 + sequence_inx})
                    product_set_id = last_section_id.product_set_id
                    if product_set_id:
                        set_line_ids = product_set_id.set_line_ids
                        if vals.get('product_id') in set_line_ids.mapped('product_id').ids:
                            product_set_line_id = set_line_ids. \
                                filtered(lambda p: p.product_id.id == vals.get('product_id'))
                            vals.update({
                                'product_set_id': product_set_id.id,
                                'product_set_line_id': product_set_line_id.id,
                                'product_set_section_id': last_section_id.id,
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

    def unlink(self):
        for record in self:
            product_set_section_id = record
            for move_id in record.mapped('move_id'):
                invoice_line_ids = move_id.invoice_line_ids. \
                               filtered(lambda r: r.product_set_section_id.id == product_set_section_id.id)
                for line in invoice_line_ids:
                    line.unlink()
        return super().unlink()
