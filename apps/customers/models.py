from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

class Client(TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)

    # Automatically create the schema and run migrations when a client is created
    auto_create_schema = True

    def __str__(self):
        return f"{self.name} ({self.schema_name})"

class Domain(DomainMixin):
    def __str__(self):
        return self.domain
