from odoo import api, models, fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    customer_signature = fields.Binary(
        string='Customer acceptance',
    )

    @api.model
    def create(self, values):
        sale = super(AccountInvoice, self).create(values)
        if sale.customer_signature:
            values = {'customer_signature': sale.customer_signature}
            sale._track_signature(values, 'customer_signature')
        return sale

    @api.multi
    def write(self, values):
        self._track_signature(values, 'customer_signature')
        return super(AccountInvoice, self).write(values)
