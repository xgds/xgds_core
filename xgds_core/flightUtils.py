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
# pylint: disable=W0702

import pytz
from uuid import uuid4
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from geocamUtil.loader import LazyGetModelByName


ACTIVE_FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_ACTIVE_FLIGHT_MODEL)
FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_FLIGHT_MODEL)
GROUP_FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_GROUP_FLIGHT_MODEL)
VEHICLE_MODEL = LazyGetModelByName(settings.XGDS_CORE_VEHICLE_MODEL)


def getFlight(event_time, vehicle=None):
    """ Returns the flight that contains that event_time """
    if vehicle:
        found_flights = FLIGHT_MODEL.get().objects.exclude(end_time__isnull=True).filter(vehicle=vehicle, start_time__lte=event_time, end_time__gte=event_time)
    else:
        found_flights = FLIGHT_MODEL.get().objects.exclude(end_time__isnull=True).filter(start_time__lte=event_time, end_time__gte=event_time)

    if found_flights.count() == 0:
        found_active_flight = getActiveFlight(vehicle)
        if found_active_flight and found_active_flight.start_time:
            if event_time >= found_active_flight.start_time:
                return found_active_flight;
        return None
    else:
        return found_flights[0]
    
    
def getNextAlphabet(character):
    """
    For getting the next letter of the alphabet for prefix.
    """
    # a is '97' and z is '122'. There are 26 letters total
    nextChar = ord(character) + 1
    if nextChar > 122:
        nextChar = (nextChar - 97) % 26 + 97
    return chr(nextChar)


def get_next_available_group_flight_name(prefix):
    character = 'A'
    gModel = GROUP_FLIGHT_MODEL.get()
    while True:
        try:
            gModel.objects.get(name=prefix + character)
            character = getNextAlphabet(character)
        except:
            return prefix + character

    
def getActiveFlight(vehicle):
    if vehicle:
        foundFlights = ACTIVE_FLIGHT_MODEL.get().objects.filter(flight__vehicle = vehicle)
    else:
        foundFlights = ACTIVE_FLIGHT_MODEL.get().objects.filter()
        
    if foundFlights:
        return foundFlights.last().flight
    return None


def get_default_vehicle():
    """
    Gets the default vehicle.
    :return:
    """
    return VEHICLE_MODEL.get().objects.get(pk=settings.XGDS_CORE_DEFAULT_VEHICLE_PK)


def create_group_flight(group_flight_name, notes=None, vehicles=None):
    """
    Create a new group flight
    :param group_flight_name:
    :param notes:
    :param vehicles:
    :return:
    """
    group_flight = GROUP_FLIGHT_MODEL.get()(name=group_flight_name, notes=notes)
    group_flight.save()

    if not vehicles:
        vehicles = VEHICLE_MODEL.get().objects.all()
    for vehicle in vehicles:
        new_flight = FLIGHT_MODEL.get()()
        new_flight.group = group_flight
        new_flight.vehicle = vehicle
        new_flight.name = group_flight_name + "_" + vehicle.name
        new_flight.uuid = uuid4()
        new_flight.save()

    return group_flight


def lookup_vehicle(vehicle_name):
    """ Look up the vehicle by name or get the default
    :param vehicle_name: The name of the vehicle
    :return: the found vehicle, or None
    """
    vehicle = None
    try:
        if vehicle_name:
            vehicle = VEHICLE_MODEL.get().objects.get(name=vehicle_name)
    except:
        pass
    if not vehicle:
        vehicle = get_default_vehicle()
    return vehicle


def lookup_flight(flight_name):
    """ Look up the flight by name
    :param flight_name: The name of the flight
    :return: the found flight, or None
    """
    flight = None
    if flight_name:
        try:
            flight = FLIGHT_MODEL.get().objects.get(name=flight_name)
        except:
            pass
    return flight


def get_or_create_flight(start_time, vehicle=None, check_flight_exists=True, end_time=None):
    """
    Get or create a flight; will create the group flight and the flights, and set the start time.
    :param start_time: the start time of the flight
    :param vehicle: the vehicle
    :param check_flight_exists: flag to check if the flight exists
    :param end_time: Not used for search, but if you want to set the end time of the newly created flight pass it here
    :return: the flight
    """
    if not vehicle:
        vehicle = get_default_vehicle()
    flight = None
    if check_flight_exists:
        flight = getFlight(start_time, vehicle)
    if not flight:
        # There was not a valid flight, so let's make a new one.  We will make a new group flight.

        # localize the time
        local_start_time = start_time.astimezone(pytz.timezone(settings.TIME_ZONE))
        group_flight = create_group_flight(get_next_available_group_flight_name(local_start_time.strftime('%Y%m%d')))
        if group_flight:
            flights = group_flight.flights.filter(vehicle=vehicle)
            flight = flights[0]  # there should only be one

            # set its start time
            flight.start_time = start_time
            flight.end_time = end_time
            flight.save()
    else:
        flight.update_start_time(start_time)
    return flight


def get_or_create_flight_with_source_root(source_root, timestamp, end_time=None):
    """
    See if there is already a flight for this directory, or create it.
    It is on us to guarantee uniqueness (db has limitation of 255 characters for unique)
    #TODO have flexible flight naming convention and make sure that works
    :param source_root: the path that should correspond to a flight
    :param timestamp: the timestamp to be used when building flight name
    :return: the flight
    """
    try:
        flight = FLIGHT_MODEL.get().objects.get(source_root__icontains=source_root)
    except ObjectDoesNotExist:
        # create it
        flight = get_or_create_flight(timestamp, check_flight_exists=False, end_time=end_time)
        flight.source_root = source_root
        flight.save()
    return flight
