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
from django.views.generic.base import TemplateView, RedirectView
from django.conf import settings

from dal.autocomplete import Select2QuerySetView

import xgds_core.views as views
import xgds_core.typeahead as typeahead
from xgds_core.models import XgdsUser

urlpatterns = [url(r'^gridstack_test$', TemplateView.as_view(template_name='xgds_core/gridstack_test.html'), {}, 'gridstack_test'),
               url(r'^gridstack_generic_test$', TemplateView.as_view(template_name='xgds_core/gridstack_generic_test.html'), {}, 'gridstack_generic_test'),
               url(r'^gridstack_generic_oursite$', TemplateView.as_view(template_name='xgds_core/gridstack_generic_oursite.html'), {}, 'gridstack_test_oursite'),
               url(r'^gridstack_test_bootstrap$', TemplateView.as_view(template_name='xgds_core/gridstack_test_bootstrap.html'), {}, 'gridstack_test_bootstrap'),
               url(r'^test_bootstrap$', TemplateView.as_view(template_name='xgds_core/test_bootstrap.html'), {}, 'gridstack_test'),
               url(r'^test_bootstrap4$', TemplateView.as_view(template_name='test/hello_bootstrap.html'), {}, 'test_bootstrap4'),
               url(r'^update_session', views.update_session, {}, 'update_session'),
               url(r'^update_cookie', views.update_cookie, {}, 'update_cookie'),
               url(r'^handlebar_string/(?P<handlebarPath>[\s\S]+)$', views.get_handlebar_as_string, {}, 'handlebar_string'),
               url(r'^db_attachment/(?P<docDir>[\w./-]+)/(?P<docName>[\w.-]+)$', views.get_db_attachment, {'readOnly': True, 'loginRequired': False, 'securityTags': ['readOnly']}, 'get_db_attachment'),
               url(r'^live/$', RedirectView.as_view(url=settings.XGDS_CORE_LIVE_INDEX_URL, permanent=False), name='live_index'),
               url(r'^error', TemplateView.as_view(template_name='xgds_core/error.html'), {}, 'error'),
               url(r'^view/(?P<modelName>\w+)/$', views.OrderListJson.as_view(), {}, 'view_json_modelName'),
               #url(r'^view/(?P<modelName>\w+)/(?P<filter>(([\w]+|[a-zA-Z0-9:._\-\s]+),*)+)$', views.OrderListJson.as_view(), {}, 'view_json_modelName_filter'),
               url(r'^help/(?P<help_content_path>[\s\S]+)/(?P<help_title>[\s\S]+)$', views.helpPopup, {}, 'help_popup'),
               url(r'^users.json$', typeahead.getTypeaheadUsers, {}, 'xgds_core_users_json'),
               url(r'^(?P<model_name>[\w]+[\.]*[\w]*).json$', typeahead.getTypeaheadJson, {}, 'xgds_core_model_json'),
               url(r'^complete/User.json/$', typeahead.XSelect2QuerySetView.as_view(model=XgdsUser), name='select2_model_user'),
               url(r'^complete/(?P<model_name>[\w]+[\.]*[\w]*).json/$',typeahead.getSelectJson2, name='select2_model'),

               ]
