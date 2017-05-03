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
	preloadImages: function(urls) {
		var result = [];
		$.each(urls, function(index, theUrl){
	        var theImg = $('<img/>')[0];
	        theImg.src = theUrl;
	        result.push(theImg);
	    });
		return result;
	},
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
		var theFunction = context[func];
		if (theFunction !== undefined){
			return theFunction.apply(context, [args]);
		}
		return undefined;
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
	},
	arrayEquals: function(a1, a2){
	    return (JSON.stringify(a1) == JSON.stringify(a2));
	},
	indexBy: function(list, keyProp) {
		// Return an object that indexes the objects in a list by their key property.
		// keyProp should be a string.
		obj = {};
		_.each(list, function(item) {
			obj[item[keyProp]] = item;
		});
		return obj;
	},
	groupBy: function(list, keyProp) {
		obj = {};
		_.each(list, function(item) {
			if (_.isUndefined(obj[item[keyProp]])) {
				obj[item[keyProp]] = [];
			}
			obj[item[keyProp]].push(item);
		});
		return obj;
	},
	randomColor: function() {
        return '#' + ((1 << 24) * Math.random() | 0).toString(16);
    },
    rainbow: function(numOfSteps, step) {
        // This function generates vibrant, 'evenly spaced' colours (i.e. no clustering).
        // This is ideal for creating easily distiguishable vibrant markers in Google Maps and other apps.
        // Adam Cole, 2011-Sept-14
        // HSV to RBG adapted from:
        // http://mjijackson.com/2008/02/rgb-to-hsl-and-rgb-to-hsv-color-model-conversion-algorithms-in-javascript
        // source: http://stackoverflow.com/questions/1484506/random-color-generator-in-javascript/7419630
        var r, g, b;
        var h = step / numOfSteps;
        var i = ~~(h * 6);
        var f = h * 6 - i;
        var q = 1 - f;
        switch (i % 6) {
        case 0:
            r = 1, g = f, b = 0;
            break;
        case 1:
            r = q, g = 1, b = 0;
            break;
        case 2:
            r = 0, g = 1, b = f;
            break;
        case 3:
            r = 0, g = q, b = 1;
            break;
        case 4:
            r = f, g = 0, b = 1;
            break;
        case 5:
            r = 1, g = 0, b = q;
            break;
        }
        var c = '#' + ('00' + (~~(r * 255)).toString(16)).slice(-2) +
            ('00' + (~~(g * 255)).toString(16)).slice(-2) +
            ('00' + (~~(b * 255)).toString(16)).slice(-2);
        return (c);
    },
});