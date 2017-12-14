from django.conf.urls import url, include
from django.contrib.auth.views import logout, LoginView
from django.contrib.auth.decorators import login_required
from django.views.generic.base import RedirectView

from backend.apps.base.views import *

urlpatterns = [
#     url(r'^login/$', LoginView.as_view(template_name='base/login.html') , name='login'),
#     url(r'^logout/$', logout, name='logout'),
#     url(r'^$', login_required(home), name='home'),
#     url(r'^api/test_endpoint/$', test_endpoint, name='test_endpoint'),
#     url(r'^api/send_sms/$', SendSMSView.as_view(), name='send_sms'),
#     url(r'^api/call_back/$', CallBackView.as_view(), name='call_back'),
#     url(r'^.*/$', RedirectView.as_view(url='/', permanent=False), name='redirect'),
]
