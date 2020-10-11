from webthing import (Property, Thing, Value)
from datetime import datetime
from dataclasses import dataclass
from typing import List
import logging
import pickle
import requests
import threading
import time
import tornado.ioloop


@dataclass(eq=False)
class ConnectionInfo:
    date: datetime
    is_connected: bool
    ip_address: str

    def __eq__(self, other):
        return self.is_connected == other.is_connected and self.ip_address == other.ip_address

    def __str__(self):
        return self.date.isoformat()  + ", " + str(self.is_connected) + ", " + self.ip_address


class ConnectedRunner:

    def __init__(self):
        self.cache_ip_address = ""
        self.cache_time = datetime.fromtimestamp(555)

    def listen(self, listener, measure_period_sec, test_uri: str = "http://google.com"):
        threading.Thread(target=self.__measure_periodically, args=(measure_period_sec, test_uri, listener), daemon=True).start()

    def __measure_periodically(self, measure_period_sec: int, test_server: str, listener):
        while True:
            try:
                connected_info = self.__measure(test_server)
                listener(connected_info)
            except Exception as e:
                logging.error(e)
            time.sleep(measure_period_sec)

    def __measure(self, test_uri) -> ConnectionInfo:
        try:
            requests.get(test_uri)
            return ConnectionInfo(datetime.now(), True, self.__get_internet_address(60))
        except:
            self.__invalidate_cache()
            return ConnectionInfo(datetime.now(), False, "")

    def __invalidate_cache(self):
        self.cache_ip_address = ""
        self.cache_time = datetime.fromtimestamp(555)

    def __get_internet_address(self, max_cache_ttl: int = 60):
        try:
            now = datetime.now()
            if (now - self.cache_time).seconds > max_cache_ttl:
                response = requests.get('http://whatismyip.akamai.com/')
                self.cache_ip_address = response.text
                self.cache_time = now
            return self.cache_ip_address
        except Exception as e:
            return "???"


class ConnetionHistory:
    FILENAME = "history.p"

    def __init__(self, updated_listener):
        self.updated_listener = updated_listener
        self.history_log = self.__load()

    def __load(self):
        try:
            with open(self.FILENAME, "rb") as file:
                data = pickle.load(file)
                return data
        except Exception as e:
            logging.error(e)
            return []

    def __store(self):
        try:
            with open(self.FILENAME, "wb") as file:
                pickle.dump(self.history_log, file)
        except Exception as e:
            logging.error(e)

    def on_connection_info_fetched(self, connection_info: ConnectionInfo):
        if len(self.history_log) > 0 and self.history_log[len(self.history_log) -1] == connection_info:
            return
        if len(self.history_log) > 50:
            del self.history_log[0]
        self.history_log.append(connection_info)
        self.updated_listener(self.history_log)
        self.__store()


class InternetConnectivityMonitorWebthing(Thing):

    # regarding capabilities refer https://iot.mozilla.org/schemas
    # there is also another schema registry http://iotschema.org/docs/full.html not used by webthing

    def __init__(self, description: str, connecttest_period: int, connecttest_url: str):
        Thing.__init__(
            self,
            'urn:dev:ops:connectivitymonitor-1',
            'Connectivity-Monitor',
            ['MultiLevelSensor'],
            description
        )
        self.history = ConnetionHistory(self.__on_connection_history_updated)
        self.connecttest_period = connecttest_period

        self.test_url = Value(connecttest_url)
        self.add_property(
            Property(self,
                     'test_url',
                     self.test_url,
                     metadata={
                         '@type': 'Name',
                         'title': 'url',
                         "type": "string",
                         'description': 'The url to connect',
                         'readOnly': True,
                     }))

        self.testperiod = Value(connecttest_period)
        self.add_property(
            Property(self,
                     'test_period',
                     self.testperiod,
                     metadata={
                         '@type': 'LevelProperty',
                         'title': 'connecttest execution period',
                         'type': 'number',
                         'description': 'The connecttest execution period',
                         'unit': 'sec',
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

        self.connection_history = Value([str(info) for info in self.history.history_log])
        self.add_property(
            Property(self,
                     'connection_history',
                     self.connection_history,
                     metadata={
                         '@type': 'List',
                         'title': 'The connection history',
                         'type': 'list',
                         'description': 'The connection history',
                         'readOnly': True,
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()
        ConnectedRunner().listen(self.__on_connected_data_fetched, self.testperiod.get(), self.test_url.get())

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
        self.connection_history.notify_of_external_update(history)
