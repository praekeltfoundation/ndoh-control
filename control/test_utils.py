from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

import csv


class AdminCsvDownloadBase(TestCase):
    path = None
    cls = None

    def setUp(self):
        self.user = User.objects.create_superuser(
            'admin', 'admin@example.org', 'admin')
        self.client.login(username='admin', password='admin')

    def get_csv(self):
        '''Returns a list of lists that represent each row  of the csv.'''
        r = self.client.get(reverse(
            '%s_actions' % self.path, args=['export_csv']))
        content = csv.reader(r.streaming_content)
        header = content.next()
        self.assertEqual(header, self.cls.csv_header)
        return sorted(content, key=lambda l: int(l[0]))

    def assert_download_button_present(self):
        r = self.client.get(reverse(
            '%s_changelist' % self.path))
        self.assertContains(
            r, '<a href="%s" title="Download an export of the data as CSV"'
            ' class="">Download</a>' % reverse(
                '%s_actions' % self.path,
                args=['export_csv']),
            html=True)
