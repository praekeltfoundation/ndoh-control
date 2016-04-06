from django.contrib import admin

from control.utils import CsvExportAdminMixin
from .models import Source, Registration


class RegistrationAdmin(CsvExportAdminMixin, admin.ModelAdmin):
    csv_header = [
        'id', 'mom_id_type', 'mom_passport_origin', 'mom_lang', 'mom_edd',
        'mom_dob', 'clinic_code', 'authority', 'created_at', 'updated_at']

    def clean_csv_line(self, model):
        return [
            model.id, model.mom_id_type, model.mom_passport_origin,
            model.mom_lang, model.mom_edd, model.mom_dob, model.clinic_code,
            model.authority, model.created_at, model.updated_at]


admin.site.register(Source)
admin.site.register(Registration, RegistrationAdmin)
