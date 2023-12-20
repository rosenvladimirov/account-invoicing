#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for line in env['account.move.line'].search([]):
        for sale_order_line in line.sale_line_ids:
            line.write({
                'product_set_id': sale_order_line.product_set_id.id,
                'product_set_line_id': sale_order_line.product_set_line_id.id
            })
