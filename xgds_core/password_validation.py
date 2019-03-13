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

from django.core.exceptions import ValidationError

ERROR_MESSAGE = 'Password must contain at least one of %s'


class SpecialCharsValidator(object):

    def __init__(self, characters="~!@#$%^&*()_+-=`;:',.<>?/"):
        self.special_characters = characters

    def validate(self, password, user=None):
        if any(char in self.special_characters for char in password):
            return None
        raise ValidationError(ERROR_MESSAGE % self.special_characters, 'special_chars_missing')

    def get_help_text(self):
        return ERROR_MESSAGE % self.special_characters