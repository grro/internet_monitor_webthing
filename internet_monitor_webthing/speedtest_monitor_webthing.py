from webthing import (Property, Thing, Value, Action)
from internet_monitor_webthing.speedtest_monitor import SpeedtestRunner, Speed
from datetime import datetime
import tornado.ioloop
import uuid


class TriggerSpeedTest(Action):

    def __init__(self, thing, input_):
        Action.__init__(self, uuid.uuid4().hex, thing, 'trigger', input_=input_)

    def perform_action(self):
        self.thing.speedtest_runner.measure()


class InternetSpeedMonitorWebthing(Thing):

    # regarding capabilities refer https://iot.mozilla.org/schemas
    # there is also another schema registry http://iotschema.org/docs/full.html not used by webthing

    def __init__(self, description: str, speedtest_period: int):
        Thing.__init__(
            self,
            'urn:dev:ops:speedmonitor-1',
            'Internet Speed Monitor',
            ['MultiLevelSensor'],
            description
        )

        self.downloadspeed = Value(0)
        self.add_property(
            Property(self,
                     'download_speed',
                     self.downloadspeed,
                     metadata={
                         '@type': 'LevelProperty',
                         'title': 'Internet download speed',
                         'type': 'number',
                         'description': 'The current internet download  speed',
                         'unit': 'Mbit/sec',
                         'readOnly': True,
                     }))

        self.uploadspeed = Value(0)
        self.add_property(
            Property(self,
                     'upload_speed',
                     self.uploadspeed,
                     metadata={
                         '@type': 'LevelProperty',
                         'title': 'Internet upload speed',
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
                         'title': 'Internet ping (latency)',
                         'type': 'number',
                         'description': 'The current internet ping latency',
                         'unit': 'milliseconds',
                         'readOnly': True,
                     }))

        self.testdate = Value("")
        self.add_property(
            Property(self,
                     'last_test',
                     self.testdate,
                     metadata={
                         'title': 'Last executed test date',
                         'type': 'string',
                         'description': 'The date of the last successfully executed test (iso 8601 string)',
                         'readOnly': True,
                     }))

        self.testperiod = Value(speedtest_period)
        self.add_property(
            Property(self,
                     'speedtest_exection_period',
                     self.testperiod,
                     metadata={
                         '@type': 'LevelProperty',
                         'title': 'Speedtest execution period',
                         'type': 'number',
                         'description': 'Speedtest execution period in seconds',
                         'unit': 'sec',
                         'readOnly': True,
                     }))

        self.testserver = Value("")
        self.add_property(
            Property(self,
                     'speedtest_server',
                     self.testserver,
                     metadata={
                         'title': 'Speedtest servername',
                         'type': 'string',
                         'description': 'The speedtest server which has been connected to perform the speedtest',
                         'readOnly': True,
                     }))

        self.resulturi = Value("")
        self.add_property(
            Property(self,
                     'speedtest_result_uri',
                     self.resulturi,
                     metadata={
                         'title': 'Speedtest result report url',
                         'type': 'string',
                         'description': 'speedtest result report url',
                         'readOnly': True,
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()
        self.speedtest_runner = SpeedtestRunner(self.__on_speed_updated)
        self.add_available_action(
            'trigger',
            {
                'title': 'Trigger',
                'description': 'Triggers a speed test run',
            },
            TriggerSpeedTest)
        self.speedtest_runner.run_periodically(self.testperiod.get())

    def __on_speed_updated(self, speed: Speed):
        self.ioloop.add_callback(self.__update_speed_props, speed)

    def __update_speed_props(self, speed: Speed):
        self.uploadspeed.notify_of_external_update(self.__to_mbit(speed.uploadspeed))
        self.downloadspeed.notify_of_external_update(self.__to_mbit(speed.downloadspeed))
        self.ping_time.notify_of_external_update(speed.ping)
        self.testdate.notify_of_external_update(datetime.now().isoformat())
        self.testserver.notify_of_external_update(speed.server)
        self.resulturi.notify_of_external_update(speed.report_uri)

    def __to_mbit(self, bit_pre_sec: int):
        return round(bit_pre_sec / (1000 * 1000), 1)
