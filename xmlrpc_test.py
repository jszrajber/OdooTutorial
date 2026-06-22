import xmlrpc.client

# Odoo variables
url = 'http://localhost:8069/'
db = 'mydb'
username = 'test@gmail.com'
password = 'Testing.123'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))    # Authentication first
print(common.version())

uid = common.authenticate(db, username, password, {})
print(uid)


models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))    # Filtering DB
result = models.execute_kw(db, uid, password, 'hello.product', 'search_read', [[["name", "=", "Laptop"]]], {'fields': ['name', 'price']})   # Operations on Odoo DB

print(result)