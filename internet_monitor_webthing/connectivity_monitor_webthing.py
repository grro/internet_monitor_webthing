from webthing import Property, Thing, Value
from internet_monitor_webthing.connectivity_monitor import ConnectionInfo, ConnectionLog, ConnectionTester
import tornado.ioloop


class InternetConnectivityMonitorWebthing(Thing):

    # regarding capabilities refer https://iot.mozilla.org/schemas
    # there is also another schema registry http://iotschema.org/docs/full.html not used by webthing

    def __init__(self, description: str, connecttest_period: int, connecttest_url: str):
        Thing.__init__(
            self,
            'urn:dev:ops:connectivitymonitor-1',
            'Internet Connectivity Monitor',
            ['MultiLevelSensor'],
            description
        )
        self.connection_log = ConnectionLog()
        self.connecttest_period = connecttest_period

        self.internet_connected = Value(False)
        self.add_property(
            Property(self,
                     'connected',
                     self.internet_connected,
                     metadata={
                         '@type': 'BooleanProperty',
                         'title': 'Internet is connected',
                         "type": "boolean",
                         'description': 'Whether the internet is connected',
                         'readOnly': True,
                     }))

        self.event_date = Value("")
        self.add_property(
            Property(self,
                     'time',
                     self.event_date,
                     metadata={
                         'title': 'Updated time',
                         "type": "string",
                         'unit': 'datetime',
                         'description': 'The ISO 8601 date time of last state update',
                         'readOnly': True,
                     }))

        self.ip_address = Value("")
        self.add_property(
            Property(self,
                     'ip_address',
                     self.ip_address,
                     metadata={
                         'title': 'Public IP address',
                         'type': 'string',
                         'description': 'The public WAN IP address used for internet connection',
                         'readOnly': True,
                     }))

        self.isp = Value("")
        self.add_property(
            Property(self,
                     'isp',
                     self.isp,
                     metadata={
                         'title': 'Internet service provider',
                         'type': 'string',
                         'description': 'The name of the internet service provider providing the public WAN IP address ',
                         'readOnly': True,
                     }))

        self.latitude = Value("")
        self.add_property(
            Property(self,
                     'latitude',
                     self.latitude,
                     metadata={
                         'title': 'latitude',
                         'type': 'string',
                         'description': 'The resolve latitude regarding the ip address',
                         'readOnly': True,
                     }))

        self.longitude = Value("")
        self.add_property(
            Property(self,
                     'longitude',
                     self.longitude,
                     metadata={
                         'title': 'longitude',
                         'type': 'string',
                         'description': 'The resolve longitude regarding the ip address',
                         'readOnly': True,
                     }))

        self.location_uri = Value("")
        self.add_property(
            Property(self,
                     'location_uri',
                     self.location_uri,
                     metadata={
                         'title': 'location_uri',
                         'type': 'string',
                         'description': 'The resolve location regarding the ip address',
                         'readOnly': True,
                     }))

        self.test_url = Value(connecttest_url)
        self.add_property(
            Property(self,
                     'connection_test_url',
                     self.test_url,
                     metadata={
                         'title': 'Internet connection test url',
                         "type": "string",
                         'description': 'The url to connect',
                         'readOnly': True,
                     }))

        self.testperiod = Value(connecttest_period)
        self.add_property(
            Property(self,
                     'connection_test_period',
                     self.testperiod,
                     metadata={
                         '@type': 'LevelProperty',
                         'title': 'Internet connection test execution period in seconds',
                         'type': 'number',
                         'description': 'The Internet connection test execution period in seconds',
                         'unit': 'sec',
                         'readOnly': True,
                     }))

        self.connection_history = Value("")
        self.add_property(
            Property(self,
                     'connection_history',
                     self.connection_history,
                     metadata={
                         'title': 'Connection log',
                         'type': 'array',
                         'description': 'The connection log',
                         'readOnly': True,
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()
        self.tester = ConnectionTester(self.connection_log)
        self.tester.listen(self.__connection_state_updated, self.testperiod.get(), self.test_url.get())

    def __connection_state_updated(self, connection_info: ConnectionInfo):
        if connection_info is not None:
            self.ioloop.add_callback(self.__update_connected_props, connection_info)

    def __update_connected_props(self, connection_info: ConnectionInfo):
        self.internet_connected.notify_of_external_update(connection_info.is_connected)
        self.event_date.notify_of_external_update(connection_info.date.isoformat())
        self.ip_address.notify_of_external_update(connection_info.ip_address)
        self.isp.notify_of_external_update(connection_info.ip_info['isp'])
        longitude = connection_info.ip_info['longitude']
        latitude = connection_info.ip_info['latitude']
        self.longitude.notify_of_external_update(longitude)
        self.latitude.notify_of_external_update(latitude)
        self.location_uri.notify_of_external_update('https://www.google.com/maps/search/?api=1&query='+ latitude + ',' + longitude)
        self.connection_history.notify_of_external_update(self.connection_log.to_report())
