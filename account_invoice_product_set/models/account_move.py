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
            _logger.info(f"INVOICE LINE {record}:{record.invoice_line_ids}")
            record.product_set_ids = False
            if not record.id:
                continue

            for product_set_id, lines in groupby(record.invoice_line_ids.sorted(lambda r: r.product_set_id.id),
                                                 key=lambda r: r.product_set_id):
                if not product_set_id:
                    continue
                # line_product_set_id = product_set_id
                quantity = sum([l.quantity for l in product_set_id.set_line_ids.filtered(lambda r: r.product_id.id == compensation_product_id)]) or 1.0
                total_quantity = [0.0] * 2
                for invoice_line_id in lines:
                    total_quantity[1] += invoice_line_id.price_subtotal
                    if invoice_line_id.product_id.id == compensation_product_id:
                        total_quantity[0] += invoice_line_id.quantity

                _logger.info(f"VALUES {record}:{lines}:{product_set_id}:{total_quantity}:{quantity}")
                record.product_set_ids |= self.env['account.move.product.set'].create(
                    self.env['account.move.product.set']._get_account_move_product_set_value(
                        record,
                        product_set_id,
                        total_quantity[1],
                        total_quantity[0]/quantity,
                    ))
                # record.product_set_ids |= sale_product_set
