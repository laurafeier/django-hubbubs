from django import forms
from django.utils import html
from django.utils.safestring import mark_safe

# thanks to https://djangosnippets.org/snippets/2312/
class SubmitButtonWidget(forms.CheckboxInput):

    def render(self, name, value, attrs=None):
        return mark_safe(
            '<input type="submit" class="default" name="%s" value="%s">' % (
            html.escape(name), html.escape(value)
        ))


class SubmitButtonField(forms.Field):

    def __init__(self, *args, **kwargs):
        kwargs = kwargs or {}
        kwargs["widget"] = SubmitButtonWidget
        kwargs["required"] = False
        kwargs["label"] = ''
        super(SubmitButtonField, self).__init__(*args, **kwargs)

    def clean(self, value):
        return value


class SubscribeForm(forms.ModelForm):
    generate_verification_token = forms.BooleanField(
        required=False, initial=True)
    custom_verification_token = forms.CharField(
        required=False, max_length=255)

    generate_secret_key = forms.BooleanField(
        required=False, initial=True)
    custom_secret_key = forms.CharField(
        required=False, max_length=255)

    subscribe = SubmitButtonField(initial='Subscribe to topic')

    fieldsets = [
        (None, {
            'fields': [
                ('topic', 'hub', 'site'),
                ('generate_verification_token', 'custom_verification_token'),
                ('generate_secret_key', 'custom_secret_key'),
                'subscribe'
            ]
        })
    ]
    readonly = ('topic', 'hub', 'site')
