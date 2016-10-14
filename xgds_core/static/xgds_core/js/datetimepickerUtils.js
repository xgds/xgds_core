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
function addDateTimePicker(element_id, defaultTimeZone, showTimezone){
	showTimezone = showTimezone || false;
	var options = {'controlType': 'select',
	        	   'oneLine': true,
	        	   'showTimezone': showTimezone,
	        	   'timezone': moment.tz(defaultTimeZone).utcOffset(),
	        	   'format': 'd/m/Y H:M zzz'
	       			};
	if (showTimezone){
		var timezoneList = []; 
		var names = moment.tz.names();
		for (var i=0; i < names.length; i++){
			var offset = moment.tz(names[i]).utcOffset();
			timezoneList.push({label:names[i], value:offset});
		}
		options['timezoneList'] = timezoneList;
	}
	$( "#" + element_id ).datetimepicker(options);
}

function addDateTimePickers(){
	// add timezoneless utc date time pickers on anything with datetimepicker class
	var options = {'controlType': 'select',
     	   		    'oneLine': true,
     	   		    'showTimezone': false,
     	   		    'format': 'd/m/Y H:M zzz'
    			};
	$( ".datetimepicker" ).datetimepicker(options);
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