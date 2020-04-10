# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Invoice company currency",
    'version': '11.0.1.0.0',
    'category': 'Accounting & Finance',
    "author": "Rosen Vladimirov <vladimirov.rosen@gmail.com>, "
              "dXFactory Ltd. <http://www.dxfactory.eu>",
    'website': 'https://github.com/rosenvladimirov/account-invoicing',
    'license': 'AGPL-3',
    "depends": [
            'account'
            ],
    'data': [
            'views/account_invoice_view.xml'
            ],
    'installable': True,
}
