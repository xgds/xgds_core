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
Utilities for discovering telemetry files and launching the corresponding loader.
See ../../docs/dataImportYml.rst
"""


import yaml
import os
import re
import datetime
import pytz
from subprocess import Popen, PIPE
from threading import Timer
import shlex
import time
import traceback
import django
django.setup()
from xgds_core.models import ImportedTelemetryFile
from heapq import *


class ImportFinder:
    def __init__(self, config_yaml_path):
        # config comes from a YAML file
        self.config = yaml.load(open(config_yaml_path))
        self.registry = self.config['registry']
        # Local copy of processed files, which are also tracked in the database
        # in order to keep state when the import finder is restarted and for
        # reporting import status to users
        self.processed_files = []
        self.files_to_process = []
        # Keep track of the disposition of all discovered files:
        self.previously_imported_files = [] # were in the database
        self.ignored_files = [] # matched an explicit ignore rule
        self.ambiguous_files = [] # matched more than one config rule
        self.unmatched_files = [] # matched no config rule
        self.imports_that_failed = [] # tried to import and failed
        self.imports_that_succeeded = [] # tried and succeeded

    def get_new_files(self):
        for dirName, subdirList, fileList in os.walk(self.config['import_path']):
            #print('Found directory: %s' % dirName)
            for basename in fileList:
                filename = os.path.join(dirName, basename)
                # If the filename is in the list of processed files, skip it
                if filename in self.processed_files:
                    '%s is in processed files list' % filename
                    continue
                # If the filename is not in the locally cached list it might be in the db as
                # having successfully imported previously
                previous = ImportedTelemetryFile.objects.filter(filename=filename, returncode=0)
                if previous:
                    print '%s is in the database as having been imported' % filename
                    # Add it to the previously imported files for statistics
                    self.previously_imported_files.append(filename)
                    # Add it to the locally cached copy of processed files
                    self.processed_files.append(filename)
                    continue

                # Identify which importer to use, and make sure it's a unique match
                matches = []
                for r in self.registry:
                    #print r['filepath_pattern']
                    match = re.search(r['filepath_pattern'], filename)
                    if match:
                        matches.append(r)
                if 1 == len(matches):
                    if 'ignore' in matches[0] and matches[0]['ignore']:
                        # matched an explicit ignore rule
                        print 'Ignoring', basename
                        self.ignored_files.append(filename)
                        continue
                    if 'order' in matches[0].keys():
                        order = matches[0]['order']
                    else:
                        order = 10
                    print 'Adding', basename
                    # unique match, add to the list of things to import
                    heappush(self.files_to_process,(order,(filename,matches[0])))
                elif 0 == len(matches):
                    print 'Warning: file %s does not match any importer config' % filename
                    self.unmatched_files.append(filename)
                else:
                    print 'Warning: file %s matches more than one importer config' % filename
                    for m in matches:
                        print m
                    self.ambiguous_files.append(filename)

        print 'Identified files to process:'
        for item in self.files_to_process:
            order = item[0]
            filename = item[1][0]
            registry = item[1][1]
            print '%s %s' % (order,filename)

    def process_files(self):
        while len(self.files_to_process)>0:
            order, pair = heappop(self.files_to_process)
            filename, registry = pair
            arguments = ''
            if 'arguments' in registry:
                if '%(filename)s' in registry['arguments']:
                    arguments = registry['arguments']
                    arguments = arguments % {'filename': filename}
                else:
                    arguments = ' '.join([registry['arguments'], filename])
            else:
                    arguments = filename
            cmd = ' '.join([registry['importer'], arguments])
            timeout = registry['timeout']
            try:
                print order, cmd
                proc = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
            except Exception as e:
                print str(e)
                print traceback.format_exc()
                continue
            # Set a timeout per the import handler config file
            timer = Timer(timeout, proc.kill)
            start_import_time = pytz.timezone('utc').localize(datetime.datetime.utcnow())
            try:
                timer.start()
                (stdout, stderr) = proc.communicate()
            finally:
                timer.cancel()
            end_import_time = pytz.timezone('utc').localize(datetime.datetime.utcnow())

            # Add or update metadata about this import in the database
            itf = ImportedTelemetryFile()
            previous_itf = ImportedTelemetryFile.objects.filter(filename=filename)
            retry_count = 0
            if previous_itf.count() > 0:
                itf = previous_itf[0]
                retry_count = itf.retry_count + 1
            itf.filename = filename
            itf.commandline = cmd
            itf.timestamp = end_import_time
            itf.duration = (end_import_time - start_import_time).total_seconds()
            itf.returncode = proc.returncode
            itf.runlog = stdout
            itf.errlog = stderr
            itf.retry_count = retry_count
            itf.save()
            # If it succeeded, keep track that we did this one
            if proc.returncode == 0:
                self.imports_that_succeeded.append(filename)
                self.processed_files.append(filename)
            else:
                self.imports_that_failed.append(filename)

    def print_import_stats(self):
        print 'Found %d previously imported files' % len(self.previously_imported_files)
        print 'Found %d files configured to ignore' % len(self.ignored_files)
        print 'Found %d ambiguous files, matched more than one config rule' % len(self.ambiguous_files)
        print 'Found %d unmatched files, matched no config rule' % len(self.unmatched_files)
        print 'Tried %d imports that failed' % len(self.imports_that_failed)
        print 'Tried %d imports that succeeded' % len(self.imports_that_succeeded)

    def do_once(self,test):
        self.get_new_files()
        self.process_files()

    def loop(self):
        while True:
            self.do_once()
            time.sleep(10)


if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser('usage: %prog')
    parser.add_option('-t', '--test',
                      action='store_true', default=False,
                      help='Run in test mode: find files and report them but do not process them')
    opts, args = parser.parse_args()

    finder = ImportFinder(args[0])
    finder.get_new_files()
    if not opts.test:
        finder.process_files()
    finder.print_import_stats()
