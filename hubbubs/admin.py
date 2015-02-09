from django.contrib import admin
from django.template.defaultfilters import timesince_filter
from .models import Subscription


class AbstractSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('topic', 'status',
                    'lease_expires_in', 'last_update', 'site',
                    'custom_actions')

    def lease_expires_in(self, subscription):
        return timesince_filter(subscription.lease_expiration)

    def last_update(self, subscription):
        return timesince_filter(subscription.updated_at)

    def custom_actions(self, subscription):
        link_html = "<li><a href='%s' class='link'>%s</a></li>"
        list_style = "float: none; margin: 0px; padding: 0px;"
        return (
            '<ul style="%s" class="object-tools">' % list_style +
            link_html % ('', 'Subscribe') +
            link_html % ('', 'Unsubscribe') +
            '</ul>'
        )
    custom_actions.short_description = 'Actions'
    custom_actions.allow_tags = True


class SubscriptionAdmin(AbstractSubscriptionAdmin):
    pass


admin.site.register(Subscription, SubscriptionAdmin)
