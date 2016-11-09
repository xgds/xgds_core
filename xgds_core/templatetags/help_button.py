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

from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(name='help_button')
def help_button(help_content_path, help_title):
    try:
        url = reverse('help_popup', kwargs={'help_content_path':help_content_path,
                                            'help_title':str(help_title)})
        result = "<a href='#' onclick='help.openPopup(\"" + url + "\")' class='help_button'><i class='fa fa-question-circle-o fa-2' aria-hidden='true'></i></a>"
        return mark_safe(result)
    except:
        # if the url is not found do not include the help button
        return ""