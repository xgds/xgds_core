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

playback = {}; //namespace

jQuery(function($) {
	var windowWidth = $(window).width();
	$(window).resize(function() {
		if (windowWidth != $(window).width()) {
			return;
		}
	});
});

$.extend(playback, {
	/**
	 * Helper for converting json datetime object to javascript date time
	 */
	toJsDateTime : function(jsonDateTime) {
		if ((jsonDateTime) && (jsonDateTime != 'None') && (jsonDateTime != '')
				&& (jsonDateTime != undefined)) {
			//need to subtract one from month since Javascript datetime indexes month  0 to 11.
			jsonDateTime.month = jsonDateTime.month - 1;
			return new Date(Date.UTC(jsonDateTime.year, jsonDateTime.month,
					jsonDateTime.day, jsonDateTime.hour, jsonDateTime.min,
					jsonDateTime.seconds, 0));
		}
		return null;
	},

	/**
	 * Used by both seekCallback and seekFromUrlOffset
	 * to seek all players to given time.
	 */
	seekHelper : function(seekTimeStr) {
		var seekTime = playback.seekTimeParser(seekTimeStr);
		
		if (seekTime != null){
			var newTime = moment(playback.currentTime); // start with the current date
			
			// update the time
			newTime.hour(seekTime.hour());
			newTime.minute(seekTime.minute());
			newTime.second(seekTime.second());
			
			// check the time is within range
			if (playback.endTime != undefined){
				var range = new DateRange(playback.startTime, playback.endTime);
				if (range.contains(newTime)) {
					playback.setCurrentTime(newTime);
					return;
				}
			}
			alert("Invalid jump to time.");
		}
	},

	/**
	 * Helper to parse seektime into hours, minutes, seconds
	 */
	seekTimeParser : function(input) {
		var parsedMoment = moment(input,'MM/DD/YY hh:mm:ss');
		if (!parsedMoment.isValid()){
			parsedMoment = moment(input,'hh:mm:ss');
		} else {
			return parsedMoment;
		}
	},

	padNum : function(num, size) {
		var s = num + '';
		while (s.length < size) {
			s = '0' + s;
		}
		return s;
	},


	getLocalTimeString : function(utctime, format) {
		var localTime = utctime.tz(playback.displayTZ)
		var time = localTime.format(format)
		return time;
	},

	setTimeLabel : function(datetime) {
		$('#sliderTimeLabel').text(getLocalTimeString(datetime, playback.displayTZ, DEFAULT_TIME_FORMAT));
	},
	
	setupSpeedInput: function() {
		try {
			var speedInput = $("#playbackSpeed");
			speedInput.on('input', function(e) {
				var newSpeed = parseFloat(e.currentTarget.value);
				if (!isNaN(newSpeed)){
					playback.setPlaybackSpeed(newSpeed);
				}
			});
		} catch (e){
			// pass, may not have the input
		}
	},
	
	setupSeekButton: function() {
		/// set up the seek button and contents of the jump to
		try {
			var seekButton = $("#seekButton");
			seekButton.on('click', function(e) {
				playback.seekCallback();
			});
			var seekTime = $("#seekTime");
			seekTime.attr('placeholder', playback.startTime.format('MM/DD/YY') + ' hh:mm:ss');
			
		} catch (e){
			// pass, may not have the input
		}
	}

	

});