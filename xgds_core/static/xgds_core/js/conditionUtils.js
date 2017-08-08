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

condition = {}; //namespace

$.extend(condition, {
	lastCondition: undefined,
	initialize: function() {
		condition.subscribe();
		condition.getCurrentConditions();
	},
	subscribe: function() {
		sse.subscribe('condition', condition.handleConditionEvent)
	},
	handleConditionEvent: function(event){
		try {
			var receivedCondition = JSON.parse(event.data);
			if ('data' in receivedCondition){
				receivedCondition = JSON.parse(receivedCondition.data);
			}
			condition.updateColor(receivedCondition);
			$('#conditionDiv').html(condition.getMessage(receivedCondition));
		} catch(err){
			// bad stuff
		}
	},
	updateColor: function(received) {
		// TODO replace this function with one that processes your status the way you want.
//		var ch = received[1].fields;
//		var cdiv = $('#conditionDiv');
//		cdiv.removeClass (function (index, className) {
//		    return (className.match (/(^|\s)alert-\S+/g) || []).join(' ');
//		});
//		cdiv.addClass('alert-info');
	},
	getPrintableTime: function(theTime, theTimeZone){
		var theMoment = moment.tz(theTime, "Etc/UTC");
		theMoment.tz(theTimeZone);
		return theMoment.format('HH:mm:ss');
	},
	getMessage: function(received) {
		// TODO replace this function with one that creates the message the way you want
		var c = received[0].fields;
		var ch = received[1].fields;
		
		// SOURCE(TIME): NAME STATUS
		var result = c.source;
		result += ' (' + condition.getPrintableTime(ch.source_time, c.timezone) + '): '; // todo convert to the timezone
		result += c.name;
		result += ' <strong>' + ch.status + '</strong>';
		return result;
		
	},
	getCurrentConditions: function() {
		$.ajax({
            url: '/xgds_core/condition/activeJSON',
            dataType: 'json',
            success: $.proxy(function(data) {
            	if (!_.isEmpty(data)){
            		var fakeEvent = {'data': {'data': data}};
            		condition.handleConditionEvent(fakeEvent);
            	}
            }, this)
          });
	}
});