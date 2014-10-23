from django.db import models

class Dashboard(models.Model):
    pass


    class Meta:
        permissions = (
            ("view_dashboard_private", "Can see all private dashboard data"),
            ("view_dashboard_public", "Can see all public dashboard data"),
            ("view_dashboard_summary", "Can see all summary dashboard data"),
        )

class Widget(models.Model):
    pass

