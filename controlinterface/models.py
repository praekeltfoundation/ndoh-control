from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# Modelled on https://github.com/jamesmarlowe/django-AutoDateTimeFields
# But with timezone support
class AutoDateTimeField(models.DateTimeField):

    def pre_save(self, model_instance, add):
        now = timezone.now()
        setattr(model_instance, self.attname, now)
        return now


class AutoNewDateTimeField(models.DateTimeField):

    def pre_save(self, model_instance, add):
        if not add:
            return getattr(model_instance, self.attname)
        now = timezone.now()
        setattr(model_instance, self.attname, now)
        return now


class WidgetData(models.Model):

    """ Metric a widget has data from
    """
    DATA_SOURCES = (
        ('vumi', 'Vumi Go'),
        ('influxdb', 'InfluxDB'),
    )
    DATA_TYPES = (
        ('private', 'Private'),
        ('public', 'Public'),
        ('summary', 'Summary'),
    )
    title = models.CharField(max_length=200)
    key = models.CharField(max_length=200)
    source = models.CharField(max_length=10, choices=DATA_SOURCES)
    data_type = models.CharField(max_length=10, choices=DATA_TYPES)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    class Meta:
        verbose_name = 'widget data'
        verbose_name_plural = 'widget data sources'

    def __unicode__(self):
        return "%s (%s)" % (self.title, self.key)


class Widget(models.Model):

    """ Metric a widget has data from
    """
    WIDGET_TYPES = (
        ('bars', 'Bar Graph'),
        ('last', 'Last'),
        ('lines', 'Lines'),
        ('pie', 'Pie Chart'),
    )
    SHOW_NULLS = (
        ('omit', 'Omit'),
    )
    title = models.CharField(max_length=200)
    type_of = models.CharField(max_length=10, choices=WIDGET_TYPES)
    data_from = models.CharField(max_length=20)
    interval = models.CharField(max_length=20)
    nulls = models.CharField(max_length=20, choices=SHOW_NULLS, null=True, blank=True)
    data = models.ManyToManyField(WidgetData, null=True, blank=True,)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    class Meta:
        verbose_name = 'widget'
        verbose_name_plural = 'widgets'

    def __unicode__(self):
        return "%s (%s)" % (self.title, self.type_of)


class Dashboard(models.Model):

    """ Base Dashboard config that Widgets are collected into
    """
    DASHBOARD_TYPES = (
        ('private', 'Private'),
        ('public', 'Public'),
        ('summary', 'Summary'),
    )
    name = models.CharField(max_length=200)
    widgets = models.ManyToManyField(Widget, null=True, blank=True,)
    dashboard_type = models.CharField(max_length=10, choices=DASHBOARD_TYPES)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    def __unicode__(self):
        return "%s" % self.name

    class Meta:
        verbose_name = 'dashboard'
        verbose_name_plural = 'dashboards'
        permissions = (
            ("view_dashboard_private", "Can see all private dashboard data"),
            ("view_dashboard_public", "Can see all public dashboard data"),
            ("view_dashboard_summary", "Can see all summary dashboard data"),
        )


class UserDashboard(models.Model):

    """ Dashboards a user is interested in
    """
    #: the :class:`django.contrib.auth.models.User` this dashboard is a profile for
    user = models.OneToOneField('auth.User')
    dashboards = models.ManyToManyField(Dashboard, related_name='dashboards')
    default_dashboard = models.ForeignKey(Dashboard, related_name='default')
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    class Meta:
        verbose_name = 'user dashboard'
        verbose_name_plural = 'users dashboards'

    def __unicode__(self):
        return "%s %s (%s)" % (self.user.first_name, self.user.last_name, self.user.email)



from south.modelsinspector import add_introspection_rules
add_introspection_rules(
    [], ["^controlinterface\.models\.AutoNewDateTimeField",
         "^controlinterface\.models\.AutoDateTimeField"])
