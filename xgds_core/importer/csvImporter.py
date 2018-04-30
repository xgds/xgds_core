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
        the_time = dateparser(row['timestamp'])
        flight = getFlight(the_time, vehicle)
        if not flight:
            # There was not a valid flight, so let's make a new one.  We will make a new group flight.
            group_flight = create_group_flight(get_next_available_group_flight_name(the_time.strftime('%Y%m%d')))
            if group_flight:
                for f in group_flight.flights:
                    if f.vehicle == vehicle:
                        flight = f
                        break
    return flight


def load_csv(config, csv_file, vehicle, flight, defaults):
    """
    Load the CSV file according to the configuration, and store the values in the database using the
    Django ORM and including any data from the current state.
    Warning: the model's save method will not be called as we are using bulk_create.
    :param config: the configuration dictionary
    :param csv_file: the path to the csv file
    :param vehicle: vehicle if any
    :param flight: flight if any
    :param defaults: the dictionary of defaults
    :return: the number of rows loaded
    """
    delimiter = ','
    if 'delimiter' in config:
        delimiter = config['delimiter']

    quotechar = '"'
    if 'quotechar' in config:
        quotechar = config['quotechar']

    the_model = getModelByName(config['class'])
    new_models = []
    csv_file = open(csv_file, 'rb')
    count = 0
    try:
        csv_reader = csv.DictReader(csv_file, fieldnames=config['fieldnames'], delimiter=delimiter, quotechar=quotechar)
        the_list = list(csv_reader)
        count = len(the_list)
        if not flight and config['flight_required']:
            # read the first timestamp and find a flight for it
            flight = get_or_make_flight(vehicle, the_list[0])
            config['defaults']['flight_id'] = flight.id
        for row in the_list:
            row.update(config['defaults'])
            for fieldname in config['timefields']:
                row[fieldname] = dateparser(row[fieldname])
            print row

            new_models.append(the_model(**row))
        the_model.objects.bulk_create(new_models)
    finally:
        csv_file.close()
    return count


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


def do_import(yaml_file, csv_file, vehicle_name=None, flight_name=None, defaults=None, stateKey=None):
    """
    Do an import with a path to a configuration yaml file and a path to a csv file
    :param yaml_file: The path to the yaml configuration file for import
    :param csv_file: The path to the csv file to import
    :param vehicle_name: The name of the vehicle
    :param flight_name: The name of the flight
    :param stateKey: The state key to look up the active state.  None will use the last active state.
    :param defaults: Optional additional defaults to add to objects
    :return: the number of items imported
    """
    config = load_yaml(yaml_file, defaults)

    vehicle = None
    try:
        if vehicle_name:
            vehicle = VEHICLE_MODEL.get().objects.get(name=vehicle_name)
    except:
        pass
    if not vehicle:
        vehicle = get_default_vehicle()

    flight = None
    if flight_name:
        try:
            flight = FLIGHT_MODEL.get().objects.get(name=flight_name)
        except:
            pass

    # state = getStateDict(stateKey)
    # state.update(defaults)
    return load_csv(config, csv_file, vehicle, flight, defaults)


