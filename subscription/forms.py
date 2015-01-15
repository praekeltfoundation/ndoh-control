from django import forms
from subscription.models import MessageSet
from subscription.tasks import ingest_csv, ingest_opt_opts_csv
from StringIO import StringIO

class CSVUploader(forms.Form):
    csv = forms.FileField()
    message_set = forms.ModelChoiceField(queryset=MessageSet.objects.all())
    def save(self):
        csv_data = StringIO(self.cleaned_data["csv"].read())
        ingest_csv.delay(csv_data, self.cleaned_data["message_set"])


class OptOutCSVUploader(forms.Form):
    csv = forms.FileField()
    def save(self):
        csv_data = StringIO(self.cleaned_data["csv"].read())
        ingest_opt_opts_csv.delay(csv_data)
