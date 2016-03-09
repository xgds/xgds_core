// __BEGIN_LICENSE__
//Copyright (c) 2015, United States Government, as represented by the 
//Administrator of the National Aeronautics and Space Administration. 
//All rights reserved.
//
//The xGDS platform is licensed under the Apache License, Version 2.0 
//(the "License"); you may not use this file except in compliance with the License. 
//You may obtain a copy of the License at 
//http://www.apache.org/licenses/LICENSE-2.0.
//
//Unless required by applicable law or agreed to in writing, software distributed 
//under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR 
//CONDITIONS OF ANY KIND, either express or implied. See the License for the 
//specific language governing permissions and limitations under the License.
// __END_LICENSE__

// this depends on moment.js, moment-timezone.js,  jqueryui-timepicker-addon/dist/jquery-ui-timepicker-addon.min.js

/*
 * Add a date time picker on an input field
 */
function addDateTimePicker(element_id, defaultTimeZone){
	$( "#" + element_id ).datetimepicker({'controlType': 'select',
        'oneLine': true,
        'showTimezone': false,
        'timezone': moment.tz(defaultTimeZone).utcOffset()
       });
}

/*
 * get the time from the date time picker and return it in utc time.
 */
function getUtcTime(element_id, defaultTimeZone){
	moment.tz.setDefault(defaultTimeZone);
    var tzified = moment.tz($('#' + element_id).val(), 'MM/DD/YYYY HH:mm', defaultTimeZone);
    var theUtc = tzified.utc().format('MM/DD/YYYY HH:mm');
    return theUtc;
}