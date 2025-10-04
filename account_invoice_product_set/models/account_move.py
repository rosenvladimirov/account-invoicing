#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, Command
from odoo.tools import groupby

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    product_set_ids = fields.Many2many('account.move.product.set',
                                       compute="_compute_product_set_ids",
                                       string="Product sets",
                                       store=True,)

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
            sale_line_ids = record.mapped('invoice_line_ids').mapped('sale_line_ids')

            if sale_line_ids:
                order_lines = sale_line_ids.sorted(lambda r: r.product_set_section_id.id).\
                    filtered(lambda r: r.product_set_section_id)

                for section_id, lines in groupby(order_lines, lambda r: r.product_set_section_id):
                    inv_line_section_ids[section_id] = lines

                for inx, lines in inv_line_section_ids.items():
                    sale_order_line_ids = self.env['sale.order.line']
                    for sale_order_line_id in lines:
                        sale_order_line_ids |= sale_order_line_id

                    product_set_section_id = sale_line_ids.filtered(lambda r: r.id == inx.id)
                    new_product_set_section_id = False
                    for invoice_line_id in record.mapped('invoice_line_ids'):
                        if product_set_section_id.id in invoice_line_id.mapped('sale_line_ids').ids:
                            new_product_set_section_id = invoice_line_id.id
                            # new_product_set_section_id.product_set_qty = product_set_section_id.product_set_qty
                            break

                    for invoice_line_id in record.mapped('invoice_line_ids').\
                        filtered(lambda r: r.id != new_product_set_section_id):
                        for sale_order_line_id in invoice_line_id.sale_line_ids:
                            if sale_order_line_id in sale_order_line_ids:
                                invoice_line_id.product_set_section_id = new_product_set_section_id

                #     for inv_line in invoice_line_ids.filtered(lambda r: r.display_type == 'line_section'):
                #         if section_id.id in inv_line.mapped('sale_line_ids').ids:
                #             inv_line_section_ids[inv_line] = [l.id for l in lines]
                # for inv_line in invoice_line_ids.filtered(lambda r: r.display_type != 'line_section'):
                #     for key, values in inv_line_section_ids.items():
                #         sale_line_ids = inv_line.mapped('sale_line_ids').ids
                #         for ln in values:
                #             if ln in sale_line_ids:
                #                 inv_line.product_set_section_id = key

            for product_set_section_id, lines in groupby(invoice_line_ids.sorted(lambda r: r.product_set_section_id.id),
                                                         key=lambda r: r.product_set_section_id):
                if not product_set_section_id:
                    continue
                product_set_id = product_set_section_id.product_set_id
                if product_set_id:
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

                    if not product_set_ids.get(product_set_id):
                        product_set_ids[product_set_id] = total_quantity
                    product_set_ids[product_set_id].update({
                        'amount': product_set_ids[product_set_id]['amount'] + total_quantity['amount'],
                        'section_quantity': product_set_ids[product_set_id]['section_quantity'] + total_quantity[
                            'section_quantity'],
                    })
                    # product_set_section_id.write(product_set_section_id._get_values_product_set_mixin(total_quantity))

            for product_set_id, total_quantity in product_set_ids.items():
                product_set_ids = self.env['account.move.product.set'].search([
                    ('move_id', '=', record.id),
                    ('product_set_id', '=', product_set_id.id)])
                if product_set_ids:
                    record.product_set_ids |= product_set_ids
                    product_set_ids.with_context(**dict(self._context, create_new_set=True)).write(
                        record.product_set_ids._get_account_move_product_set_value(
                            record,
                            product_set_id,
                            total_quantity['amount'],
                            total_quantity['section_quantity'] / total_quantity['quantity'],
                        )
                    )
                else:
                    record.product_set_ids |= self.env['account.move.product.set'].create(
                        record.product_set_ids._get_account_move_product_set_value(
                            record,
                            product_set_id,
                            total_quantity['amount'],
                            total_quantity['section_quantity'] / total_quantity['quantity'],
                        )
                    )

    def action_set_sections(self):
        compensation_product_id = self.with_company(self.env.company). \
            env.ref('product_set.compensation_product', raise_if_not_found=False).id
        for record in self:
            product_set_ids = {}
            record.invoice_line_ids.filtered(lambda r: r.display_type == 'line_section').with_context(**dict(self._context, create_new_set=True, force_delete=True)).unlink()
            self.env['account.move.product.set'].search([('move_id', '=', record.id)]).with_context(**dict(self._context, create_new_set=True)).unlink()
            values = {}
            add_sequence = add_no_set_sequence = sequence = 0
            no_set_sequence = 999

            invoice_line_ids = record.invoice_line_ids
            total_quantity = {}

            lines = record.invoice_line_ids.sorted(lambda r: r.product_set_id and r.product_set_id.id or 0)
            product_set_id = False
            for line in lines.\
                with_context(**dict(self._context, lang=record.partner_id.lang)).filtered(lambda r: r.product_set_id):
                sequence += 1
                if not total_quantity.get(line.product_set_id):
                    total_quantity[line.product_set_id] = {
                        'amount': 0.0,
                        'quantity': 1.0,
                        'section_quantity': 0.0,
                    }

                if line.product_set_id != product_set_id:
                    product_set_id = line.product_set_id
                    values[f'section_{line.id}'] = {
                        'display_type': 'line_section',
                        'product_set_id': line.product_set_id.id,
                        'name': line.product_set_id.display_name or _('Uncategorized'),
                        'move_id': record.id,
                        'sequence': sequence + add_sequence
                    }
                    quantity = sum([sl.quantity for sl in line.product_set_id.set_line_ids.
                                   filtered(lambda r: r.product_id.id == compensation_product_id)]) or 1.0
                    total_quantity[line.product_set_id].update({
                        'quantity': quantity,
                    })
                    add_sequence += 1
                values[f'line_{line.id}'] = {
                    'sequence': sequence + add_sequence,
                }
                if line.product_id.id != compensation_product_id:
                    total_quantity[line.product_set_id]['amount'] += line.price_subtotal
                if line.product_id.id == compensation_product_id:
                    total_quantity[line.product_set_id]['section_quantity'] += line.quantity

            for line in lines.filtered(lambda r: not r.product_set_id):
                no_set_sequence += 1
                if line.product_set_id != product_set_id:
                    product_set_id = line.product_set_id
                    values[f'section_{line.id}'] = {
                        'display_type': 'line_section',
                        'name': _('Uncategorized'),
                        'move_id': record.id,
                        'sequence': no_set_sequence + add_no_set_sequence
                    }
                    add_no_set_sequence += 1
                values[f'line_{line.id}'] = {
                    'sequence': no_set_sequence + add_no_set_sequence,
                }

            for line in record.invoice_line_ids:
                if values.get(f'section_{line.id}'):
                    if not values.get(line.product_set_id):
                        values[line.product_set_id] = {}
                    if total_quantity.get(line.product_set_id):
                        values[f'section_{line.id}'].update(line._get_values_product_set_mixin(total_quantity[line.product_set_id]))
                    values[line.product_set_id] = {
                        'product_set_section_id': record.with_context(**dict(self._context, create_new_set=True)).\
                            invoice_line_ids.create(values[f'section_{line.id}']).id
                    }

            for line in record.invoice_line_ids:
                if values.get(f'line_{line.id}'):
                    # _logger.info(f"values: {f'line_{line.id}'} {values[line.product_set_id]['product_set_section_id']}")
                    if line.product_set_id:
                        values[f'line_{line.id}'].update({'product_set_section_id': values[line.product_set_id]['product_set_section_id']})
                    # _logger.info(f"values: {values[f'line_{line.id}']}")
                    line.with_context(**dict(self._context, create_new_set=True)).write(values[f'line_{line.id}'])

            for line in record.invoice_line_ids.filtered(lambda r: r.product_set_id):
                product_set_ids = self.env['account.move.product.set'].search([
                    ('move_id', '=', record.id),
                    ('product_set_id', '=', line.product_set_id.id)])
                if product_set_ids:
                    record.product_set_ids |= product_set_ids
                    product_set_ids.with_context(**dict(self._context, create_new_set=True)).write(
                        record.product_set_ids._get_account_move_product_set_value(
                            record,
                            line.product_set_id,
                            total_quantity[line.product_set_id]['amount'],
                            total_quantity[line.product_set_id]['section_quantity'] / total_quantity[line.product_set_id]['quantity'],
                        )
                    )
                else:
                    record.product_set_ids |= self.env['account.move.product.set'].create(
                        record.product_set_ids._get_account_move_product_set_value(
                            record,
                            line.product_set_id,
                            total_quantity[line.product_set_id]['amount'],
                            total_quantity[line.product_set_id]['section_quantity'] / total_quantity[line.product_set_id]['quantity'],
                        )
                    )

    def unlink(self):
        for record in self:
            self.env['account.move.product.set'].search([('move_id', '=', record.id)]).with_context(**dict(self._context, create_new_set=True)).unlink()
        return super().unlink()
