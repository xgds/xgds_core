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

@register.simple_tag(name='typeahead')
def typeahead(url, input_id):
    result = ('''
<script type="text/javascript">
    var theInput = $('#%(input_id)s');
    if (theInput.length > 0) {
        theInput.addClass("typeahead");
        var bloodhound = bloodhound || {};
        var key = "%(input_id)s";
        if (_.isUndefined(bloodhound[key])) {
              bloodhound[key]  = new Bloodhound({datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
                                                 queryTokenizer: Bloodhound.tokenizers.whitespace,
                                                 prefetch: {cache: false, 
                                                            ttl: 1,
                                                            url: "%(url)s"
                                                           }
                                                      });  
              bloodhound[key].initialize();
            }
        theInput.typeahead({hint: true,
                            highlight: true,
                            minLength: 1
                           },
                            {name: "%(input_id)s",
                            displayKey: 'name',
                            valueKey: 'id',
                            source: bloodhound[key].ttAdapter()
                        }).bind("typeahead:selected", function(obj, datum, name) {
                            $(this).data("value", datum.id);
                            });
    }
</script>''' % {'input_id':input_id,
                'url':url})
    return mark_safe(result)
    
@register.simple_tag(name='typeahead_model')
def typeahead_model(model_name, input_id):
    ''' model_name is fully qualified ie basaltApp.BasaltFlight
    '''
    url = reverse('xgds_core_model_json', kwargs={'model_name':model_name})
    return typeahead(url, input_id)

@register.simple_tag(name='typeahead_user')
def typeahead_user(input_id):
    url = reverse('xgds_core_users_json')
    return typeahead(url, input_id)
        