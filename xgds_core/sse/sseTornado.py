#!/usr/bin/env python3

# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
#
# The xGDS platform is licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
# __END_LICENSE__

"""Server Sent Events (SSE) server using tornado.  For production use,
should be run behind and nginx proxy - with tornado running locally on
a "non-standard" port like 8080 or 9191.

"""

import signal
from tornado import web
from tornado.options import options, define
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
import json
import datetime
import aioredis


class EventSource(web.RequestHandler):
    """Basic handler for server-sent events."""
    def initialize(self):
        self.set_header('content-type', 'text/event-stream')
        self.set_header('cache-control', 'no-cache')

    async def publish(self, msgDict):
        """Pushes data to a listener following SSE spec.
        See: https://developer.mozilla.org/en-US/docs/Web/API/
             Server-sent_events/Using_server-sent_events
        """
        try:
            msgId = msgDict.get("id", None)
            msgType = msgDict.get("type", None)
            msgRetry = msgDict.get("retry", None)
            if msgId:
                self.write('id: {}\n'.format(msgId))
            if msgType:
                self.write('event: {}\n'.format(msgType))
            if msgRetry:
                self.write('retry: {}\n'.format(msgRetry))
            self.write('data: {}\n\n'.format(msgDict["data"]))
            await self.flush()
            return True
        except StreamClosedError:
            return False


    async def get(self):
        channelName = self.get_query_argument("channel", default="sse")
        print("Start subscription on Redis channel:", channelName)
        rs = await aioredis.create_redis(options.redisUrl)
        channel, = await rs.subscribe(channelName)
        assert isinstance(channel, aioredis.Channel)

        while await channel.wait_message():
            msg = await channel.get(encoding='utf-8')
            msgDict = json.loads(msg)
            connectionLive = await self.publish(msgDict)
            if not connectionLive:
                print("Closing dead connection - channel:", channelName)
                await rs.unsubscribe(channelName)
                # We seem to be leaking connections even after unsubscribe, so make sure we close it.
                print("Closing server connection...")
                rs.close()
                await rs.wait_closed()
                print("Closed...")
                break


if __name__ == "__main__":
    print("Starting Tornado SSE server...")
    define("redisUrl", default="redis://localhost", help="URL to redis server")
    define("tornadoPort", default="8080", help="TCP port where tornado will listen")
    options.parse_command_line()
    print("  Redis URL:", options.redisUrl)
    print("  Tornado port:", options.tornadoPort)

    app = web.Application(
        [
            (r'/stream', EventSource)
        ],
        debug=False
    )
    server = HTTPServer(app)
    server.listen(options.tornadoPort)
    signal.signal(signal.SIGINT, lambda x, y: IOLoop.instance().stop())
    IOLoop.instance().start()
