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

from django.conf.urls import url, include
from django.views.generic.base import TemplateView, RedirectView
from django.conf import settings

import xgds_core.views as views

urlpatterns = [url(r'^update_session', views.update_session, {}, 'update_session'),
               url(r'^update_cookie', views.update_cookie, {}, 'update_cookie'),
               url(r'^handlebar_string/(?P<handlebarPath>[\s\S]+)$', views.get_handlebar_as_string, {}, 'handlebar_string'),
               url(r'^live/$', RedirectView.as_view(url=settings.XGDS_CORE_LIVE_INDEX_URL, permanent=False), name='live_index'),
               url(r'^error', TemplateView.as_view(template_name='xgds_core/error.html'), {}, 'error'),
               url(r'^help/(?P<help_content_path>[\s\S]+)/(?P<help_title>[\s\S]+)$', views.helpPopup, {}, 'help_popup'),
               ## uploading data
               url(r'^import/$', TemplateView.as_view(template_name='xgds_core/importData.html'), name='xgds_core_import'),

               # flight management
               url(r'^updateToday/$', views.updateTodaySession, {}, "xgds_core_updateToday"),
               url(r'^listFlights/$', views.listFlownFlights, {}, "xgds_core_flownFlights"),
               url(r'startFlight/(?P<uuid>[\w-]+)$', views.startFlight, {}, 'xgds_core_startFlight'),
               url(r'stopFlight/(?P<uuid>[\w-]+)$', views.stopFlight, {}, 'xgds_core_stopFlight'),
               url(r'startTracking/(?P<flightName>\w+)$', views.startFlightTracking, {},
                   'xgds_core_startFlightTracking'),
               url(r'stopTracking/(?P<flightName>\w+)$', views.stopFlightTracking, {}, 'xgds_core_stopFlightTracking'),
               url(r'^addGroupFlight/$', views.addGroupFlight, {}, "xgds_core_addGroupFlight"),
               url(r'^manageFlights/$', views.manageFlights, {}, "xgds_core_manage"),
               url(r'^summary/(?P<groupFlightName>\w+)$', views.getGroupFlightSummary,
                   name="xgds_core_group_flight_summary"),
               url(r'^summary/f/(?P<flightName>\w+)$', views.getFlightSummary, name="xgds_core_flight_summary"),

               # Including these in this order ensures that reverse will return the non-rest urls for use in our server
               url(r'^rest/', include('xgds_core.restUrls')),
               url('', include('xgds_core.restUrls')),
               ]

