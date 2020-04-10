# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Invoice sale order link",
    'version': '11.0.1.0.0',
    'category': 'Accounting & Finance',
    "author": "Rosen Vladimirov <vladimirov.rosen@gmail.com>, "
              "Bioprint Ltd. <http://www.bioprint.bg>",
    'website': 'https://github.com/rosenvladimirov/account-invoicing',
    'license': 'GPL-3',
    "depends": [
            'account'
            ],
    'data': [
            'views/account_invoice_view.xml'
            ],
    'installable': True,
}
