# -*- coding: utf-8 -*-
{
    'name': "Technical Service",

    'summary': """
        Manage Technical Service for different companies and creates Invoices automatically""",

    'description': """
        Close in spirit to Maintenance module but in this case just for external actions. You can create and manage Technical Services
        teams and assign them task to be completed throug different stages. At the final stage an Invoice is automatically generated 
        taking into account the amount of time spent in the service and the posibility of extra cost caused by the replacement of pieces
        during the reparation.
    """,

    'author': "Moreno J. David",
    'website': "https://stackoverflow.com/users/story/9693357",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'After-Sales',
    'version': '0.1',
    'application': True,
    'installable': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'maintenance', 'account'],

    # always loaded
    'data': [
        'security/technical_service_security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'data/data.xml',
        'wizard/wizards.xml',
        'views/menuitems.xml',
        'views/assets.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'css': ['static/src/css/styles.css'],
}