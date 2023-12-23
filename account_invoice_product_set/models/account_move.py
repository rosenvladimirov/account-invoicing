#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, Command
from odoo.tools import groupby

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    product_set_ids = fields.Many2many('account.move.product.set',
                                       compute="_compute_product_set_ids",
                                       string="Product sets")

    @api.depends('invoice_line_ids')
    def _compute_product_set_ids(self):
        compensation_product_id = self.with_company(self.env.company). \
            env.ref('product_set.compensation_product', raise_if_not_found=False).id
        for record in self:
            record.product_set_ids = False
            product_set_ids = {}
            inv_line_section_ids = {}

            if not record.id:
                continue

            invoice_line_ids = record.invoice_line_ids
            if not invoice_line_ids.mapped('product_set_section_id'):
                order_lines = invoice_line_ids.mapped('sale_line_ids').sorted(lambda r: r.product_set_section_id.id)
                for section_id, lines in groupby(order_lines, lambda r: r.product_set_section_id):
                    for inv_line in invoice_line_ids.filtered(lambda r: r.display_type == 'line_section'):
                        if section_id.id in inv_line.mapped('sale_line_ids').ids:
                            inv_line_section_ids[inv_line] = [l.id for l in lines]
                for inv_line in invoice_line_ids.filtered(lambda r: r.display_type != 'line_section'):
                    for key, values in inv_line_section_ids.items():
                        sale_line_ids = inv_line.mapped('sale_line_ids').ids
                        for ln in values:
                            # _logger.info(f"inv_line {ln} in {sale_line_ids} for {key}")
                            if ln in sale_line_ids:
                                inv_line.product_set_section_id = key

            for product_set_section_id, lines in groupby(invoice_line_ids.sorted(lambda r: r.product_set_section_id.id),
                                                         key=lambda r: r.product_set_section_id):
                if not product_set_section_id:
                    continue
                product_set_id = product_set_section_id.product_set_id
                quantity = sum([sl.quantity for sl in product_set_id.set_line_ids.
                               filtered(lambda r: r.product_id.id == compensation_product_id)]) or 1.0

                total_quantity = {
                    'amount': 0.0,
                    'quantity': quantity,
                    'section_quantity': 0.0,
                }
                for invoice_line_id in lines:
                    total_quantity['amount'] += invoice_line_id.price_subtotal
                    if invoice_line_id.product_id.id == compensation_product_id:
                        total_quantity['section_quantity'] += invoice_line_id.quantity
                product_set_section_id.write(product_set_section_id._get_values_product_set_mixin(total_quantity))

                if not product_set_ids.get(product_set_id):
                    product_set_ids[product_set_id] = {
                        'amount': 0.0,
                        'quantity': quantity,
                        'section_quantity': 0.0,
                    }
                product_set_ids[product_set_id].update({
                    'amount': product_set_ids[product_set_id]['amount'] + total_quantity['amount'],
                    'section_quantity': product_set_ids[product_set_id]['section_quantity'] + total_quantity[
                        'section_quantity'],
                })

            for product_set_id, total_quantity in product_set_ids.items():
                record.product_set_ids |= self.env['account.move.product.set'].create(
                    record.product_set_ids._get_account_move_product_set_value(
                        record,
                        product_set_id,
                        total_quantity['amount'],
                        total_quantity['section_quantity'] / total_quantity['quantity'],
                    )
                )
