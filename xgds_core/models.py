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

from django.utils import timezone
from django.db import models
from xgds_core.util import get100Years

class Constant(models.Model):
    name = models.CharField(max_length=64, blank=False)
    units = models.CharField(max_length=32, blank=False)
    notes = models.CharField(max_length=256, blank=False)
    dataType = models.CharField(max_length=32, blank=False)
    value = models.CharField(max_length=256, blank=False)
    
class TimeZoneHistory(models.Model):
    startTime = models.DateTimeField(default=timezone.now)
    endTime = models.DateTimeField(null=True, blank=True, default=get100Years )
    timeZone = models.CharField(max_length=128, blank=False)
    notes = models.CharField(max_length=512, blank=True)