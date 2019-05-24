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

analytics = {}; //namespace

$.extend(analytics, {
    trackActionMethods: [],
    stringify: function(value){
        if (value instanceof Object){
            return JSON.stringify(value);
        }
        return String(value);
    },
    trackAction: function(category, action, identifier) {
        category = analytics.stringify(category);
        action = analytics.stringify(action);
        identifier = analytics.stringify(identifier);
        _.each(analytics.trackActionMethods, function(method) {
            try {
                method(category, action, identifier);
            } catch (e) {
                // pass
            }
        })
    },
    addTrackActionMethod: function(method){
        analytics.trackActionMethods.push(method);
    }

});