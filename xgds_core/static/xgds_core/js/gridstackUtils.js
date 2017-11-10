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

var xgds_gridstack = xgds_gridstack || {};
$.extend(xgds_gridstack,{
	DEFAULT_GRIDSTACK_OPTIONS : {
	        cellHeight: 200,
	        verticalMargin: 20,
	        width: 6,
	        float: false
	    },
	THE_GRIDSTACK : undefined,
	initializeGridstack: function(options){
		
		if (options === undefined){
			options = xgds_gridstack.DEFAULT_GRIDSTACK_OPTIONS;
		}
	    
		var container = $('.grid-stack');
	    container.gridstack(options);
	    xgds_gridstack.THE_GRIDSTACK = container.data('gridstack');
	        
	    xgds_gridstack.bindButtonCallbacks(container);
	    
	    var itemElements = container.find('.grid-stack-item');
	    itemElements.each(function(index, element) {
	    	xgds_gridstack.initializePin(element);
	    });
	    
	    xgds_gridstack.bindMapResize(container);
	    xgds_gridstack.bindChanges();
	    xgds_gridstack.loadGrid(window.location.pathname);
	},

	addItem: function(item, x, y, width, height){
		xgds_gridstack.THE_GRIDSTACK.addWidget(item, x, y, width, height);
		xgds_gridstack.bindButtonCallbacks(item);
		xgds_gridstack.initializePin(item);
	},

	bindMapResize: function (container){
		var mapGridstackItem = container.find("#map-gridstack-item");
		if (mapGridstackItem.length == 1) {
			mapGridstackItem.on('resizestop', function(event, ui){
				app.vent.trigger('doMapResize');
			});
			app.vent.trigger('doMapResize');
		}
	},

	initializePin: function(item){
		var locks = $(item).find('.fa-lock');
		if (locks.length > 0){
			xgds_gridstack.pinItem(item);
		} else {
			xgds_gridstack.unpinItem(item);
		}
		if ($(item).hasClass("noresize")){
			xgds_gridstack.THE_GRIDSTACK.resizable(item, false);
	    }
	},

	bindButtonCallbacks: function(container){
		xgds_gridstack.bindDeleteButtonCallback(container);
		container.find(".pinDiv").bind("click", function(event) {
			xgds_gridstack.clickPin(event);
		});	
	},

	/**
	 * Removes item upon delete button click.
	 */
	bindDeleteButtonCallback: function(container) {
		container.find(".fa-window-close").bind("click", function(event) {
			var parentElement = $(event.target).closest(".grid-stack-item");
			if (parentElement != undefined){
				xgds_gridstack.THE_GRIDSTACK.removeWidget(parentElement);
			}
		});
	},

	clickPin: function(event) {
	    var pinButton = $(event.target);
	    var item = pinButton.closest(".grid-stack-item");
	    
	    if (pinButton.hasClass('fa-lock')) {
	    	xgds_gridstack.unpinItem(item, pinButton);
	    } else {
	    	xgds_gridstack.pinItem(item, pinButton);
	    }
	},

	pinItem: function(item, pinButton){
	    // pin it -- not draggable or resizable
		xgds_gridstack.THE_GRIDSTACK.locked(item, true);
		xgds_gridstack.THE_GRIDSTACK.movable(item, false);
	    if (!$(item).hasClass("noresize")){
	    	xgds_gridstack.THE_GRIDSTACK.resizable(item, false);
	    }

		if (pinButton === undefined){
			pinButton = $(item).find(".pinDiv");
		}
	    pinButton.removeClass('fa-unlock-alt');
	    pinButton.addClass('fa-lock');
	},

	unpinItem: function(item, pinButton){
	 // unpin it, make it draggable and resizable
		xgds_gridstack.THE_GRIDSTACK.locked(item, false);
		xgds_gridstack.THE_GRIDSTACK.movable(item, true);
		if (!$(item).hasClass("noresize")){
			xgds_gridstack.THE_GRIDSTACK.resizable(item, true);
		}

		if (pinButton === undefined){
			pinButton = $(item).find(".pinDiv");
		}
	    pinButton.removeClass('fa-lock');
	    pinButton.addClass('fa-unlock-alt');
	},
	
	bindChanges: function() {
		var _this = this;
		$('.grid-stack').on('change', function(event, items) {
		   	_this.saveGrid(window.location.pathname)
		});
	},

	saveGrid: function(location){
	    var serializedData = _.map($('.grid-stack > .grid-stack-item:visible'), function (el) {
	    	var elid = el.id;
	        el = $(el);
	        var node = el.data('_gridstack_node');
	        return {
	            x: node.x,
	            y: node.y,
	            width: node.width,
	            height: node.height,
				elid: elid
	        };
	    });
		var url = location.split("/");
		url = url[1] + "/" + url[2];

	    Cookies.set("gridstack_" + url, serializedData);
	},

	loadGrid: function(location) {
	    // this.THE_GRIDSTACK.removeAll();
		if (this.getGrid != null){
			var serializedData = this.getGrid(location);
			var items = GridStackUI.Utils.sort(serializedData);
			_.each(items, function (node) {
				// this.grid.addWidget($('<div><div class="grid-stack-item-content" /><div/>'),
				//     node.x, node.y, node.width, node.height);
				this.THE_GRIDSTACK.move(document.getElementById(node.elid), node.x, node.y);
				this.THE_GRIDSTACK.resize(document.getElementById(node.elid), node.width, node.height);
			}, this);
		}
	},

	getGrid: function(location){
		var url = location.split("/");
		url = url[1] + "/" + url[2];

		if (Cookies.get("gridstack_" + url) != null){
			var data = Cookies.getJSON("gridstack_" + url);
			return data;
		}
	},

	resetGrid: function(location){
		var url = location.split("/");
		url = url[1] + "/" + url[2];

		if (Cookies.get("gridstack_" + url) != null)
			Cookies.remove("gridstack_" + url);
	},

	toggleAllPins: function(open) {
		$('.grid-stack-item').each(function() {
			if (open){
				xgds_gridstack.unpinItem(this);
			} else {
				xgds_gridstack.pinItem(this);
			}
		});
	},
	handleToggleAllClick: function(){
		var toggleAllButton = $('#gridstack_toggleAll');
		if (toggleAllButton.hasClass('fa-lock')) {
			// unlock
			xgds_gridstack.toggleAllPins(true);
			toggleAllButton.removeClass('fa-lock');
			toggleAllButton.addClass('fa-unlock-alt');
		} else {
			// lock
			xgds_gridstack.toggleAllPins(false);
			toggleAllButton.removeClass('fa-unlock-alt');
			toggleAllButton.addClass('fa-lock');
		}
	}
});


