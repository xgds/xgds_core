//__BEGIN_LICENSE__
//Copyright (c) 2015, United States Government, as represented by the
//Administrator of the National Aeronautics and Space Administration.
//All rights reserved.

//The xGDS platform is licensed under the Apache License, Version 2.0
//(the "License"); you may not use this file except in compliance with the License.
//You may obtain a copy of the License at
//http://www.apache.org/licenses/LICENSE-2.0.

//Unless required by applicable law or agreed to in writing, software distributed
//under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
//CONDITIONS OF ANY KIND, either express or implied. See the License for the
//specific language governing permissions and limitations under the License.
//__END_LICENSE__

//This simple javascript is called by tungsten replicator after it does an insertion.
//To test in your virtual machine, type
//rhino handle_data_insertion.js

//naive java implementation variant, if curl is not available
var prefix = 'http://localhost:8181';
var tableListUrl = '/xgds_core/rebroadcast/tableNamesAndKeys/'
var url = '/xgds_core/tungsten/dataInsert/';
var httpStatusOK = 200;
var colTypeInt = 4;
var colTypeVarchar = 12;

var tableNamesAndKeys = {};
var getTableNamesAndKeys = function() {
    // TODO: Manage exceptions on HTTP GET
    resp = httpGet(prefix + tableListUrl);
    if (resp.statusCode == httpStatusOK) {   // Only process data if we get OK status code
        tableNamesStr = resp.data;
        tableNamesAndKeys = JSON.parse(tableNamesStr);
    }
    logger.info("TABLE LIST: " + tableNamesAndKeys);
    return tableNamesAndKeys;
}

function getMethods(obj) {
    var result = [];
    for (var id in obj) {
        try {
            result.push(id + ": " + obj[id].toString());
        } catch (err) {
            result.push(id + ": inaccessible");
        }
    }
    return result;
}

var prepare = function()
{
    getTableNamesAndKeys();
}

//Perform the filter process; function is called for each event in the THL

