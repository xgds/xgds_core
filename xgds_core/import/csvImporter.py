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

from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import csv

from geocamUtil.loader import getModelByName
from xgds_core.views import getActiveStates, getState,


def loadYaml(yamlFile):
    """
    Load the contents of a Yaml file and return it as a dictionary.
    :param yamlFile: the path to the file to load.  If running within django, the path can be /apps/myapp/path/to/yaml
    :return: the dictionary of data
    """
    theStream = open(yamlFile, 'r')
    try:
        data = load(theStream, Loader=Loader)
        data['fieldnames'] = [f['name'] for f in data['fields']]

        if 'defaults' not in data:
            data['defaults'] = {}
    finally:
        theStream.close()
    return data


def loadCSV(config, csvFile, state):
    """
    Load the CSV file according to the configuration, and store the values in the database using the
    Django ORM and including any data from the current state.
    Warning: the model's save method will not be called as we are using bulk_create.
    :param config: the configuration dictionary
    :param csvFile: the path to the csv file
    :param state: the state dictionary to use
    :return: the number of rows loaded
    """
    delimiter = ','
    if 'delimiter' in config:
        delimiter = config['delimiter']

    quotechar = '"'
    if 'quotechar' in config:
        quotechar = config['quotechar']

    theModel = getModelByName(config['class'])
    newModels = []
    csvFile = open(csvFile, 'rb')
    count = 0
    try:
        csvReader = csv.DictReader(csvfile, fieldnames=config['fieldnames'], delimiter=delimiter, quotechar=quotechar)
        theList = list(csvReader)
        count = len(theList)
        for row in theList:
            row.update(config['defaults'])
            newModels.append(theModel(**row))
        theModel.objects.bulk_create(newModels)
    finally:
        csvFile.close()
    return count


def getStateDict(stateKey):
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


def doImport(yamlFile, csvFile, stateKey=None, defaults=None):
    """
    Do an import with a path to a configuration yaml file and a path to a csv file
    :param yamlFile: The path to the yaml configuration file for import
    :param csvFile: The path to the csv file to import
    :param stateKey: The state key to look up the active state.  None will use the last active state.
    :param defaults: Optional additional defaults to add to objects
    :return: the number of items imported
    """
    config = loadYaml(yamlFile)
    state = getStateDict(stateKey)
    state.update(defaults)
    return loadCSV(config, csvFile, state)
