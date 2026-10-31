class SystemController:
    def __init__(self, model, reports, admin):
        self.model, self.reports, self.admin = model, reports, admin

    def health(self):
        return self.model.health()

    def sales(self):
        return self.reports.sales()

    def query(self, data):
        return self.admin.query(data)

    def reset(self, data):
        self.admin.reset(data)
