from webthing import (Property, Thing, Value)
from speedtest import Speedtest
from dataclasses import dataclass
from datetime import datetime
import tornado.ioloop
import threading
import time
import logging


@dataclass
class Speed:
    server: str
    downloadspeed: int
    uploadspeed: int
    ping: float
    report_uri: str


class SpeedtestRunner:

    def listen(self, listener, measure_period_sec: int):
        threading.Thread(target=self.__measure_periodically, args=(measure_period_sec, listener), daemon=True).start()

    def __measure_periodically(self, measure_period_sec: int, listener):
        while True:
            try:
                speed = self.__measure()
                listener(speed)
            except Exception as e:
                logging.error(e)
            time.sleep(measure_period_sec)

    def __measure(self) -> Speed:
        s = Speedtest()
        s.download()
        s.upload()
        try:
            link = s.results.share()   # POST data to the speedtest.net API to obtain a share results link
        except:
            link = None
        metrics = s.results.dict()
        return Speed(metrics['server'].get('sponsor', '') + "/" + metrics['server'].get('name', ''), int(metrics['download']), int(metrics['upload']), metrics['ping'], link)


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
        SpeedtestRunner().listen(self.__on_speed_updated, self.testperiod.get())

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
