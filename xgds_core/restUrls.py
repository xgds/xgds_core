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
import xgds_core.redisUtil as redisUtil
import xgds_core.typeahead as typeahead
from xgds_core.models import XgdsUser

urlpatterns = [url(r'^view/(?P<modelName>\w+)/$', views.OrderListJson.as_view(), {}, 'view_json_modelName'),
               url(r'^users.json$', typeahead.getTypeaheadUsers, {}, 'xgds_core_users_json'),
               url(r'^(?P<model_name>[\w]+[\.]*[\w]*).json$', typeahead.getTypeaheadJson, {}, 'xgds_core_model_json'),
               url(r'^complete/User.json/$', typeahead.XSelect2QuerySetView.as_view(model=XgdsUser), name='select2_model_user'),
               url(r'^complete/(?P<model_name>[\w]+[\.]*[\w]*).json/$',typeahead.getSelectJson2, name='select2_model'),
               url(r'^relay/$',views.receiveRelay, {}, 'receive_relay'),
               url(r'^condition/set/$',views.setCondition, {}, 'xgds_core_set_condition'),
               url(r'^condition/activeJSON/$',views.getConditionActiveJSON, {}, 'xgds_core_get_condition_active_json'),
               url(r'^tungsten/dataInsert/(?P<action>[\w]*)/(?P<tablename>[\w]*)/(?P<pk>[\w]*)$',views.dataInsert, {}, 'xgds_core_data_insert'),
               url(r'^rebroadcast/tableNamesAndKeys/$', views.getRebroadcastTableNamesAndKeys, {}, 'xgds_core_rebroadcast_tablenames_keys'),
#                url(r'^condition/list/(?P<state>\w+)/$',views.listConditions, {}, 'xgds_core_list_conditions_by_state'),
#                url(r'^condition/range/(?P<range>[\d]+)/$',views.listConditions, {}, 'xgds_core_list_conditions_by_range'),
               
               ]

if settings.XGDS_CORE_REDIS:
    urlpatterns.append(url(r'^sseActiveChannels/$', redisUtil.getSseActiveChannels, {}, 'xgds_core_sse_active_channels'))
