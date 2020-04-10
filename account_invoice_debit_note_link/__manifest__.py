# Copyright 2004-2011 Pexego Sistemas Informáticos. (http://pexego.es)
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2014-2017 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2018-2019 Rosen Vladimirov <rv@dxfactory.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Link debit note invoice with original",
    "summary": "Link debit note invoice with its original invoice",
    "version": "11.0.1.0.0",
    "category": "Accounting & Finance",
    "website": "https://odoo-community.org/",
    "author": "Pexego, "
              "Tecnativa, "
              "Rosen Vladimirov, "
              "Odoo Community Association (OCA)",
    "installable": True,
    "post_init_hook": "post_init_hook",
    "depends": [
        'account',
        'l10n_bg',
    ],
    "license": "AGPL-3",
    "data": [
        'views/account_invoice_view.xml',
    ],
}
