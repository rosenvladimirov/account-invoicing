# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends('currency_id', 'company_currency_id')
    def _compute_has_currency(self):
        self.has_currency = self.currency_id != self.company_currency_id

    has_currency = fields.Boolean(compute=_compute_has_currency)


class AccountInvoice(models.Model):
    _inherit = "account.invoice.line"

    @api.one
    @api.depends('currency_id', 'company_currency_id')
    def _compute_has_currency(self):
        self.has_currency = self.currency_id != self.company_currency_id

    has_currency = fields.Boolean(compute=_compute_has_currency)
