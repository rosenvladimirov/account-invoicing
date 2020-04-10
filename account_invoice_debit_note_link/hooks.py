# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2017-2018 Tecnativa - Pedro M. Baeza
# Copyright 2018-2029 Rosen Vladimirov <rv@dxfactory.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def match_origin_lines(debit_note):
    """Try to match lines by product or by description."""
    invoice = debit_note.debitnote_invoice_id
    invoice_lines = invoice.invoice_line_ids
    for debit_note_line in debit_note.invoice_line_ids:
        for invoice_line in invoice_lines:
            match = (
                debit_note_line.product_id and
                debit_note_line.product_id == invoice_line.product_id or
                debit_note_line.name == invoice_line.name
            )
            if match:
                invoice_lines -= invoice_line
                debit_note_line.origin_dn_line_ids = [(6, 0, invoice_line.ids)]
                break
        if not invoice_lines:
            break


def post_init_hook(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        # Linking all debit note invoices to its original invoices
        debit_notes = env['account.invoice'].search([
            ('sub_type', 'in', ('out_debitnote', 'in_debitnote')),
            ('debitnote_invoice_id', '!=', False),
        ])
        for debit_note in debit_notes:
            match_origin_lines(debit_note)
