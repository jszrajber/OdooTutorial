from odoo import models, fields, api


class Product(models.Model):
    # Parametres with _ is a model configuration, not DB column
    _name = "hello.product"     # Table name, will change to hello_product
    _description = 'My First Product'   # Metadata

    # Table fields
    name = fields.Char(required=True)
    price = fields.Float()
    active = fields.Boolean(default=True)
    category_id = fields.Many2one('hello.category', string="Category")  # Relation with Category model

    # 'compute' indicates the root function
    # 'store' saves result in db
    price_with_tax = fields.Float(compute='_compute_price_with_tax', store=True)

    # Without decorator method must be applied manually
    @api.depends("price")   # recount this field again when 'price' value changes, works like useEffect in React
    def _compute_price_with_tax(self):
        for record in self:     # In Odoo 'self' represents all products from this model
            record.price_with_tax = record.price * 1.23

    def apply_discount(self, percent):
        for record in self:
            record.price = record.price * (1 - percent / 100)

    @api.model_create_multi  # Decorator for multi dicts, Odoo convention
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            print(f"Product created: {record.name}")
        return records
