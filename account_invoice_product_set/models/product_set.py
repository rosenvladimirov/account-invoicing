#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, tools, api, _, Command, SUPERUSER_ID


class ProductSet(models.Model):
    _inherit = "product.set"

    def prepare_account_move_values(self, sequence):
        self.ensure_one()
        return {
            "sequence": sequence,
            "name": self.display_name,
            "product_set_id": self.id,
            "display_type": 'line_section',
        }