var filter= function(event)
{
    if (Object.keys(tableNamesAndKeys).length == 0) {
        logger.info("NO TABLES IN LIST!");
        return;
    }
// Get the array of DBMSData objects
    data = event.getData();

    // Iterate over the individual DBMSData objects
    for(i=0;i<data.size();i++)
    {
      // Get a single DBMSData object
      d = data.get(i);

      // Process a Statement Event; event type is identified by comparing the object class type

      if (d instanceof com.continuent.tungsten.replicator.dbms.StatementData)
      {
        // Do statement processing
    	  logger.info('STATEMENT UPDATE:');
    	  logger.info('  ' + d.getQuery());
      }
      else if (d instanceof com.continuent.tungsten.replicator.dbms.RowChangeData)
      {
        // Get an array of all the row changes
        rows = data.get(i).getRowChanges();

        // Iterate over row changes
        for(j=0;j<rows.size();j++)
        {
        	// Get the single row change
        	rowchange = rows.get(j);

        	// Identify the row change type

        	logger.info(rowchange.getAction());
        	var tableName = rowchange.getTableName();
        	logger.info('TABLE NAME: ' + tableName);

        	if (!tableNamesAndKeys[tableName]) {
        		logger.info("SKIPPING TABLE: " + tableName);
        		return;
        	}

//        	var colSpecs = rowchange.getColumnSpec();
//        	var idIndex = -1;
//        	logger.info('COL SPEC SIZE: ' + colSpecs.size());

//        	for (var c=0; c<colSpecs.size(); c++) {
//        		logger.info(c);
//        		logger.info(colSpecs.get(c));
//        		var colName = colSpecs.get(c).getName();
//        		var colLength = colSpecs.get(c).getLength();
//        		logger.info('COL NAME: ' + colName + '(' + colLength +')');
//
//        		if (colName == 'id'){
//        			logger.info('COLUMN ID FOUND ');
//        			idIndex = c;
//        			break;
//        		}
//        	}

        	var dbAction = rowchange.getAction();
        	logger.info('ROW CHANGE ACTION: ' + dbAction);
        	var pkType = 0;
        	var pkValue = -1;
        	
        	if ((dbAction == "UPDATE") || (dbAction == "DELETE")) {
        		var rowKeys = rowchange.getKeyValues();
        		var rowKeyTypes = rowchange.getKeySpec();
        		if (rowKeyTypes.size() != 1) {
        			logger.info("ONLY Single Column PK's supported for table: " + tableName + " - " + rowKeyTypes.size());
        			return;
        		}
        		pkType = rowKeyTypes.get(0).getType();
        		for (var i=0; i<rowKeys.size(); i++) {
        			switch (pkType) {
        			case colTypeInt:
        				pkValue = rowKeys.get(i).get(0).getValue();
        				break;
        			case colTypeVarchar:
        				pkValue = java.lang.String(rowKeys.get(i).get(0).getValue())
        				break;
        			default:
        				logger.info("TYPE code " + pkType + " not recognized for PK in table: " + tableName);
        				break;
        			}
        			logger.info("DOING " + dbAction + " on table: " + tableName + " for PK: " + pkValue);
        		}
        	}	
        	
        	if (dbAction == "INSERT") {
        		var colValues = rowchange.getColumnValues();
        		logger.info("ROWS INSERTED: " + colValues.size());
        		for (var r=0; r<colValues.size(); r++) {
        			var pkType = tableNamesAndKeys[tableName].pkType;
        			switch (pkType) {
        			case "int":
        				pKValue = colValues.get(r).get(tableNamesAndKeys[tableName].pkColNum-1).getValue();
        				break;
        			case "string":
        				pKValue = java.lang.String(colValues.get(r).get(tableNamesAndKeys[tableName].pkColNum-1).getValue());
        				break;
        			}
        			logger.info("DOING " + dbAction + " on table: " + tableName + " for PK: " + pkValue);
//      			var styleName = colValues.get(r).get(1).getValue();
//      			var styleColor = colValues.get(r).get(2).getValue();
//        			logger.info('PK: (' + pkType + ')' + pKValue);
//      			logger.info('Style Name: ' + java.lang.String(styleName));
//      			logger.info('Style Color: ' + java.lang.String(styleColor));
        		}
        	}
        	//logger.info(rowchange.getColumnSpec());
        }
      }
    }
}

function doThings() {
	
	response = httpPost(prefix + url, data).data;
	
	logger.info('response: ' + response);
	var theResponse = JSON.parse(response);
	logger.info ('timestamp: ' + theResponse.timestamp);
	logger.info ('data: ' + theResponse.data);
}

function httpGet(theUrl){
	var con = new java.net.URL(theUrl).openConnection();
	con.requestMethod = "GET";
	return asResponse(con);
}

function httpPost(theUrl, data, contentType){
	var con = new java.net.URL(theUrl).openConnection();

	con.setRequestMethod("POST");

	var contentType = contentType || "application/json";
	con.setRequestProperty("Content-Type", contentType);
   
	con.setDoOutput(true);
	con.setDoInput(true);
	con.setAllowUserInteraction(false);
	logger.info('ABOUT TO POST:' + JSON.stringify(data));
	write(con.getOutputStream(), data);
	return asResponse(con);
}

function asResponse(con){
    var d = read(con.inputStream);
    return {data : d, statusCode : con.responseCode};
}

function write(outputStream, data){
	// either way seems to work but on the django side content is in request.body
	var wr = new java.io.OutputStreamWriter(outputStream);
	wr.write(JSON.stringify(data));
//	var wr = new java.io.DataOutputStream(outputStream);
//	wr.writeBytes(data);
	wr.flush();
	wr.close();
}

function read(inputStream){
	var inReader = new java.io.BufferedReader(new java.io.InputStreamReader(inputStream));
	var inputLine;
	var response = new java.lang.StringBuffer();

	while ((inputLine = inReader.readLine()) != null) {
		response.append(inputLine);
	}
	inReader.close();
	return response.toString();
}
