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

import django
django.setup()


def main():
    import optparse

    parser = optparse.OptionParser('usage: -c config -i input')
    parser.add_option('-c', '--config', help='path to config file (yaml)')
    parser.add_option('-i', '--input', help='path to csv file to import')
    parser.add_option('-h', '--vehicle', help='name of vehicle')
    parser.add_option('-f', '--flight', help='name of flight')

    opts, args = parser.parse_args()

    if not opts.config:
        parser.error('config is required')
    if not opts.input:
        parser.error('input is required')

    result = csvImporter.do_import(parser.config, parser.input, parser.vehicle, parser.flight)
    print 'loaded %d ' % result


if __name__ == '__main__':
    main()
