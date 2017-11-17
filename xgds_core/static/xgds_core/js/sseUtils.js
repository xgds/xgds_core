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

sse = {}; //namespace

$.extend(sse, {
	initialize: function() {
		sse.heartbeat();
	},
	heartbeat: function() {
		setInterval(sse.checkHeartbeat, 11000);
		sse.subscribe('heartbeat', sse.connectedCallback, 'sse');
	},
	checkHeartbeat: function() {
		var connected = false
		if (sse.lastHeartbeat != undefined){
			var diff = moment.duration(moment().diff(sse.lastHeartbeat));
			if (diff.asSeconds() <= 10) {
				connected = true;
			}
		}
		if (!connected){
			sse.disconnectedCallback();
		}
	},
	connectedCallback: function(event){
		try {
			sse.lastHeartbeat = moment(JSON.parse(event.data).timestamp);
			var cdiv = $("#connected_div");
			if (cdiv.hasClass('alert-danger')){
				cdiv.removeClass('alert-danger');
				cdiv.addClass('alert-success');
				var c = $("#connected");
				c.removeClass('fa-bolt');
				c.addClass('fa-plug');
			}
		} catch(err){
			// in case there is no such page
		}
	},
	disconnectedCallback: function(event){
		try {
			var cdiv = $("#connected_div");
			if (cdiv.hasClass('alert-success')){
				cdiv.removeClass('alert-success');
				cdiv.addClass('alert-danger');
				var c = $("#connected");
				c.addClass('fa-bolt');
				c.removeClass('fa-plug');
			}
		} catch(err){
			// in case there is no such page
		}
	},
	allChannels: function(theFunction, channels){
		for (var i=0; i<channels.length; i++){
			var channel = channels[i];
			if (channel != 'sse') {
				theFunction(channel);
			}
		}
	},
	activeChannels: undefined,
	getChannelsUrl: '/xgds_core/sseActiveChannels',
	getChannels: function(url) {
		// get the active channels over AJAX
		if (sse.activeChannels === undefined){
			$.ajax({
	            url: sse.getChannelsUrl,
	            dataType: 'json',
	            async: false,
	            success: $.proxy(function(data) {
	                sse.activeChannels = data;
	            }, this)
	          });
		}
		return sse.activeChannels;
	},
	parseEventChannel: function(event){
		return sse.parseChannel(event.target.url);
	},
	parseChannel: function(fullUrl){
		var splits = fullUrl.split('=');
		if (splits.length > 1){
			return splits[splits.length-1];
		}
		return 'sse';
	},
	subscribe: function(event_type, callback, channels) {
		if (channels != undefined) {
			if (!_.isArray(channels)) {
				channels = [channels];
			}
			for (var i=0; i<channels.length; i++){
				var channel = channels[i];
				//console.log('SUBSCRIBING TO ' + channel + ':' + event_type);

                var source = new EventSource("/sse/stream?channel=" + channel);
                source.addEventListener(event_type, callback, false);
            }
		} else {
			var allChannels = sse.getChannels();
			for (var i=0; i<allChannels.length; i++){
				var channel = allChannels[i];
				//console.log('SUBSCRIBING TO ' + channel + ':' + event_type);
				var source = new EventSource("/sse/stream?channel=" + channel);
				source.addEventListener(event_type, callback, false);
			}
		}
	}
});