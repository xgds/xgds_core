#!/usr/bin/env python
#  __BEGIN_LICENSE__
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
Utilities for validating timestamps in import files
"""

import sys

import yaml
import os
import re
import datetime
import pytz

from PNGinfo import PNGinfo
import PIL.Image
import PIL.ExifTags

from csv import DictReader
from dateutil.parser import parse as dateparser


def get_timestamp_from_filename(filename, time_format, regex=None):
    """
    Returns a utz timezone aware time parsed from the filename given the time format & regex
    :param filename: the actual filename to parse for time
    :param time_format: seconds, microseconds or dateparser
    :param regex:  The last pattern matched in the regex should hold the time
    :return: time
    """
    # Some filenames contain float seconds, some int microseconds
    result = None

    if time_format == 'seconds':
        timestamp_pattern = '(\d{10}\.\d{4,10})'
        match = re.search(timestamp_pattern, filename)
        if match:
            timestamp_string = match.groups()[-1]
            result = datetime.datetime.utcfromtimestamp(float(timestamp_string)).replace(tzinfo=pytz.UTC)
        else:
            raise ValueError('Could not find expected time string in %s' % filename)

    elif time_format == 'microseconds':
        timestamp_pattern = '(\d{16})'
        match = re.search(timestamp_pattern, filename)
        if match:
            timestamp_string = match.groups()[-1]
            result = datetime.datetime.utcfromtimestamp(1e-6 * int(timestamp_string)).replace(tzinfo=pytz.UTC)
        else:
            raise ValueError('Could not find expected time string in %s' % filename)
    elif time_format == 'dateparser':
        if regex:
            timestamp_pattern = regex
            match = re.search(timestamp_pattern, filename)
            if match:
                timestamp_string = match.groups()[-1]
                zoneless_timestamp = dateparser(timestamp_string)
                result = pytz.utc.localize(zoneless_timestamp)
            else:
                raise ValueError('Could not find expected time string in %s' % filename)
        else:
            raise ValueError('dateparser configuration requires regex: %s' % filename)

    else:
        raise ValueError('invalid type for filename timestamp: %s' % time_format)
    return result

class TimestampValidator:
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
        self.ignored_files = [] # matched an explicit ignore rule
        self.ambiguous_files = [] # matched more than one config rule
        self.unmatched_files = [] # matched no config rule
        self.timestamps_that_failed = [] # tried to import and failed
        self.timestamps_that_succeeded = [] # tried and succeeded
        # The actual timestamps
        self.timestamps = []

    def find_files(self, root_dir):
        for dirName, subdirList, fileList in os.walk(root_dir):
            # print('Found directory: %s' % dirName)
            for basename in fileList:
                filename = os.path.join(dirName, basename)

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
                        if not QUIET:
                            print 'Ignoring', basename
                        self.ignored_files.append(filename)
                        continue
                    if not QUIET:
                        print 'Adding', basename
                    # unique match, add to the list of things to import
                    self.files_to_process.append((filename, matches[0]))
                elif 0 == len(matches):
                    if not QUIET:
                        print 'Warning: file %s does not match any importer config' % filename
                    self.unmatched_files.append(filename)
                else:
                    if not QUIET:
                        print 'Warning: file %s matches more than one importer config' % filename
                        for m in matches:
                            print m
                    self.ambiguous_files.append(filename)

        if not QUIET:
            print 'Identified files to process:'
        for item in self.files_to_process:
            filename = item[0]
            registry = item[1]
            if not QUIET:
                print '%s' % (filename)

    def process_files(self, username=None, password=None):
        for pair in self.files_to_process:
            filename, registry = pair
            if 'from' in registry:
                if registry['from'] == 'filename':
                    self.get_timestamp_from_filename(filename, registry)
                elif registry['from'] == 'csv':
                    self.get_timestamps_from_csv(filename, registry)
                elif registry['from'] == 'exif':
                    self.get_timestamp_from_exif(filename, registry)
                elif registry['from'] == 'doc':
                    self.get_timestamp_from_doc(filename, registry)
                elif registry['from'] == 'text':
                    # TODO IMPLEMENT for example for html parsing
                    pass
                else:
                    raise ValueError('Invalid from argument: %s' % registry['from'])

    def get_timestamp_from_filename(self, full_filename, registry):
        # Some filenames contain float seconds, some int microseconds

        filename = os.path.basename(full_filename)
        format = registry['format']
        regex = None
        if 'regex' in registry:
            regex = registry['regex']

        timestamp = get_timestamp_from_filename(filename, format, regex)
        self.timestamps.append(('%s: %s' % (registry['name'], filename), timestamp))

    def get_timestamps_from_csv(self, filename, registry):
        delimiter = ','
        if 'delimiter' in registry:
            delimiter_string = registry['delimiter']
            if len(delimiter_string) > 1:
                if 't' in delimiter_string:
                    delimiter = '\t'
            else:
                delimiter = delimiter_string

        if 'column_number' in registry:
            column = '%d' % registry['column_number']
            fieldnames = ['%d' % n for n in range(int(column) + 1)]
            reader = DictReader(open(filename, 'r'), delimiter=delimiter,
                                fieldnames=fieldnames)
        else:
            column = registry['column_name']
            reader = DictReader(open(filename, 'r'), delimiter=delimiter)

        for row in reader:
            timestamp_string = row[column]
            if timestamp_string:
                if registry['format'] == 'seconds':
                    timestamp = datetime.datetime.utcfromtimestamp(float(timestamp_string)).replace(tzinfo=pytz.UTC)
                elif registry['format'] == 'microseconds':
                    timestamp = datetime.datetime.utcfromtimestamp(1e-6 * int(timestamp_string)).replace(tzinfo=pytz.UTC)
                elif registry['format'] == 'iso8601':
                    timestamp = dateparser(timestamp_string)
                    # print 'timezone:', timestamp.tzname()
                else:
                    raise ValueError('Invalid type for csv timestamp: %s' % registry['format'])

                self.timestamps.append((registry['name'], timestamp))

    def get_timestamp_from_exif(self, filename, registry):
        img = PIL.Image.open(filename)
        exif_data = img._getexif()
        exif = {
            PIL.ExifTags.TAGS[k]: v
            for k, v in img._getexif().items()
            if k in PIL.ExifTags.TAGS
        }
        # Note there is no timezone info standard defined for EXIF,
        # although there is a standard for GPS time in GPSInfo,
        # but our robot is in a cave so none of the cameras will have GPSInfo
        timestamp = dateparser(exif['DateTimeOriginal']).replace(tzinfo=pytz.utc)
        self.timestamps.append((registry['name'], timestamp))

    def get_timestamp_from_doc(self, filename, registry):
        """
        This supports custom metadata in a png image which includes a date with time.
        :param filename:
        :param registry:
        :return:
        """
        info = PNGinfo(filename)
        for entry in info.text:
            match = re.search('date:(\D+)([\d\-T\:]+)', entry)
        if match:
            timestamp = dateparser(match.group(2)).astimezone(pytz.utc)
            self.timestamps.append((registry['name'], timestamp))
        else:
            raise ValueError('Cannot parse DOC timestamp')

    def print_stats(self):
        print 'Found %d files configured to ignore' % len(self.ignored_files)
        print 'Found %d ambiguous files, matched more than one config rule' % len(self.ambiguous_files)
        print 'Found %d unmatched files, matched no config rule' % len(self.unmatched_files)
        if len(self.files_to_process) > 0:
            print 'Found %d files to process' % len(self.files_to_process)

    def plot_times(self,pdffile):
        # Convert list of tuples of source name, timestamp to a dictionary of source name key, timestamp list value
        plot_data = {}
        for name,timestamp in self.timestamps:
            if name not in plot_data.keys():
                plot_data[name] = []
            plot_data[name].append(timestamp)

        # decimate big datasets because otherwise the plot is kinda unmanageable
        for k in plot_data.keys():
            if len(plot_data[k])>1000:
                print 'there were', len(plot_data[k]), k
                plot_data[k].sort()
                n = len(plot_data[k])/1000
                newlist = plot_data[k][0::n]
                # just in case we need to see the last one...
                newlist.append(plot_data[k][-1])
                plot_data[k] = newlist
                print 'now there are', len(plot_data[k]), k

        import matplotlib as mpl
        mpl.use('pdf')
        from matplotlib import pyplot as plt
        import matplotlib.dates as mdates
        from matplotlib.dates import DateFormatter
        fig, ax = plt.subplots()
        locs = []
        labels = []
        for idx,name in enumerate(plot_data.keys()):
            locs.append(idx)
            labels.append(name)
            y = [idx]*len(plot_data[name])
            x = plot_data[name]
            plt.plot(x,y,'o')
        plt.yticks(locs,labels)

        # ax.format_xdata = mdates.DateFormatter('%Y.%m.%d %H:%M:%S')
        myFmt = mdates.DateFormatter('%Y.%m.%d %H:%M:%S')
        ax.xaxis.set_major_formatter(myFmt)
        ax.margins(0.05)
        fig.autofmt_xdate()
        fig.tight_layout()
        plt.savefig(pdffile)


def get_timestamp_from_dirname(dirname, pattern):
    match = re.search(pattern, dirname)
    if match:
        timestamp = datetime.datetime.utcfromtimestamp(1e-6*int(match.group(1))).replace(tzinfo=pytz.utc)
        return timestamp
    return None


if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser('usage: %prog [options] <source_root_dir_for_flight>')
    parser.add_option('-c', '--configfile',
                      help='yaml config file for getting timestamps from files')
    parser.add_option('-t', '--test',
                      action='store_true', default=False,
                      help='Run in test mode')
    parser.add_option('-f', '--force',
                      action='store_true', default=False,
                      help='Force creation of a flight even if invalid timestamps are found')
    parser.add_option('-m', '--make_flight',
                      action='store_true', default=False,
                      help='Create a flight for the given directory')
    parser.add_option('-p', '--plot',
                      action='store_true', default=False,
                      help='Plot results to pdf, filename uses the import directory name')
    parser.add_option('-q', '--quiet',
                      action='store_true', default=False,
                      help='Silence most printouts, only include times')
    parser.add_option('-d', '--dirname_pattern', default=None,
                      help='pattern regex for dirname matching')

    opts, args = parser.parse_args()

    if len(args)<1:
        parser.print_help()
        sys.exit(0)

    global QUIET
    QUIET = opts.quiet

    # the top level directory should contain all the data for a flight
    flight_dir = args[0]
    print 'flight_dir: %s' % flight_dir

    # just the final directory name, not the full path to it
    # have to accommodate the path ending in '/' or not
    basename = os.path.basename(os.path.normpath(flight_dir))
    print 'basename: %s' % basename

    # Get start time from root directory
    start_time = None
    if opts.dirname_pattern:
        start_time = get_timestamp_from_dirname(flight_dir, opts.dirname_pattern)
        if start_time is None:
            print 'ERROR: Expected the source root to be in the form %s' % opts.dirname_pattern
            raise ValueError('Cannot get a valid timestamp from source root %s' % flight_dir)
        if not QUIET:
            print 'Flight dir timestamp is %s' % start_time

    # If we were given a timestamp validation config, go validate timestamps for all data
    if opts.configfile is not None:
        validator = TimestampValidator(opts.configfile)
        validator.find_files(flight_dir)
        if not opts.test:
            validator.process_files()
        if not QUIET:
            validator.print_stats()
        timestamps = [t[1] for t in validator.timestamps]
        first_data_time = min(timestamps)
        last_data_time = max(timestamps)
        print 'Timestamps for', basename
        if start_time:
            print 'start time:     ', start_time
        print 'first data time:', first_data_time
        print 'last data time: ', last_data_time

        if start_time:
            for name, timestamp in validator.timestamps:
                if timestamp < start_time:
                    print 'Error: %s in %s is before start time %s' % (timestamp, name, start_time)

        # If we were asked to create a flight, create it
        # Note that we cannot make a flight with an end time if we didn't get a config
        if opts.make_flight:
            try:
                # get or create a flight for that source root directory
                import django
                django.setup()
                from django.conf import settings
                from xgds_core.flightUtils import get_or_create_flight_with_source_root

                dirname = os.path.basename(os.path.normpath(flight_dir))
                suffix = dirname[dirname.find('_'):]
                local_start_time = start_time.astimezone(pytz.timezone(settings.TIME_ZONE))
                name = '%s%s' % (local_start_time.strftime('%Y%m%d'), suffix)

                flight = get_or_create_flight_with_source_root(flight_dir, start_time, last_data_time, name)
                print 'Created or got flight %s' % flight
            except ImportError as e:
                print 'Error: Cannot create a flight'
                print e

        # If we were asked to make a plot, make it
        if opts.plot:
            pdffile = 'timestamps_%s.pdf' % basename
            print 'plotting to', pdffile
            validator.plot_times(pdffile)
