# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Invoice Digitized Signature",
    "version" : "11.0.1.0",
    "author" : "Rosen Vladimirov",
    'category': 'Accounting & Finance',
    "website": "https://github.com/rosenvladimirov/account-invoicing",
    "description": """
Sing invoice with Digitized Signature
    """,
    'depends': [
        'account',
    ],
    "demo" : [],
    "data" : [
        'views/account_invoice_view.xml',
              ],
    'license': 'AGPL-3',
    "installable": True,
}
