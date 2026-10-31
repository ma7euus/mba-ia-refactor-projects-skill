"""Product use cases independent of HTTP."""
class ProductController:
    def __init__(self, service):
        self.service = service

    def list(self):
        return self.service.all()

    def find(self, product_id):
        return self.service.find(product_id)

    def search(self, query):
        return self.service.search(query)

    def create(self, data):
        return self.service.create(data)

    def update(self, product_id, data):
        self.service.update(product_id, data)

    def delete(self, product_id):
        self.service.delete(product_id)
