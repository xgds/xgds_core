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

sse = {}; // namespace

$.extend(sse, {
	initialize: function () {
		sse.heartbeat();
	},
	heartbeat: function () {
		setInterval(sse.checkHeartbeat, 11000);
		sse.subscribe('heartbeat', sse.connectedCallback, 'sse');
	},
	checkHeartbeat: function () {
		var connected = false
		if (sse.lastHeartbeat != undefined) {
			var diff = moment.duration(moment().diff(sse.lastHeartbeat));
			if (diff.asSeconds() <= 10) {
				connected = true;
			}
		}
		if (!connected) {
			sse.disconnectedCallback();
		}
	},
	// connectedCallback will trigger on each SS event from the "heartbeat"
	// channel, it will modify a div with ID "connected_div" and another
	// div with ID "connected" to show that we are connected and recieving
	// SS events
	connectedCallback: function (event) {
		try {
			sse.lastHeartbeat = moment(JSON.parse(event.data).timestamp);
			var cdiv = $("#connected_div");
			if (cdiv.hasClass('alert-danger')) {
				cdiv.removeClass('alert-danger');
				cdiv.addClass('alert-success');
				var c = $("#connected");
				c.removeClass('fa-bolt');
				c.addClass('fa-plug');
			}
		} catch (err) {
			// in case there is no such page
			console.log("[SSE Error] failiure in the connectedCallback function");
			console.log("[SSE Error]", err);
		}
	},
	// disconnectedCallback will trigger when the last SSE heartbeat was recieved more than
	// 10 seconds ago, it will modify a div with ID "connected_div" and another
	// div with ID "connected" to show that we are disconnected
	disconnectedCallback: function (event) {
		try {
			var cdiv = $("#connected_div");
			if (cdiv.hasClass('alert-success')) {
				cdiv.removeClass('alert-success');
				cdiv.addClass('alert-danger');
				var c = $("#connected");
				c.addClass('fa-bolt');
				c.removeClass('fa-plug');
			}
		} catch (err) {
			// in case there is no such page
			console.log("[SSE Error] failiure in the disconnectedCallback function");
			console.log("[SSE Error]", err);
		}
	},
	// allChannels will loop over all our SSE channels, except the "sse" channel,
	// and call "theFunction" for each channel
	allChannels: function (theFunction, channels) {
		for (var i = 0; i < channels.length; i++) {
			var channel = channels[i];
			if (channel != 'sse') {
				theFunction(channel);
			}
		}
	},
	activeChannels: undefined,
	getChannelsUrl: '/xgds_core/sseActiveChannels',
	// getChannels function will return the activeChannels array; if it is undefined,
	// the function will request an array of channels from URL @ getChannelsUrl
	getChannels: function (url) {
		// get the active channels over AJAX
		if (sse.activeChannels === undefined) {
			$.ajax({
				url: sse.getChannelsUrl,
				dataType: 'json',
				async: false,
				success: $.proxy(function (data) {
					sse.activeChannels = data;
				}, this)
			});
		}
		return sse.activeChannels;
	},
	parseEventChannel: function (event) {
		console.log("[SSE Info] inside parse event channel function; event:", event);
		return sse.parseChannel(event.target.url);
	},
	parseChannel: function (fullUrl) {
		console.log("[SSE Info] parsing a channel with full URL:", fullUrl);
		var splits = fullUrl.split('=');
		if (splits.length > 1) {
			return splits[splits.length - 1];
		}
		return 'sse';
	},
	subscribe: function (event_type, callback, channels) {
		if (channels != undefined) {
			console.log("[SSE Info] inside subscribe function and channels have been defined");
			if (!Array.isArray(channels)) {
				channels = [channels];
			}
			for (let channel of channels) {
				console.log("[SSE Info] creating a new Event Source for channel with name:", channel);
				var source = new EventSource("/sse/stream?channel=" + channel);
				source.addEventListener(event_type, callback, false);
			}
		} else {
			console.log("[SSE Info] inside subscribe function and channels are undefined");
			for (let channel of sse.getChannels()) {
				console.log("[SSE Info] creating a new Event Source for channel with name:", channel);
				var source = new EventSource("/sse/stream?channel=" + channel);
				source.addEventListener(event_type, callback, false);
			}
		}
	}
});
