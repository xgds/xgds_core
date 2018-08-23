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

import sys
import re
from dateutil.parser import parse as dateparser
import json
import pytz

# TODO: We need this code because the PIL library currently has a bug
# where it will not extract text chunks if they follow IDAT chunks,
# even though the PNG standard does not require tEXt chunks to precede
# IDAT (there are ordering requirements, but that is not one of them).
# This code should be replaced by PIL.Image.info once that bug is
# fixed.  See: https://github.com/python-pillow/Pillow/issues/2908 for
# more details.


def to_int(binary_data):
    return int(binary_data.encode('hex'),16)

class PNGinfo():
    def __init__(self,filename):
        # Open and parse the data in a PNG
        fp = open(filename,'rb')
        file_data = fp.read()
        fp.close()

        # PNG file signature must be these exact 8 bytes:
        signature = ''.join(file_data[:8])
        if not signature==bytearray(b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'):
            raise ValueError('Image is not a valid PNG, signature mismatch')

        # extract strings from tEXt chunks and standard PNG header
        self.text = []
        self.header = {}

        # index into binary data from the file
        byteidx = 0

        # PNG chunk type code
        chunk_type = None

        while 'IEND' != chunk_type:
            # Length: 4-byte unsigned integer, number of bytes in the data field.
            chunk_length = to_int(file_data[byteidx+8:byteidx+12])
            # Chunk Type: A 4-byte type code, upper/lowercase letters (A-Z, a-z).
            chunk_type =''.join(file_data[byteidx+12:byteidx+16])
            # Chunk Data: The data, if any, can be zero length.
            chunk_data =''.join(file_data[byteidx+16:byteidx+16+chunk_length])
        
            # IHDR is always required and always at the top
            if chunk_type == 'IHDR':
                self.extract_png_header(chunk_data)
            # tEXt contains free-form strings, can me more than one, keep a list
            elif chunk_type == 'tEXt':
                self.text.append(chunk_data.decode('utf-8'))
            # There are other chunk types we don't care about at the moment

            # jump the byte index to the beginning of the next chunk
            byteidx += chunk_length + 12

    def get_text(self):
        return self.text

    def get_header(self):
        return self.header
    
    def extract_png_header(self,data):
        # The IHDR chunk must appear FIRST. It contains:
        #   Width:              4 bytes (0:3)
        #   Height:             4 bytes (4:7)
        #   Bit depth:          1 byte (8)
        #   Color type:         1 byte (9)
        #   Compression method: 1 byte (10)
        #   Filter method:      1 byte (11)
        #   Interlace method:   1 byte (12)
        self.header['Width'] = to_int(data[0:4])
        self.header['Height'] = to_int(data[4:8])
        self.header['Bit Depth'] = to_int(data[8])
        self.header['Color Type'] = to_int(data[9])
        self.header['Compression Method'] = to_int(data[10])
        self.header['Filter Method'] = to_int(data[11])
        self.header['Interlace Method'] = to_int(data[12])


if __name__=='__main__':
    pnginfo = PNGinfo(sys.argv[1])
    text = pnginfo.get_text()
    header = pnginfo.get_header()
    print 'Header:'
    print json.dumps(header, indent=4)
    print 'Comments:'
    for t in text:
        print str(t)
        match = re.search('date:(\D+)([\d\-T\:]+)',t)
        if match:
            timestamp = dateparser(match.group(2))
            print timestamp.astimezone(pytz.utc).isoformat()

