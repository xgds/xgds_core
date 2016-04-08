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

DEFAULT_GRIDSTACK_OPTIONS =  {
        cellHeight: 200,
        verticalMargin: 20,
        width: 6,
        float: false
    };

THE_GRIDSTACK = undefined;

function initializeGridstack(options) {
	
	if (options === undefined){
		options = DEFAULT_GRIDSTACK_OPTIONS;
	}
    
	var container = $('.grid-stack');
    container.gridstack(options);
    THE_GRIDSTACK = container.data('gridstack')
        
    bindButtonCallbacks(container);
    
    var itemElements = container.find('.grid-stack-item');
    itemElements.each(function(index, element) {
    	initializePin(element);
    });
    
    bindMapResize(container);
}

function addItem(item, x, y, width, height){
	THE_GRIDSTACK.addWidget(item, x, y, width, height);
	bindButtonCallbacks(item);
    initializePin(item);
}

function bindMapResize(container){
	var mapGridstackItem = container.find("#map-gridstack-item");
	if (mapGridstackItem.length == 1) {
		// disable resize on the map
		mapGridstackItem.find("#map").resizable('destroy');
//		mapGridstackItem.find("#map").resizable("disable").removeClass('ui-state-disabled');;
		mapGridstackItem.on('resizestop', function(event, ui){
			app.vent.trigger('doMapResize');
		});
		app.vent.trigger('doMapResize');
	}
}

function initializePin(item){
	var locks = $(item).find('.icon-lock');
	if (locks.length > 0){
		pinItem(item);
	} else {
		unpinItem(item);
	}
	if ($(item).hasClass("noresize")){
    	THE_GRIDSTACK.resizable(item, false);
    }
}

function bindButtonCallbacks(container){
	bindDeleteButtonCallback(container);
	container.find(".pinDiv").bind("click", function(event) {
		clickPin(event);
	});	
}

/**
 * Removes item upon delete button click.
 */
function bindDeleteButtonCallback(container) {
	container.find(".icon-cancel-circled").bind("click", function(event) {
		var parentElement = $(event.target).closest(".grid-stack-item");
		if (parentElement != undefined){
			THE_GRIDSTACK.removeWidget(parentElement);
		}
	});
}

function clickPin(event) {
    var pinButton = $(event.target);
    var item = pinButton.closest(".grid-stack-item");
    
    if (pinButton.hasClass('icon-lock')) {
    	unpinItem(item, pinButton);
    } else {
    	pinItem(item, pinButton);
    }
}

function pinItem(item, pinButton){
    // pin it -- not draggable or resizable
	THE_GRIDSTACK.locked(item, true);
	THE_GRIDSTACK.movable(item, false);
    if (!$(item).hasClass("noresize")){
    	THE_GRIDSTACK.resizable(item, false);
    }

	if (pinButton === undefined){
		pinButton = $(item).find(".pinDiv");
	}
    pinButton.removeClass('icon-lock-open');
    pinButton.addClass('icon-lock');
}

function unpinItem(item, pinButton){
 // unpin it, make it draggable and resizable
	THE_GRIDSTACK.locked(item, false);
	THE_GRIDSTACK.movable(item, true);
	if (!$(item).hasClass("noresize")){
		THE_GRIDSTACK.resizable(item, true);
	}

	if (pinButton === undefined){
		pinButton = $(item).find(".pinDiv");
	}
    pinButton.removeClass('icon-lock');
    pinButton.addClass('icon-lock-open');
}

function loadGrid() {
    this.grid.removeAll();
    var items = GridStackUI.Utils.sort(this.serializedData);
    _.each(items, function (node) {
        this.grid.addWidget($('<div><div class="grid-stack-item-content" /><div/>'),
            node.x, node.y, node.width, node.height);
    }, this);
}

function saveGrid(){
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
//    $('#saved-data').val(JSON.stringify(this.serializedData, null, '    '));
}

