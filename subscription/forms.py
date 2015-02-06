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

LANG_CHOICES = [
    ('en', 'en'),
    ('af', 'af'),
    ('zu', 'zu'),
    ('xh', 'xh'), 
    ('ve', 've'), 
    ('tn', 'tn'),
    ('ts', 'ts'),
    ('ss', 'ss'),
    ('st', 'st'),
    ('nso', 'nso'),
    ('nr', 'nr')
]

class MessageFindForm(forms.Form):
    messageaction = forms.CharField(widget=forms.HiddenInput(), initial="find")
    message_set = forms.ModelChoiceField(queryset=MessageSet.objects.all())
    sequence_number = forms.IntegerField()
    lang = forms.ChoiceField(choices=LANG_CHOICES)


class MessageUpdateForm(forms.Form):
    messageaction = forms.CharField(
        widget=forms.HiddenInput(), initial="update")
    message_id = forms.IntegerField(widget=forms.HiddenInput())
    content = forms.CharField(widget=forms.Textarea)
