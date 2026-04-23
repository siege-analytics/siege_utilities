"""Django app configuration for siege_utilities.geo.django."""

from django.apps import AppConfig


class SiegeGeoConfig(AppConfig):
    """Django app configuration for Census geographic data models."""

    name = "siege_utilities.geo.django"
    label = "siege_geo"
    verbose_name = "Siege Utilities - Geography"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Perform initialization when the app is ready."""
        # Import signals if needed
