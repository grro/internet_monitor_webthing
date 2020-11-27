from webthing import (Property, Thing, Value)
from datetime import datetime
from dataclasses import dataclass
from typing import List
import logging
import os
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


class ConnectedRunner:

    def __init__(self):
        self.previous_connection_info = None
        self.cache_ip_address = ""
        self.cache_time = datetime.fromtimestamp(555)

    def listen(self, listener, measure_period_sec, test_uri: str = "http://google.com"):
        threading.Thread(target=self.__measure_periodically, args=(measure_period_sec, test_uri, listener), daemon=True).start()

    def __measure_periodically(self, measure_period_sec: int, test_server: str, listener):
        while True:
            try:
                connected_info = self.__measure(test_server)
                if self.is_state_updated(connected_info):
                    listener(connected_info)
            except Exception as e:
                logging.error(e)
            time.sleep(measure_period_sec)

    def is_state_updated(self, new_connection_info: ConnectionInfo) -> bool:
        try:
            if self.previous_connection_info is not None:
                # state changed
                if self.previous_connection_info.is_connected != new_connection_info.is_connected:
                    return True
                # new ip address assigned
                if (self.previous_connection_info.ip_address is not None) and (self.previous_connection_info.ip_address != new_connection_info.ip_address):
                    return True
            return False
        finally:
            self.previous_connection_info = new_connection_info

    def __measure(self, test_uri) -> ConnectionInfo:
        try:
            requests.get(test_uri)
            ip_address = self.__get_internet_address(60)
            return ConnectionInfo(datetime.now(), True, ip_address)
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
                if (response.status_code >= 200) and (response.status_code < 300):
                    self.cache_ip_address = response.text
                    self.cache_time = now
            return self.cache_ip_address
        except Exception as e:
            return "???"


class ConnectionHistory:

    def __init__(self, updated_listener):
        self.updated_listener = updated_listener
        dir = os.path.join("var", "lib", "netmonitor2")
        os.makedirs(dir, exist_ok=True)
        self.filename = os.path.join(dir, "history.p")
        logging.info("connection history file: " + str(self.filename))
        self.history_log = self.__load()

    def __load(self) -> List[ConnectionInfo]:
        try:
            with open(self.filename, "rb") as file:
                data = pickle.load(file)
                return data
        except Exception as e:
            logging.error(e)
            return list()

    def __store(self):
        try:
            with open(self.filename, "wb") as file:
                pickle.dump(self.history_log, file)
        except Exception as e:
            logging.error(e)

    def on_connection_info_fetched(self, connection_info: ConnectionInfo):
        if len(self.history_log) > 500:
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
            'Internet Connectivity Monitor',
            ['MultiLevelSensor'],
            description
        )
        self.history = ConnectionHistory(self.__on_connection_history_updated)
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

        self.test_url = Value(connecttest_url)
        self.add_property(
            Property(self,
                     'test_url',
                     self.test_url,
                     metadata={
                         '@type': 'Name',
                         'title': 'Internet connection test url',
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
                         'title': 'Internet connection test execution period in seconds',
                         'type': 'number',
                         'description': 'The Internet connection test execution period in seconds',
                         'unit': 'sec',
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

        self.connection_history = Value([str(info) for info in self.history.history_log])
        self.add_property(
            Property(self,
                     'connection_history',
                     self.connection_history,
                     metadata={
                         'title': 'Availability report',
                         'type': 'array',
                         'description': 'The availability report',
                         'readOnly': True,
                     }))

        self.ioloop = tornado.ioloop.IOLoop.current()
        ConnectedRunner().listen(self.__on_connected_data_fetched, self.testperiod.get(), self.test_url.get())

        self.__on_connection_history_updated(self.history.history_log)

    def __on_connected_data_fetched(self, connection_info: ConnectionInfo):
        self.history.on_connection_info_fetched(connection_info)
        self.ioloop.add_callback(self.__update_connected_props, connection_info)

    def __update_connected_props(self, connection_info: ConnectionInfo):
        self.internet_connected.notify_of_external_update(connection_info.is_connected)
        self.ip_address.notify_of_external_update(connection_info.ip_address)

    def __on_connection_history_updated(self, connection_history: List[ConnectionInfo]):
        self.ioloop.add_callback(self.__update_connection_history_prop, connection_history)

    def __update_connection_history_prop(self, connection_history: List[ConnectionInfo]):
        self.connection_history.notify_of_external_update(InternetConnectivityMonitorWebthing.to_history_report(connection_history))

    @staticmethod
    def to_history_report(connection_history: List[ConnectionInfo]):
        history_with_duration = list()
        previous_connected = True
        previous_date = None
        for info in connection_history:
            elapsed = ""
            if previous_date is not None and info.is_connected and not previous_connected:
                elapsed_sec = int((info.date - previous_date).total_seconds())
                elapsed = InternetConnectivityMonitorWebthing.print_duration(elapsed_sec)
            previous_date = info.date
            previous_connected = info.is_connected
            if info.ip_address is None:
                ip_address = ""
            else:
                ip_address = info.ip_address

            if info.is_connected:
                status = "reconnected"
            else:
                status = "disconnected"
            history_with_duration.append(info.date.isoformat() + ", " + status + ", " + ip_address + ", " + elapsed)
        return history_with_duration


    @staticmethod
    def print_duration(duration: int):
        if duration > (60 * 60):
            return "reconnected after {0:.1f} h".format(duration/(60*60))
        elif duration > 60:
            return "reconnected after {0:.1f} min".format(duration/60)
        else:
            return "reconnected after {0:.1f} sec".format(duration)
