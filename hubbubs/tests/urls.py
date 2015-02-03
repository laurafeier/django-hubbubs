from django.conf.urls import patterns, include, url

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^hubbubs/', include('hubbubs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
