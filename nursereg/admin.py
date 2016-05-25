from django.contrib import admin
from control.utils import CsvExportAdminMixin

from .models import NurseSource, NurseReg


class NurseRegAdmin(CsvExportAdminMixin, admin.ModelAdmin):
    csv_header = [
        'cmsisdn', 'dmsisdn', 'rmsisdn', 'faccode',
        'id_type', 'id_no', 'passport_origin', 'dob',
        'nurse_source', 'persal_no', 'opted_out',
        'optout_reason', 'optout_count', 'sanc_reg_no',
        'created_at', 'updated_at']

    def clean_csv_line(self, model):
        return [
            model.cmsisdn, model.dmsisdn, model.rmsisdn, model.faccode,
            model.id_type, model.id_no, model.passport_origin, model.dob,
            model.nurse_source, model.persal_no, model.opted_out,
            model.optout_reason, model.optout_count, model.sanc_reg_no,
            model.created_at, model.updated_at]

admin.site.register(NurseSource)
admin.site.register(NurseReg, NurseRegAdmin)
