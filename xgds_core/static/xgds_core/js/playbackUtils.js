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

//TODO better to have the server provide
moment.tz.add([ 'America/Los_Angeles|PST PDT|80 70|0101|1Lzm0 1zb0 Op0',
		'America/New_York|EST EDT|50 40|0101|1Lz50 1zb0 Op0',
		'Etc/UTC|UTC|0|0|' ]);

jQuery(function($) {
	var windowWidth = $(window).width();
	$(window).resize(function() {
		if (windowWidth != $(window).width()) {
			return;
		}
	});
});

$.extend(playback, {
	displayTZ : 'Etc/UTC', // TODO override this

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
		var parsedMoment = moment(input,'hh:mm:ss');
		if (!parsedMoment.isValid()){
			return null;
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


	getLocalTimeString : function(utctime) {
		var pdttime = utctime.tz(playback.displayTZ)
		var time = pdttime.format("HH:mm:ss z")
		return time;
	},

	setTimeLabel : function(datetime) {
		$('#sliderTimeLabel').text(playback.getLocalTimeString(datetime));
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
		try {
			var seekButton = $("#seekButton");
			seekButton.on('click', function(e) {
				playback.seekCallback();
			});
		} catch (e){
			// pass, may not have the input
		}
	}

	

});