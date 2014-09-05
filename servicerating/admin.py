from django.contrib import admin
from servicerating.models import Contact, Conversation, Response, UserAccount, Extra
from control.actions import export_select_fields_csv_action


class ContactAdmin(admin.ModelAdmin):
    actions = [export_select_fields_csv_action(
        "Export selected objects as CSV file",
        fields = [
            ("contact", "Contact"),
            ("key", "Key"),
            ("value", "Value"),
            ("msisdn", "MSISDN"),
            ("created_at", "Created At"),
            ("updated_at", "Updated At"),
        ],
        header=True
        )]


class ConversationAdmin(admin.ModelAdmin):
    actions = [export_select_fields_csv_action(
        "Export selected objects as CSV file",
        fields = [
            ("user_account", "User Account"),
            ("key", "Key"),
            ("name", "Name"),
            ("notes", "Notes"),
            ("created_at", "Created At"),
            ("updated_at", "Updated At"),
        ],
        header=True
        )]


class UserAccountAdmin(admin.ModelAdmin):
    actions = [export_select_fields_csv_action(
        "Export selected objects as CSV file",
        fields = [
            ("key", "Key"),
            ("name", "Name"),
            ("notes", "Notes"),
            ("created_at", "Created At"),
            ("updated_at", "Updated At"),
        ],
        header=True
        )]


class ExtraAdmin(admin.ModelAdmin):
    actions = [export_select_fields_csv_action(
        "Export selected objects as CSV file",
        fields = [
            ("contact", "Contact"),
            ("key", "Key"),
            ("value", "Value"),
            ("created_at", "Created At"),
            ("updated_at", "Updated At"),
        ],
        header=True
        )]


admin.site.register(Contact, ContactAdmin)
admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Response)
admin.site.register(UserAccount, UserAccountAdmin)
admin.site.register(Extra, ExtraAdmin)
