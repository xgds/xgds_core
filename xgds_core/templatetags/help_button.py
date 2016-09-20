# __BEGIN_LICENSE__
#Copyright (c) 2015, United States Government, as represented by the 
#Administrator of the National Aeronautics and Space Administration. 
#All rights reserved.
# __END_LICENSE__

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
        return None
