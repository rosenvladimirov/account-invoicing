# Copyright 2004-2011 Pexego Sistemas Informáticos. (http://pexego.es)
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2014-2018 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2018-2029 Rosen Vladimirov <rv@dxfactory.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    debit_note_reason = fields.Text(string="Debit note reason")
    has_debit_note = fields.Boolean(compute="_compute_has_debit_note")

    @api.multi
    def _compute_has_debit_note(self):
        for record in self:
            record.has_debit_note = len(record.debitnote_invoice_ids.ids) > 0

    @api.model
    def _prepare_debit_note(self, invoice, date_invoice=None, date=None,
                        description=None, journal_id=None):
        """Add link in the debit note to the origin invoice lines."""
        res = super(AccountInvoice, self)._prepare_debit_note(
            invoice, date_invoice=date_invoice, date=date,
            description=description, journal_id=journal_id,
        )
        res['debit_note_reason'] = description
        debit_note_lines_vals = res['invoice_line_ids']
        for i, line in enumerate(invoice.invoice_line_ids):
            if i + 1 > len(debit_note_lines_vals):  # pragma: no cover
                # Avoid error if someone manipulate the original method
                break
            debit_note_lines_vals[i][2]['origin_dn_line_ids'] = [(6, 0, line.ids)]
        return res

    @api.onchange('debitnote_invoice_id')
    def _onchange_refund_invoice_id(self):
        for i, line in enumerate(self.invoice_line_ids):
            self.origin_dn_line_ids = [(6, False, line.ids)]


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    origin_dn_line_ids = fields.Many2many(
        comodel_name='account.invoice.line', column1='debit_note_line_id',
        column2='original_line_id', string="Original invoice line",
        relation='account_invoice_line_dn_rel',
        help="Original invoice line to which this debit note invoice line "
             "is corrected to",
        copy=False,
    )
    debit_note_line_ids = fields.Many2many(
        comodel_name='account.invoice.line', column1='original_line_id',
        column2='debit_note_line_id', string="Debit note invoice line",
        relation='account_invoice_line_dn_rel',
        help="Debit note invoice lines created from this invoice line",
        copy=False,
    )
