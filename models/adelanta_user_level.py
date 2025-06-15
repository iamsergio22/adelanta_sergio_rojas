# models/adelanta_user_level.py

from odoo import models, fields

class AdelantaUserLevel(models.Model):
    _name = 'adelanta.user.level'
    _description = 'Nivel de Usuario'

    name = fields.Char(string='Nombre del Nivel', required=True)
    code = fields.Selection([
        ('nivel_1', 'Nivel 1'),
        ('nivel_2', 'Nivel 2'),
        ('nivel_3', 'Nivel 3'),
    ], string='Código', required=True, unique=True)
