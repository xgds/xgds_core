//__BEGIN_LICENSE__
// Copyright (c) 2015, United States Government, as represented by the
// Administrator of the National Aeronautics and Space Administration.
// All rights reserved.
//
// The xGDS platform is licensed under the Apache License, Version 2.0
// (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// http://www.apache.org/licenses/LICENSE-2.0.
//
// Unless required by applicable law or agreed to in writing, software distributed
// under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.
//__END_LICENSE__

$.extend({
	getManyJS: function(urls, callback){
		var ajaxRequests = [];
		$.each(urls, function(i, url){
			ajaxRequests.push(
					$.ajax({
						async: false,
						url: url,
						dataType: "script",
						error: function(jqXHR, errorType, exception) {
							//TODO should probably handle this ...
							console.log(exception);
						}
					}));
		});

		$.when(ajaxRequests).then(function(){
			if (callback != undefined){
				if (typeof callback=='function') callback();
			}
		});
	},
	getManyCss: function(urls, callback){
		$.when(
				$.each(urls, function(i, url){
					$.get(url, function(){
						$('<link>', {rel:'stylesheet', type:'text/css', 'href':url}).appendTo('head');
					});
				})
		).done(function(){
			if (callback != undefined){
				if (typeof callback=='function') callback();
			}
		});
	},
	executeFunctionByName: function(functionName, context, args) {
		//var args = [].slice.call(arguments).splice(2);
		context = context || window;
		var namespaces = functionName.split(".");
		var func = namespaces.pop();
		for(var i = 0; i < namespaces.length; i++) {
			context = context[namespaces[i]];
		}
		return context[func].apply(context, args);
	},
	lookupFunctionByName: function(functionName, context) {
		context = context || window;
		var namespaces = functionName.split(".");
		var func = namespaces.pop();
		for(var i = 0; i < namespaces.length; i++) {
			context = context[namespaces[i]];
		}
		return context[func];
	},
	getValueByName: function(functionName) {
		return eval(functionName);
	}
});