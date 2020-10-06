import requests
import threading
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass


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
