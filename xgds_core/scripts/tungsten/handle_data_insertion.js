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
//jjs handle_data_insertion.js

//naive java implementation variant, if curl is not available
var prefix = 'http://localhost:8181';
var url = '/xgds_core/tungsten/dataInsert/';

// test data for Tamar's computer
var data = {'pk':14173083,
		    'tablename':'basaltApp_pastposition'};

response = httpPost(prefix + url, data).data;

print('response: ' + response);
var theResponse = JSON.parse(response);
print ('timestamp: ' + theResponse.timestamp);
print ('data: ' + theResponse.data);

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
	print('ABOUT TO POST:' + JSON.stringify(data));
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