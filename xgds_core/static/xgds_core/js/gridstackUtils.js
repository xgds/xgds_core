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
	    xgds_gridstack.THE_GRIDSTACK = container.data('gridstack')
	        
	    xgds_gridstack.bindButtonCallbacks(container);
	    
	    var itemElements = container.find('.grid-stack-item');
	    itemElements.each(function(index, element) {
	    	xgds_gridstack.initializePin(element);
	    });
	    
	    xgds_gridstack.bindMapResize(container);
	    xgds_gridstack.bindChanges();
	},

	addItem: function(item, x, y, width, height){
		xgds_gridstack.THE_GRIDSTACK.addWidget(item, x, y, width, height);
		xgds_gridstack.bindButtonCallbacks(item);
		xgds_gridstack.initializePin(item);
	},

	bindMapResize: function (container){
		var mapGridstackItem = container.find("#map-gridstack-item");
		if (mapGridstackItem.length == 1) {
			// disable resize on the map
			mapGridstackItem.find("#map").resizable('destroy');
//			mapGridstackItem.find("#map").resizable("disable").removeClass('ui-state-disabled');;
			mapGridstackItem.on('resizestop', function(event, ui){
				app.vent.trigger('doMapResize');
			});
			app.vent.trigger('doMapResize');
		}
	},

	initializePin: function(item){
		var locks = $(item).find('.icon-lock');
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
		container.find(".icon-cancel-circled").bind("click", function(event) {
			var parentElement = $(event.target).closest(".grid-stack-item");
			if (parentElement != undefined){
				xgds_gridstack.THE_GRIDSTACK.removeWidget(parentElement);
			}
		});
	},

	clickPin: function(event) {
	    var pinButton = $(event.target);
	    var item = pinButton.closest(".grid-stack-item");
	    
	    if (pinButton.hasClass('icon-lock')) {
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
	    pinButton.removeClass('icon-lock-open');
	    pinButton.addClass('icon-lock');
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
	    pinButton.removeClass('icon-lock');
	    pinButton.addClass('icon-lock-open');
	},
	
	bindChanges: function() {

//		$('.grid-stack').on('change', function(event, items) {
//			console.log(items);
//		    //serializeWidgetMap(items);
//		});
	},

	loadGrid: function() {
	    this.THE_GRIDSTACK.removeAll();
	    var items = GridStackUI.Utils.sort(this.serializedData);
	    _.each(items, function (node) {
	        this.grid.addWidget($('<div><div class="grid-stack-item-content" /><div/>'),
	            node.x, node.y, node.width, node.height);
	    }, this);
	},

	saveGrid: function(){
	    var serializedData = _.map($('.grid-stack > .grid-stack-item:visible'), function (el) {
	        el = $(el);
	        var node = el.data('_gridstack_node');
	        return {
	            x: node.x,
	            y: node.y,
	            width: node.width,
	            height: node.height
	        };
	    });
	    
	    var key = window.location.href;
	    var jsonData = JSON.stringify({ key: serializedData});  
	    $.ajax( { url: "{% url 'xgds_notes_record' %}",
	    	      type: "POST",
	    	      dataType: 'json',
	    	      data: jsonData,
	    	      success: function(data)
	    	        {
	    	    	  console.log(data);
	    	        },
	    	        error: function(data)
	    	        {
	    	        	console.log("boo");
	    	        }
	    	    });
//	    $('#saved-data').val(JSON.stringify(this.serializedData, null, '    '));
	}
});


