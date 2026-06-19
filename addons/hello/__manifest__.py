{
    "name": 'Hello',
    'version': '1.0',
    'depends': ['base'],    # Which modules must be installed before mine
    'data': [
        'security/ir.model.access.csv',     # Let's all users see my module data
        'views/product_views.xml'
        ],
    'installable': True,
}

