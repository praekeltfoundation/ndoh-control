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
    ('en', 'English'),
    ('af', 'Afrikaans'),
    ('zu', 'Zulu'),
    ('xh', 'Xhosa'),
    ('ve', 'Venda'),
    ('tn', 'Tswnana'),
    ('ts', 'Tsonga'),
    ('ss', 'Swazi'),
    ('st', 'Sotho'),
    ('nso', 'Northern Sotho'),
    ('nr', 'Ndebele')
]


class MessageFindForm(forms.Form):
    messageaction = forms.CharField(widget=forms.HiddenInput(), initial="find")
    message_set = forms.ModelChoiceField(queryset=MessageSet.objects.all())
    sequence_number = forms.IntegerField(min_value=1)
    lang = forms.ChoiceField(choices=LANG_CHOICES)


class MessageUpdateForm(forms.Form):
    messageaction = forms.CharField(
        widget=forms.HiddenInput(), initial="update")
    message_id = forms.IntegerField(widget=forms.HiddenInput())
    content = forms.CharField(widget=forms.Textarea)


class MessageConfirmForm(forms.Form):
    messageaction = forms.CharField(
        widget=forms.HiddenInput(), initial="confirm")
    message_id = forms.IntegerField(widget=forms.HiddenInput())
    content = forms.CharField(widget=forms.HiddenInput())


class SubscriptionFindForm(forms.Form):
    subaction = forms.CharField(widget=forms.HiddenInput(), initial="find")
    msisdn = forms.CharField(label="Cellphone Number")


class SubscriptionConfirmCancelForm(forms.Form):
    subaction = forms.CharField(
        widget=forms.HiddenInput(), initial="confirmcancel")
    msisdn = forms.CharField(widget=forms.HiddenInput())


class SubscriptionConfirmBabyForm(forms.Form):
    subaction = forms.CharField(
        widget=forms.HiddenInput(), initial="confirmbaby")
    msisdn = forms.CharField(widget=forms.HiddenInput())
    existing_id = forms.IntegerField(widget=forms.HiddenInput())


class SubscriptionCancelForm(forms.Form):
    subaction = forms.CharField(
        widget=forms.HiddenInput(), initial="cancel")
    msisdn = forms.CharField(widget=forms.HiddenInput())


class SubscriptionBabyForm(forms.Form):
    subaction = forms.CharField(
        widget=forms.HiddenInput(), initial="baby")
    msisdn = forms.CharField(widget=forms.HiddenInput())
    existing_id = forms.IntegerField(widget=forms.HiddenInput())
