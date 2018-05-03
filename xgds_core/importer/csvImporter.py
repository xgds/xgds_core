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

"""
Utilities for loading a csv file into the database per the yaml specification.
see ../../docs/dataImportYml.rst
"""
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import csv
from collections import OrderedDict

from geocamUtil.loader import getModelByName
from xgds_core.views import getActiveStates, getState
from xgds_core.flightUtils import get_default_vehicle, getFlight, create_group_flight, get_next_available_group_flight_name
from geocamUtil.loader import LazyGetModelByName
from dateutil.parser import parse as dateparser

from django.conf import settings

VEHICLE_MODEL = LazyGetModelByName(settings.XGDS_CORE_VEHICLE_MODEL)
FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_FLIGHT_MODEL)


# Create an ordered load function for yaml, to keep the dictionary keys in order.
def ordered_load(stream, Loader=Loader, object_pairs_hook=OrderedDict):

    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)

    return yaml.load(stream, OrderedLoader)


def load_yaml(yaml_file, defaults):
    """
    Load the contents of a Yaml file and return it as a dictionary.
    :param yaml_file: the path to the file to load.  If running within django, the path can be /apps/myapp/path/to/yaml
    :param defaults: default dictionary to append to config defaults
    :return: the dictionary of data
    """
    the_stream = open(yaml_file, 'r')
    try:
        data = ordered_load(the_stream, Loader=Loader)
        data['fieldnames'] = data['fields'].keys()

        if not defaults:
            defaults = {}
        if 'defaults' not in data:
            data['defaults'] = defaults
        else:
            data['defaults'].update(defaults)

        data['timefields'] = []
        for key, value in data['fields'].iteritems():
            if 'time' in value['type']:
                data['timefields'].append(key)

        if 'flight_required' not in data:
            data['flight_required'] = False

    finally:
        the_stream.close()
    return data


def get_or_make_flight(vehicle, row):
    """
    Use the timestamp in the row to look up or create a flight.
    :param vehicle: the vehicle
    :param row: the first row of the csv
    :return: the flight
    """
    flight = None

    if 'timestamp' in row:
        the_time = dateparser(row['timestamp'])  #TODO timezone
        flight = getFlight(the_time, vehicle)
        if not flight:
            # There was not a valid flight, so let's make a new one.  We will make a new group flight.
            group_flight = create_group_flight(get_next_available_group_flight_name(the_time.strftime('%Y%m%d')))
            if group_flight:
                flights = group_flight.flights.filter(vehicle=vehicle)
                flight = flights[0] # there should only be one

                # set its start time
                flight.start_time = the_time
                flight.save()
        else:
            update_flight_start(flight, the_time)

    return flight


def open_csv(config, csv_file):
    """ Open the CSV file and return a tuple of the file, dictreader"""
    delimiter = ','
    if 'delimiter' in config:
        delimiter = config['delimiter']

    quotechar = '"'
    if 'quotechar' in config:
        quotechar = config['quotechar']

    csv_file = open(csv_file, 'rb')
    try:
        csv_reader = csv.DictReader(csv_file, fieldnames=config['fieldnames'], delimiter=delimiter, quotechar=quotechar)
    except Exception as e:
        csv_file.close()
        raise e
    return csv_file, csv_reader


def update_row(config, row):
    """
    Update the row from the config
    :param config: the config file to use to update the row
    :param row: the loaded row
    :return: the updated row, with timestamps and defaults
    """
    row.update(config['defaults'])
    for field_name in config['timefields']:
        row[field_name] = dateparser(row[field_name])
    return row


def update_flight_end(flight, end):
    """
    Update the flight end time AND SAVE THE FLIGHT if it is not set or if this row is after its end time
    :param flight: the flight
    :param end: the end time
    :return:
    """
    if flight:
        if not flight.end_time or end > flight.end_time:
            flight.end_time = end
            flight.save()


