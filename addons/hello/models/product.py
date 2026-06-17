from odoo import models, fields


class Product(models.Model):
    # Parametres with _ is a model configuration, not DB column
    _name = "hello.product"     # Table name, will change to hello_product
    _description = 'My First Product'   # Metadata

    # Table fields
    name = fields.Char(required=True)
    price = fields.Float()
    active = fields.Boolean(default=True)