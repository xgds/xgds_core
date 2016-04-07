#__BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
#
# The xGDS platform is licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#__END_LICENSE__

from django.conf.urls import url
from django.views.generic.base import TemplateView

import xgds_core.views as views

urlpatterns = [url(r'^gridstack_test$', TemplateView.as_view(template_name='xgds_core/gridstack_test.html'), {}, 'gridstack_test'),
               url(r'^gridstack_generic_test$', TemplateView.as_view(template_name='xgds_core/gridstack_generic_test.html'), {}, 'gridstack_test'),
               url(r'^gridstack_test_bootstrap$', TemplateView.as_view(template_name='xgds_core/gridstack_test_bootstrap.html'), {}, 'gridstack_test'),
               url(r'^test_bootstrap$', TemplateView.as_view(template_name='xgds_core/test_bootstrap.html'), {}, 'gridstack_test'),
               url(r'^update_session', views.update_session, {}, 'update_session'),
               url(r'^update_cookie', views.update_cookie, {}, 'update_cookie'),
               ]