def update_flight_start(flight, start):
    """
    Update the flight start time AND SAVE THE FLIGHT if it is not set or if this row is before its start time
    :param flight: the flight
    :param start: the start time
    :return:
    """
    if flight:
        if not flight.start_time or start < flight.start_time:
            flight.start_time = start
            flight.save()


def load_csv(config, vehicle, flight, csv_file, csv_reader):
    """
    Load the CSV file according to the configuration, and store the values in the database using the
    Django ORM and including any data from the current state.
    Warning: the model's save method will not be called as we are using bulk_create.
    :param config: the configuration dictionary
    :param vehicle: vehicle if any
    :param flight: flight if any
    :param csv_file: the opened csv file
    :param csv_reader: the dict reader
    :return: the newly created models, which may be an empty list
    """

    the_model = getModelByName(config['class'])
    new_models = []

    try:
        csv_file.seek(0)
        for row in csv_reader:
            row = update_row(config, row)
            new_models.append(the_model(**row))
        update_flight_end(config['flight'], row['timestamp'])
        the_model.objects.bulk_create(new_models)
    finally:
        csv_file.close()
    return new_models


def get_state_dict(stateKey):
    result = {}
    state = None
    if stateKey:
        state = getState(stateKey)
    else:
        states = getActiveStates()
        if states:
            state = states.last()
    if state:
        result = state.values.to_dict()
    return result


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


def check_data_exists(config, row):
    """
    See if there is already identical data
    :param config: the config
    :param row: typically the first row
    :return: True if it already exists, false otherwise
    """
    row = update_row(config, row)
    the_model = getModelByName(config['class'])
    result = the_model.objects.filter(**row)
    return result.exists()


def configure(yaml_file_path, csv_file_path, vehicle_name=None, flight_name=None, defaults=None, force=False):
    """
    Configure flight, vehicle, the yanl configuration file.  Create a flight if necessary based on the first time.
    :param yaml_file_path: The path to the yaml configuration file for import
    :param csv_file_path: The path to the csv file to import
    :param vehicle_name: The name of the vehicle
    :param flight_name: The name of the flight
    :param defaults: Optional additional defaults to add to objects
    :return: the config, which will contain the vehicle, flight, csv_file and csv_reader
    """
    vehicle = lookup_vehicle(vehicle_name)
    flight = lookup_flight(flight_name)
    config = load_yaml(yaml_file_path, defaults)
    config['vehicle'] = vehicle
    config['flight'] = flight
    csv_file, csv_reader = open_csv(config, csv_file_path)
    first_row = list(csv_reader)[0]
    if not force:
        exists = check_data_exists(config, first_row)
        if exists:
            print " ABORTING: MATCHING DATA FOUND"
            print first_row
            raise Exception('Matching data found, data already imported', first_row)
    csv_file.seek(0)
    if not flight and config['flight_required']:
        # read the first timestamp and find a flight for it
        config['flight'] = get_or_make_flight(vehicle, first_row)
        config['defaults']['flight_id'] = config['flight'].id
    config['csv_file'] = csv_file
    config['csv_reader'] = csv_reader
    return config


def do_import(yaml_file_path, csv_file_path, vehicle_name=None, flight_name=None, defaults=None, force=False, stateKey=None):
    """
    Do an import with a path to a configuration yaml file and a path to a csv file
    :param yaml_file_path: The path to the yaml configuration file for import
    :param csv_file_path: The path to the csv file to import
    :param vehicle_name: The name of the vehicle
    :param flight_name: The name of the flight
    :param stateKey: The state key to look up the active state.  None will use the last active state.
    :param defaults: Optional additional defaults to add to objects
    :return: the imported items
    """

    config = configure(yaml_file_path, csv_file_path, vehicle_name, flight_name, defaults, force)

    # state = getStateDict(stateKey)
    # state.update(defaults)
    return load_csv(config, config['vehicle'], config['flight'], config['csv_file'], config['csv_reader'])


