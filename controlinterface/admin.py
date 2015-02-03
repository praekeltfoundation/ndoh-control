from django.contrib import admin
from controlinterface.models import (
    Dashboard, Widget, WidgetData, UserDashboard)


admin.site.register(Dashboard)
admin.site.register(Widget)
admin.site.register(WidgetData)
admin.site.register(UserDashboard)
