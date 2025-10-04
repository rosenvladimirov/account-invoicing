# Copyright 2015 Anybox S.A.S
# Copyright 2016-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ProductSetLine(models.Model):
    _inherit = "product.set.line"

    def prepare_account_move_line_values(self, move, quantity, max_sequence=0):
        self.ensure_one()
        return {
            "move_id": move.id,
            "product_set_id": self.product_set_id.id,
            "product_id": self.product_id.id,
            "quantity": self.quantity * quantity,
            "product_uom_id": self.product_id.uom_id.id,
            "sequence": max_sequence + self.sequence,
            "discount": self.discount,
            # "company_id": self.company_id.id,
            "product_set_line_id": self.id
        }
