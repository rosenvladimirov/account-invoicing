##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2018 Serpent Consulting Services Pvt. Ltd.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        if self._context.get('currency_id'):
            return self.env['res.currency'].browse(
                self._context.get('currency_id'))
        return journal.currency_id or journal.company_id.currency_id or \
            self.env.user.company_id.currency_id

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            if self._context.get('currency_id'):
                self.currency_id = self._context.get('currency_id')
            else:
                self.currency_id = self.journal_id.currency_id.id or \
                               self.journal_id.company_id.currency_id.id

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, readonly=True,
                                  states={'draft': [('readonly', False)]},
                                  default=_default_currency,
                                  track_visibility='always')
