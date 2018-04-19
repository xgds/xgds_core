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


def loadCSV(config, csvFile):
    delimiter = ','
    if 'delimiter' in config:
        delimiter = config['delimiter']

    quotechar = '"'
    if 'quotechar' in config:
        quotechar = config['quotechar']

    theModel = getModelByName(config['class'])
    newModels = []
    csvFile = open(csvFile, 'rb')
    try:
        csvReader = csv.DictReader(csvfile, fieldnames=config['fieldnames'], delimiter=delimiter, quotechar=quotechar)
        for row in list(csvReader):
            row.update(config['defaults'])
            newModels.append(theModel(**row))
        theModel.objects.bulk_create(newModels)
    finally:
        csvFile.close()


def doImport(yamlFile, csvFile):
    config = loadYaml(yamlFile)
    loadCSV(config, csvFile)
