{
    'name': 'Adelanta - Niveles, Plazos y Pagos',
    'version': '2.5',
    'summary': 'Control de plazos de pago por nivel de usuario y vista de estados de pago.',
    'description': '''
        - Define niveles de usuario (Nivel 1, 2, 3)
        - Asocia plazos de pago a niveles
        - Aplica lógicas de pago inicial y cuotas
        - Muestra gráfico de cambios de estado de pago
    ''',
    'author': 'Sergio Rojas',
    # 'category': 'Accounting',
    'depends': ['sale_management','account_accountant','account', 'mail', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'data/adelanta_user_levels.xml',        
        'views/res_partner_view.xml',
        'views/account_payment_term.xml',
        'views/graph.xml',
    ],
    'application': True,
    'installable': True,
}
