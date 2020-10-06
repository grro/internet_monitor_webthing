from typing import List
from webthing import (SingleThing, Property, Thing, Value, WebThingServer)
from pi_internet_webthing.speedtestrunner import SpeedtestRunner, Speed
from pi_internet_webthing.connected import ConnectedRunner, ConnectionInfo
import logging
import tornado.ioloop



class ConnetionHistory:

    def __init__(self, updated_listener):
        self.history_log = []
        self.updated_listener = updated_listener

    def on_connection_info_fetched(self, connection_info: ConnectionInfo):
        if len(self.history_log) > 0 and self.history_log[len(self.history_log)] == connection_info:
            return
        if len(self.history_log) > 50:
            del self.history_log[0]
        self.history_log.append(connection_info)
        self.updated_listener(self.history_log)


class InternetWebthing(Thing):

    # regarding capabilities refer https://iot.mozilla.org/schemas
    # there is also another schema registry http://iotschema.org/docs/full.html not used by webthing

    def __init__(self, description, speedtest_period, connecttest_period):
        Thing.__init__(
            self,
            'urn:dev:ops:speedtest-1',
            'Internet Info',
            ['MultiLevelSensor'],
            description
        )
        self.speedtest_period = speedtest_period
        self.history = ConnetionHistory(self.__on_connection_history_updated)
        self.connecttest_period = connecttest_period

        self.downloadspeed = Value(0)
        self.add_property(
            Property(self,
                     'downloadspeed',
                     self.downloadspeed,
                     metadata={
                         '@type': 'LevelProperty',
                         'title': 'Internet downloadspeed',
                         'type': 'number',
                         'description': 'The current internet download  speed',
                         'unit': 'Mbit/sec',
                         'readOnly': True,
                     }))

        self.uploadspeed = Value(0)
        self.add_property(
            Property(self,
                     'uploadspeed',
                     self.uploadspeed,
                     metadata={
                         '@type': 'LevelProperty',
                         'title': 'Internet uploadspeed',
                         'type': 'number',
                         'description': 'The current internet upload speed',
                         'unit': 'Mbit/sec',
                         'readOnly': True,
                     }))

        self.ping_time = Value(0)
        self.add_property(
            Property(self,
                     'ping',
                     self.ping_time,
                     metadata={
                         '@type': 'LevelProperty',
                         'title': 'Internet ping',
                         'type': 'number',
                         'description': 'The current internet ping latency',
                         'unit': 'milliseconds',
                         'readOnly': True,
                     }))

        self.testserver = Value("")
        self.add_property(
            Property(self,
                     'speedtest_server',
                     self.testserver,
                     metadata={
                         '@type': 'Name',
                         'title': 'The speedtest server',
                         'type': 'string',
                         'description': 'The server which has been connected to perform the speedtest',
                         'readOnly': True,
                     }))

        self.resulturi = Value("")
        self.add_property(
            Property(self,
                     'speedtest_report_uri',
                     self.resulturi,
                     metadata={
                         '@type': 'Name',
                         'title': 'The speedtest report uri',
                         'type': 'string',
                         'description': 'The speedtest report uri',
                         'readOnly': True,
                     }))

        self.internet_connected = Value(False)
        self.add_property(
            Property(self,
                     'connected',
                     self.internet_connected,
                     metadata={
                         '@type': 'BooleanProperty',
                         'title': 'Internet connected',
                         "type": "boolean",
                         'description': 'Whether the internet is connected',
                         'readOnly': True,
                     }))

        self.ip_address = Value("")
        self.add_property(
            Property(self,
                     'ip_address',
                     self.ip_address,
                     metadata={
                         '@type': 'IpAddressProperty',
                         'title': 'The ip address',
                         'type': 'string',
                         'description': 'The ip address used for internet connection',
                         'readOnly': True,
                     }))

        self.connection_history = Value("")
        self.add_property(
            Property(self,
                     'connection_history',
                     self.connection_history,
                     metadata={
                         '@type': 'List',
                         'title': 'The connection history',
                         'type': 'string',
                         'description': 'The connection history',
                         'readOnly': True,
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()
        SpeedtestRunner().listen(self.__on_speed_updated, self.speedtest_period)
        ConnectedRunner().listen(self.__on_connected_data_fetched, self.connecttest_period)

    def __on_speed_updated(self, speed: Speed):
        self.ioloop.add_callback(self.__update_speed_props, speed)

    def __update_speed_props(self, speed: Speed):
        self.uploadspeed.notify_of_external_update(self.__to_mbit(speed.uploadspeed))
        self.downloadspeed.notify_of_external_update(self.__to_mbit(speed.downloadspeed))
        self.ping_time.notify_of_external_update(speed.ping)
        self.testserver.notify_of_external_update(speed.server)
        self.resulturi.notify_of_external_update(speed.report_uri)

    def __on_connected_data_fetched(self, connection_info: ConnectionInfo):
        self.history.on_connection_info_fetched(connection_info)
        self.ioloop.add_callback(self.__update_connected_props, connection_info)

    def __update_connected_props(self, connection_info: ConnectionInfo):
        self.internet_connected.notify_of_external_update(connection_info.is_connected)
        self.ip_address.notify_of_external_update(connection_info.ip_address)

    def __on_connection_history_updated(self, connetion_history: List[ConnectionInfo]):
        self.ioloop.add_callback(self.__update_connection_history_prop, connetion_history)

    def __update_connection_history_prop(self, connetion_history: List[ConnectionInfo]):
        history = [str(info) for info in connetion_history]
        self.connection_history.notify_of_external_update("\n".join(history))

    def __to_mbit(self, bit_pre_sec: int):
        return round(bit_pre_sec / (1000 * 1000), 2)

def run_server(port, description, speedtest_period, connecttest_period):
    speedtest_webthing = InternetWebthing(description, speedtest_period, connecttest_period)
    server = WebThingServer(SingleThing(speedtest_webthing), port=port)
    try:
        logging.info('starting the server')
        server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        server.stop()
        logging.info('done')
