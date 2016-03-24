from django.contrib import admin
from subscription.models import MessageSet, Message, Subscription
from control.utils import CsvExportAdminMixin


class SubscriptionAdmin(CsvExportAdminMixin, admin.ModelAdmin):
    list_display = [
        "contact_key", "to_addr", "message_set", "next_sequence_number",
        "lang", "active", "completed", "created_at", "updated_at",
        "schedule", "process_status"]
    search_fields = ["contact_key", "to_addr"]
    csv_header = [
        'id', 'user_account', 'contact_key', 'message_set',
        'next_sequence_number', 'lang', 'active', 'completed', 'created_at',
        'updated_at', 'schedule', 'process_status']

    def clean_csv_line(self, model):
        return [
            model.id, model.user_account, model.contact_key,
            model.message_set.id, model.next_sequence_number, model.lang,
            model.active, model.completed, model.created_at, model.updated_at,
            model.schedule.id, model.process_status]


class MessageAdmin(CsvExportAdminMixin, admin.ModelAdmin):
    csv_header = [
        'id', 'message_set', 'sequence_number', 'lang', 'content', 'created_at',
        'updated_at']

    def clean_csv_line(self, model):
        return [
            model.id, model.message_set.id, model.sequence_number, model.lang,
            model.content, model.created_at, model.updated_at]

admin.site.register(MessageSet)
admin.site.register(Message, MessageAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
