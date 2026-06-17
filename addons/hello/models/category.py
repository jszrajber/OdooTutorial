from odoo import models, fields, api


class Category(models.Model):
    _name = "hello.category"
    _description = "Product category"

    name = fields.Char(required=True)
