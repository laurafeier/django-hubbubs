from django.conf.urls import patterns, url
from .views import AbstractSubscriberCallback
from .models import Subscription

sub_callback = AbstractSubscriberCallback.as_view(model=Subscription)

urlpatterns = patterns('',
    url(r'^(?P<object_id>\d+)/$', sub_callback, name='hubbubs_callback'),
)
