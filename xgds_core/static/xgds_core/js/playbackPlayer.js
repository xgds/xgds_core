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
	stopListeners: [],
	playListeners: [],
	playbackSpeed: 1,
	endTime: undefined,
	displayTZ : 'Etc/UTC',
	hasMasterSlider: true,
	initialize: function(options) {
		// check for web workers
		if (!window.Worker) { 
			alert("Browser will not support playback.  Please use Chrome.");
			$('#controller_div').hide();
			return;
		}

		if (!_.isUndefined(options.time_control_path)){
			playback.time_control_path = options.time_control_path;
		} else {
			playback.time_control_path = '/static/xgds_core/js/playbackTimeControl.js';
		}
		
		if (!_.isUndefined(options.displayTZ)){
			playback.displayTZ = options.displayTZ;
		}

		// register start and end time functions
		if (!_.isUndefined(options.getStartTime)){
			playback.getStartTime = options.getStartTime;
		}
		playback.startTime = moment(playback.getStartTime()).tz(playback.displayTZ);
		if (!_.isUndefined(options.getEndTime)){
			playback.getEndTime = options.getEndTime;
		}
		var endTime = playback.getEndTime();
		if (!_.isUndefined(endTime)){
			playback.endTime = moment(endTime).tz(playback.displayTZ);
		}
		playback.currentTime = moment(playback.startTime);
		
		if ('slider' in options){
			playback.hasMasterSlider = options.slider;
		}
		if (playback.hasMasterSlider){
			playback.setupSlider();
		}
		
		if (!_.isUndefined(options.playbackSpeed)){
			playback.playbackSpeed = options.playbackSpeed;
		}

		playback.setupTimer();
		playback.setTimeLabel(playback.currentTime);
		playback.setupSpeedInput();
		playback.setupSeekButton();
		try {
            app.vent.on('playback:setCurrentTime', function (currentTime) {
                playback.setCurrentTime(currentTime);
            });
        } catch (error) {
			// ulp.  There may not be an app on this page.
		}

	},
	addStopListener: function(stopListener) {
		playback.stopListeners.push(stopListener);
		if (!playback.playFlag) {
			stopListener(playback.currentTime);
		}
	},
	removeStopListener: function(stopListener) {
		playback.stopListeners = _.without(playback.stopListeners, stopListener);
	},
	callStopListeners: function(currentTime){
		_.each(this.stopListeners, function(sl) {
			sl(currentTime);
		});
	},
	addPlayListener: function(playListener) {
		playback.playListeners.push(playListener);
		if (playback.playFlag) {
			playListener(playback.currentTime);
		}
	},
	removePlayListener: function(playListener) {
		playback.playListeners = _.without(playback.playListeners, playListener);
	},
	callPlayListeners: function(currentTime){
		_.each(this.playListeners, function(sl) {
			sl(currentTime);
		});
	},
	addListener: function(listener) {
		playback.listeners.push(listener);
		listener.initialize();
	},
	
	removeListener: function(listener) {
		// stop it first
		try {
			listener.pause();
		} catch (err){
			// noop, there may not be a pause function
		}
		playback.listeners = _.without(playback.listeners, listener);
	},
	
	setupTimer: function(){
		playback.timerWorker = new Worker(playback.time_control_path);
		playback.timerWorker.addEventListener("message", function (event) {
			playback.currentTime = moment(event.data).tz(playback.displayTZ);
			// check if we are at the end
			if (playback.endTime !== undefined && playback.currentTime.isSameOrAfter(playback.endTime)){
				playback.pauseButtonCallback();
			} else {
		    	if (playback.hasMasterSlider){
		    		playback.setTimeLabel(playback.currentTime);
		    	}
		    	playback.updateListeners(playback.currentTime);
			}
	    }, false);
		playback.timerWorker.postMessage(['setPlaybackSpeed', playback.playbackSpeed]);
		playback.timerWorker.postMessage(['setCurrentTime', playback.currentTime.toISOString()]);
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
			try {
                listener.pause();
            } catch (err){
				// noop, there may not be a pause function
			}
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
	seekCallback : function() {
		var seekTimeStr = $('#seekTime').val();
		if ((seekTimeStr == null) || (Object.keys(playback.listeners).length < 1)) {
			return;
		}
		playback.seekHelper(seekTimeStr);
		app.vent.trigger('seekTime', seekTimeStr);
	},

	playButtonCallback : function() {
		$('#playbutton').addClass("active");
		$('#pausebutton').removeClass("active");
		playback.doPlay();
	},

	pauseButtonCallback : function() {
		$('#pausebutton').addClass("active");
		$('#playbutton').removeClass("active");
		playback.doPause();
	}, 
	
	doPause: function() {
		if (!playback.playFlag) {
			return;
		}
		playback.timerWorker.postMessage(['setPaused', true]);
		playback.playFlag = false;
		playback.pauseListeners();
		playback.callStopListeners(playback.currentTime);
	},
	
	doPlay: function() {
		if (playback.playFlag) {
			return;
		}
		playback.playFlag = true;
		playback.startListeners(playback.getCurrentTime());
		playback.timerWorker.postMessage(['setPaused',false]);
		playback.timerWorker.postMessage(['runTime']);
		playback.callPlayListeners(playback.currentTime);
	},
	
	setPlaybackSpeed: function(speed) {
		playback.playbackSpeed = speed;
		playback.timerWorker.postMessage(['setPlaybackSpeed',speed]);
	},
	
	setCurrentTime: function(currentTime){
		playback.currentTime = moment(currentTime).tz(playback.displayTZ); 
		playback.timerWorker.postMessage(['setCurrentTime',playback.currentTime.toISOString()]);
		playback.updateListeners(playback.currentTime);
	}, 
	
	updateStartTime: function(newStartTime){
		if (playback.startTime == newStartTime){
			return false;
		}
		playback.startTime = moment(newStartTime).tz(playback.displayTZ);
		if (playback.hasMasterSlider){
			playback.setSliderStartTime(playback.startTime);
		}
		if (playback.currentTime.isBefore(playback.startTime)){
			playback.currentTime = playback.startTime;
		}
		return true;

	},
	
	updateEndTime: function(newEndTime){
		playback.endTime = moment(newEndTime).tz(playback.displayTZ);
		if (playback.hasMasterSlider){
			playback.setSliderEndTime(playback.endTime);
		}
		if (playback.currentTime.isAfter(playback.endTime)){
			playback.currentTime = playback.endTime;
			if (playback.playFlag){
				playback.pauseButtonCallback();
			}
		}
	},
	
	// for testing
	getStartTime : function() {
		return moment().utc()
	},

	// for testing
	getEndTime : function() {
		var nowMoment = moment(moment.now());
		nowMoment.add(1, 'hour')
		return nowMoment;
	}
	

});