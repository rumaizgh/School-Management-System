from django_tenants.signals import post_schema_sync
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django_tenants.utils import tenant_context
from django.utils import timezone
from decouple import config

@receiver(post_schema_sync)
def create_default_admin(sender, tenant, **kwargs):
    # Do not run when migrating the public schema
    if tenant.schema_name == 'public':
        return

    User = get_user_model()

    # Sync default admin to the newly created tenant schema
    with tenant_context(tenant):
        if not User.objects.filter(is_superuser=True).exists():
            from apps.academics.models import Institute
            
            # Get the default institute created by migration 0004 and rename it to the tenant's name
            default_institute = Institute.objects.first()
            if default_institute:
                if default_institute.name == 'Default Institute':
                    default_institute.name = tenant.name
                    default_institute.save(update_fields=['name'])
            else:
                default_institute = Institute.objects.create(
                    name=tenant.name,
                    address='Default Address',
                    established_date=timezone.now().date(),
                    logo=''
                )
            
            email = config('SUPERUSER_EMAIL', default='admin@talent.com')
            password = config('SUPERUSER_PASSWORD', default='adminpassword')
            
            User.objects.create_superuser(
                email=email,
                password=password,
                name='Super Admin',
                phone='0000000000',
                user_type='admin',
                institute=default_institute
            )
