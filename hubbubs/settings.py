from django.conf import settings


USE_SSL = getattr(settings, 'HUBBUBS_USE_SSL', False)
LEASE_SECONDS = getattr(settings, 'HUBBUBS_LEASE_SECONDS', None)
