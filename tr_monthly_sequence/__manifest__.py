# -*- coding: utf-8 -*-

{
    'name': "Trinity Roots - Monthly Sequence",
    'summary': "Monthly reset sequence",
    'description': """
        This module will reset the sequences when the new month comes.
        Have to pass the context['date'] to get sequence method
        for each getting sequence.
    """,
    'author': "Trinity Roots",
    'category': 'Usability',
    'version': '1.0',
    'depends': [
        'base',
        'tr_core_update',
    ],
    'data': [
        'views/ir_sequence_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
