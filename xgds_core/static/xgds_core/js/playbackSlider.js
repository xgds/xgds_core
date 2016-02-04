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

	getPercent : function(width, totalWidth) {
		return Math.round(width / totalWidth * 100);
	},

	/**
	 * Slider Callback:
	 * update slider time text when moving slider.
	 */
	uponSliderMoveCallBack : function(event, ui) {
		//update slider time label on top
		playback.movingSlider = true;
		playback.timerWorker.postMessage(['setPaused',true]);
		var sliderTime = new Date(ui.value * 1000);
		playback.setSliderTimeLabel(moment(sliderTime));
	},

	/**
	 * Slider Callback:
	 *    get the current slider position and do
	 *    offset = slider position - start time
	 *    update the site times to equal slider position.
	 */
	uponSliderStopCallBack : function(event, ui) {
		var currTime = playback.masterSlider.slider('value'); //in seconds
		playback.currentTime = moment(new Date(currTime * 1000)); //convert to javascript date
		playback.timerWorker.postMessage(['setCurrentTime',playback.currentTime.format()]);
		playback.timerWorker.postMessage(['setPaused',false]);
		playback.timerWorker.postMessage(['runTime']);
		playback.movingSlider = false;
	},

	// for testing
	// TODO client page must register this function
	getPlaybackStartTime : function() {
		return moment.now()
	},

	// for testing
	// TODO client page must register this function
	getPlaybackEndTime : function() {
		var nowMoment = moment(moment.now());
		nowMoment.add(1, 'hour')
		return nowMoment;
	},

	/**
	 * initialize master slider with range (start and end time from registered methods)
	 */
	setupSlider : function() {
		var endTime = playback.getPlaybackEndTime();
		var endMoment = moment(endTime);
		var startTime = playback.getPlaybackStartTime();
		var startMoment = moment(startTime);
		var duration = endMoment.diff(startMoment, 'seconds')
		if (endTime) {
			playback.masterSlider = $('#masterSlider').slider({
				step : 1,
				min : startMoment.unix(),
				max : endMoment.unix(),
				stop : playback.uponSliderStopCallBack,
				slide : playback.uponSliderMoveCallBack,
				range : 'min'
			});
			playback.setSliderTimeLabel(startMoment);
		}
	}

});