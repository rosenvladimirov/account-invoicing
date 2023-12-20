# Copyright 2023 BioPrint Ltd.
# Copyright 2015 Anybox S.A.S
# Copyright 2016-2020 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, api, exceptions, fields, models


class InvoiceProductSetAdd(models.TransientModel):
    _name = "invoice.product.set.add"
    _rec_name = "product_set_id"
    _description = "Wizard model to add product set into a invoice"

    move_id = fields.Many2one(
        "account.move",
        "Invoice",
        required=True,
        default=lambda self: self.env.context.get("active_id")
        if self.env.context.get("active_model") == "account.move"
        else None,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(related="move_id.partner_id", ondelete="cascade")
    product_set_id = fields.Many2one(
        "product.set", "Product set", required=True, ondelete="cascade"
    )
    product_set_line_ids = fields.Many2many(
        "product.set.line",
        string="Product set lines",
        required=True,
        store=True,
        ondelete="cascade",
        compute="_compute_product_set_line_ids",
        readonly=False,
    )
    quantity = fields.Float(
        digits="Product Unit of Measure", required=True, default=1.0
    )
    skip_existing_products = fields.Boolean(
        default=False,
        help="Enable this to not add new lines "
        "for products already included in Invoice lines.",
    )

    @api.depends_context("product_set_add__set_line_ids")
    @api.depends("product_set_id")
    def _compute_product_set_line_ids(self):
        line_ids = self.env.context.get("product_set_add__set_line_ids", [])
        lines_from_ctx = self.env["product.set.line"].browse(line_ids)
        for rec in self:
            if rec.product_set_line_ids:
                # Passed on creation
                continue
            lines = lines_from_ctx.filtered(
                lambda x: x.product_set_id == rec.product_set_id
            )
            if lines:
                # Use the ones from ctx but make sure they belong to the same set.
                rec.product_set_line_ids = lines
            else:
                # Fallback to all lines from current set
                rec.product_set_line_ids = rec.product_set_id.set_line_ids

    def _check_partner(self):
        """Validate order partner against product set's partner if any."""
        if not self.product_set_id.partner_id or self.env.context.get(
            "product_set_add_skip_validation"
        ):
            return

        allowed_partners = self._allowed_order_partners()
        if self.move_id.partner_id not in allowed_partners:
            raise exceptions.ValidationError(
                _(
                    "You can use a sale order assigned "
                    "only to following partner(s): {}"
                ).format(", ".join(allowed_partners.mapped("name")))
            )

    def _allowed_order_partners(self):
        """Product sets' partners allowed for current sale order."""
        partner_ids = self.env.context.get("allowed_order_partner_ids")
        if partner_ids:
            return self.env["res.partner"].browse(partner_ids)
        return self.product_set_id.partner_id

    def add_set(self):
        """Add product set, multiplied by quantity in sale order line"""
        self._check_partner()
        invoice_lines = self._prepare_order_lines()
        if invoice_lines:
            self.move_id.write({"invoice_line_ids": invoice_lines})
        return invoice_lines

    def _prepare_order_lines(self):
        max_sequence = self._get_max_sequence()
        invoice_lines = []
        invoice_lines.append((0, 0, self.product_set_id.prepare_account_move_values(max_sequence + 1)))
        for seq, set_line in enumerate(self._get_lines(), start=1):
            values = self.prepare_account_move_line_data(set_line)
            # When we play with sequence widget on a set of product,
            # it's possible to have a negative sequence.
            # In this case, the line is not added at the correct place.
            # So we have to force it with the invoice for the line.
            values.update({"sequence": max_sequence + 1 + seq})
            invoice_lines.append((0, 0, values))
        return invoice_lines

    def _get_max_sequence(self):
        max_sequence = 0
        if self.move_id.invoice_line_ids:
            max_sequence = max(line.sequence for line in self.move_id.invoice_line_ids)
        return max_sequence

    def _get_lines(self):
        # hook here to take control on used lines
        inv_product_ids = self.move_id.invoice_line_ids.mapped("product_id").ids
        for set_line in self.product_set_line_ids:
            if self.skip_existing_products and set_line.product_id.id in inv_product_ids:
                continue
            yield set_line

    def prepare_account_move_line_data(self, set_line, max_sequence=0):
        self.ensure_one()
        line_values = set_line.prepare_account_move_line_values(
            self.move_id, self.quantity, max_sequence=max_sequence
        )
        if set_line.display_type:
            line_values.update(
                {"name": set_line.name, "display_type": set_line.display_type}
            )

        return line_values
