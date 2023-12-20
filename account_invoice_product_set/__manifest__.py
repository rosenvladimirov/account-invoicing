# Copyright 2023 Rosen Vladimirov, BioPrint Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Account Invoice Product Set',
    'summary': """
        Add product sets support on invoices.""",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov, BioPrint Ltd.,Odoo Community Association (OCA)',
    'website': 'https://github.com/oca/account-invoicing',
    'depends': [
        'product_set',
        'sale_product_set',
        'account',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_set_add.xml',
        'views/account_move_views.xml',
    ],
    'demo': [
    ],
    'post_init_hook': 'post_init_hook',
}
