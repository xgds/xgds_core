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
		setInterval(sse.checkHeartbeat, 6000);
		sse.subscribe('heartbeat', sse.connectedCallback, 'sse');
	},
	checkHeartbeat: function() {
		var connected = false
		if (sse.lastHeartbeat != undefined){
			var diff = moment.duration(moment().diff(sse.lastHeartbeat));
			if (diff.asSeconds() <= 5) {
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
				$("#connected").addClass('fa-spin');
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
				$("#connected").removeClass('fa-spin');
			}
		} catch(err){
			// in case there is no such page
		}
	},
	activeChannels: undefined,
	getChannels: function() {
		// get the active channels over AJAX
		if (sse.activeChannels === undefined){
			$.ajax({
	            url: '/xgds_core/sseActiveChannels',
	            dataType: 'json',
	            async: false,
	            success: $.proxy(function(data) {
	                sse.activeChannels = data;
	            }, this)
	          });
		}
		return sse.activeChannels;
	},
	subscribe: function(event_type, callback, channel) {
		if (channel != undefined) {
			var source = new EventSource("/sse/stream?channel=" + channel);
			source.addEventListener(event_type, callback, false);
			return source;
		} else {
			sse.getChannels();
			for (var i=0; i<sse.activeChannels.length; i++){
				var channel = sse.activeChannels[i];
				var source = new EventSource("/sse/stream?channel=" + channel);
				source.addEventListener(event_type, callback, false);
			}
		}
	}
});