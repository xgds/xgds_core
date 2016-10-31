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

/*
 * All of this depends on moment.js and moment-timezone.js, and timezoneDefs.js
 */

/*
 * Convert a utc moment time into the destination time zone.
 */
getLocalTime = function(utctime, destTimeZone) {
	moment.tz.setDefault('Etc/UTC');
	return moment(utctime).tz(destTimeZone);
};

DEFAULT_TIME_FORMAT = "MM/DD/YY HH:mm:ss z"

/*
 * Convert a utc moment time into the destination timezone and format it.
 */
getLocalTimeString = function(utctime, destTimeZone, format) {
	if (format === undefined){
		format = DEFAULT_TIME_FORMAT;
	}
	if (utctime === undefined){
		return '';
	}
	var localTime = getLocalTime(utctime, destTimeZone);
	if (localTime != undefined && localTime != null){
		return localTime.format(format);
	} else {
		alert("Tell the system administrators that something is wrong with moment timezone.");
	}
};

getUTCTime = function(localtime, localTimeZone){
	var zone = moment.tz.zone(localTimeZone);
	var hoursOffset = zone.parse(localtime)/60;
	var localtimeoffset = localtime + '-' +  hoursOffset + ':00';
	var theMoment = moment(localtimeoffset, 'MM/DD/YY HH:mm:ssZ');
	theMoment.tz(localTimeZone);
	return theMoment.tz('Etc/UTC');
//	
//	return moment(localtime).tz(localTimeZone).tz('Etc/UTC')
}