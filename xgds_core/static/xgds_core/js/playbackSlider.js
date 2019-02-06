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
	
	setSliderTime : function(datetime) {
		var seconds = datetime.unix();
		playback.masterSlider.slider('value', seconds);
		playback.setTimeLabel(datetime);
	},
	
	/**
	 * Slider Callback:
	 * update slider time text when moving slider.
	 */
	uponSliderMoveCallback : function(event, ui) {
		//update slider time label on top
		playback.movingSlider = true;
		if (playback.playFlag){
			playback.wasPlaying = true;
			playback.doPause();
		}
		var sliderTime = new Date(ui.value * 1000);
		playback.setTimeLabel(moment(sliderTime));
	},

	/**
	 * Slider Callback:
	 *    get the current slider position and do
	 *    offset = slider position - start time
	 *    update the site times to equal slider position.
	 */
	uponSliderStopCallback : function(event, ui) {
		var currTime = playback.masterSlider.slider('value'); //in seconds
		var currMoment = moment(new Date(currTime * 1000));
		playback.setCurrentTime(currMoment);
		playback.movingSlider = false;
		if (!playback.playFlag){
			if (playback.wasPlaying){
				playback.doPlay();
				playback.wasPlaying = false;
			}
		}
		playback.callStopListeners(currMoment);
	},
	
	setSliderStartTime: function(startTime){
		playback.masterSlider.slider( "option", "min", startTime.unix() );
	},
	
	setSliderEndTime: function(endTime){
		playback.masterSlider.slider( "option", "max", endTime.unix() );
	},

	/**
	 * initialize master slider with range (start and end time from registered methods)
	 */
	setupSlider : function() {
		if (playback.endTime != undefined) {
			playback.masterSlider = $('#masterSlider').slider({
				step : 1,
				min : playback.startTime.unix(),
				max : playback.endTime.unix(),
				stop : playback.uponSliderStopCallback,
				slide : playback.uponSliderMoveCallback,
				range : false //'min'
			});
		}
		playback.addListener(playback.sliderListener);
	},
	
	sliderListener: {
		lastUpdate: undefined,
		initialize: function() {
			//noop
		},
		doSetTime: function(currentTime){
			playback.sliderListener.lastUpdate = moment(currentTime);
			playback.setSliderTime(playback.currentTime);
		},
		start: function(currentTime){
			playback.sliderListener.doSetTime(currentTime);
		},
		update: function(currentTime){
			if (playback.sliderListener.lastUpdate === undefined){
				playback.sliderListener.doSetTime(currentTime);
				return;
			}
			var delta = currentTime.diff(playback.sliderListener.lastUpdate);
			if (Math.abs(delta) >= 1000) {
				playback.sliderListener.doSetTime(currentTime);
			}
		},
		pause: function() {
			// noop
		}
	}

});