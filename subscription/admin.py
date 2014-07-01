from django.contrib import admin
from subscription.models import MessageSet, Message, Subscription

admin.site.register(MessageSet)
admin.site.register(Message)
admin.site.register(Subscription)
