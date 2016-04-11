import csv
from datetime import datetime
import itertools

from django.http import StreamingHttpResponse
from django_object_actions import DjangoObjectActions


class Echo(object):
    '''An object that implements just the write method of the file-like
    interface.'''
    def write(self, value):
        '''Write the value by returning it, instead of storing it in a
        buffer.'''
        return value


class CsvExportAdminMixin(DjangoObjectActions):
    '''A mix-in class for adding a CSV export button to a Django Admin page.'''
    csv_header = None

    def clean_csv_line(self, obj):
        '''Subclass to override. Gets a model object, and returns a list
        representing a line in the CSV file.'''

    def get_csv_header(self):
        '''Subclass can override. Returns a list representing the header of the
        CSV. Can also set the `csv_header` class variable.'''
        return self.csv_header

    def _encode_csv_line(self, line):
        return [unicode(item).encode('utf-8') for item in line]

    def export_csv(self, request, queryset):
        rows = itertools.chain(
            (self.get_csv_header(), ),
            (
                self._encode_csv_line(self.clean_csv_line(obj))
                for obj in queryset.iterator()
            )
        )
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        response = StreamingHttpResponse(
            (writer.writerow(row) for row in rows),
            content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s-%s.csv' % (
            self.model.__name__, datetime.now().strftime('%Y-%m-%d'))

        return response
    export_csv.label = "Download"
    export_csv.short_description = "Download an export of the data as CSV"

    changelist_actions = ('export_csv', )
