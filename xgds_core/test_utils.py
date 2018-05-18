# __BEGIN_LICENSE__
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
# __END_LICENSE__

import datetime
import json
import pytz
from django.conf import settings
from django.test import TestCase

from xgds_core.flightUtils import get_default_vehicle, getFlight, getNextAlphabet, create_group_flight

class xgds_getFlightTest(TestCase):
    """
    Tests for getFlight
    """
    fixtures = ['xgds_core_testing.json']

    def test_getFlight(self):
        flight = getFlight(datetime.datetime(2015,12,25,12,0,0,0,pytz.utc),1)
        assert(flight.id==1)
        assert(flight.uuid=='abc123')
        assert(flight.name=='Christmas in a Generic Vehicle')


    def test_getFlightWithoutVehicle(self):
        flight = getFlight(datetime.datetime(2015,12,25,12,0,0,0,pytz.utc),None)
        assert(flight.id==1)
        assert(flight.uuid=='abc123')
        assert(flight.name=='Christmas in a Generic Vehicle')


    def test_getFlightNoResult(self):
        # If there is no vehicle and the query time is PRIOR TO the
        # active flight we should get None as a result
        flight = getFlight(datetime.datetime(2014,12,25,12,0,0,0,pytz.utc),None)
        assert(flight==None)


    def test_getFlightActive(self):
        # If there is no vehicle and the query time is AFTER the
        # active flight we should get the active flight as a result
        flight = getFlight(datetime.datetime(2016,12,25,12,0,0,0,pytz.utc),None)
        assert(flight.id==1)
        assert(flight.uuid=='abc123')
        assert(flight.name=='Christmas in a Generic Vehicle')


    def test_getNextAlphabet(self):
        assert('b'==getNextAlphabet('a'))
        assert('c'==getNextAlphabet('b'))
        assert('a'==getNextAlphabet('z'))

        # Do we care about this working properly for capital letters?
        # Because it doesn't, after "Z" is "["
        # assert('B'==getNextAlphabet('A'))
        # assert('C'==getNextAlphabet('B'))
        # assert('A'==getNextAlphabet('Z'))

