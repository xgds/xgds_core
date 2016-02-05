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

$.extend(playback, {
	listeners: [],
	playbackSpeed: 1,
	initialize: function(options) {
		// check for web workers
		if (!window.Worker) { 
			alert("Browser will not support playback.  Please use Chrome.");
			$('#controller_div').hide();
			return;
		} 
		
		// register start and end time functions
		if (options.getEndTime){
			playback.getEndTime = options.endTime;
		}
		if (options.getStartTime){
			playback.getStartTime = options.startTime;
		}
		playback.currentTime = moment(playback.getStartTime());
		
		if (options.slider){
			playback.setupSlider();
			playback.hasMasterSlider = true;
		} else {
			playback.hasMasterSlider = false;
		}
		
		if (options.playbackSpeed){
			playback.playbackSpeed = options.playbackSpeed;
		}
		playback.setupTimer();
		playback.setupSpeedInput();
	},
	
	addListener: function(listener) {
		playback.listeners.push(listener);
	},
	
	removeListener: function(listener) {
		// stop it first
		listener.pause();
		playback.listeners = _.without(playback.listeners, listener);
	},
	
	setupTimer: function(){
		playback.timerWorker = new Worker('/static/xgds_core/js/playbackTimeControl.js');
		playback.timerWorker.addEventListener("message", function (event) {
			playback.currentTime = moment(event.data);
	    	if (playback.hasMasterSlider){
	    		playback.setTimeLabel(playback.currentTime);
	    	}
	    	playback.updateListeners(playback.currentTime);
	    }, false);
		playback.timerWorker.postMessage(['setPlaybackSpeed', playback.playbackSpeed]);
		playback.timerWorker.postMessage(['setCurrentTime', playback.currentTime.format()]);
	},

	getCurrentTime : function() {
		return playback.currentTime;
	},

	startListeners : function() {
		var currentTime = playback.getCurrentTime();
		for (var i=0; i < playback.listeners.length; i++) {
			var listener = playback.listeners[i];
			listener.start(currentTime);
		}
	},
	
	updateListeners : function(currentTime) {
		for (var i=0; i < playback.listeners.length; i++) {
			var listener = playback.listeners[i];
			listener.update(currentTime);
		}
	},

	pauseListeners : function() {
		for (var i=0; i < playback.listeners.length; i++) {
			var listener = playback.listeners[i];
			listener.pause();
		}
	},

	/**
	 * Only called once onReady. Reads offset from URL hash
	 * (i.e. http://mvp.xgds.snrf/playback/archivedImageStream/2014-06-19#19:00:00)
	 * and seeks to that time.
	 */
	seekFromUrlOffset : function() {
		var timestr = window.location.hash.substr(1); //i.e. 19:00:00
		seekHelper(timestr);
	},

	/**
	 * Updates the player and the slider times based on
	 * the seek time value specified in the 'seek' text box.
	 */
	seekCallBack : function() {
		var seekTimeStr = $('#seekTime').val();
		if ((seekTimeStr == null)
				|| (Object.keys(playback.listeners).length < 1)) {
			return;
		}
		playback.seekHelper(seekTimeStr);
	},

	playButtonCallback : function() {
		if (playback.playFlag) {
			return;
		}
		playback.playFlag = true;
		$('#playbutton').addClass("active");
		$('#pausebutton').removeClass("active");

		playback.startListeners(playback.getCurrentTime());
		playback.timerWorker.postMessage(['setPaused',false]);
		playback.timerWorker.postMessage(['runTime']);
	},

	pauseButtonCallback : function() {
		if (!playback.playFlag) {
			return;
		}
		playback.timerWorker.postMessage(['setPaused', true]);
		playback.playFlag = false;
		$('#pausebutton').addClass("active");
		$('#playbutton').removeClass("active");
		playback.pauseListeners();
	}, 
	
	setPlaybackSpeed: function(speed) {
		playback.playbackSpeed = speed;
		playback.timerWorker.postMessage(['setPlaybackSpeed',speed]);
	}

});