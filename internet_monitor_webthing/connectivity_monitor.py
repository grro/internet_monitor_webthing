from datetime import datetime
from dataclasses import dataclass
from typing import List
import logging
import time
import requests
import threading
import os
import pickle

@dataclass()
class ConnectionInfo:
    date: datetime
    is_connected: bool
    ip_address: str
    isp: str


class ConnectionLog:

    def __init__(self, filename:str = None):
        if filename is None:
            dir = os.path.join("var", "lib", "netmonitor")
            os.makedirs(dir, exist_ok=True)
            self.filename = os.path.join(dir, "history.p")
        else:
            self.filename = filename

        try:
            with open(self.filename, "rb") as file:
                self.entries = pickle.load(file)
        except Exception as e:
            logging.error(e)
            self.entries = list()

    def append(self, connection_info : ConnectionInfo):
        if len(self.entries) > 500:
            del self.entries[0]
        self.entries.append(connection_info)
        self.__store()

    def __store(self):
        try:
            with open(self.filename, "wb") as file:
                pickle.dump(self.entries, file)
        except Exception as e:
            logging.error(e)

    def print_duration(self, duration: int):
        if duration > (60 * 60):
            return "{0:.1f} h".format(duration/(60*60))
        elif duration > 60:
            return "{0:.1f} min".format(duration/60)
        else:
            return "{0:.1f} sec".format(duration)

    def to_report(self) -> List[str]:
        report = list()

        previous_entry = None
        for entry in self.entries:
            try:
                status = "connected" if entry.is_connected else "disconnected"
                detail = ""
                if previous_entry is not None:
                    elapsed_sec = int((entry.date - previous_entry.date).total_seconds())
                    if entry.is_connected and not previous_entry.is_connected:
                        detail = "reconnected after " + self.print_duration(elapsed_sec)
                    elif len(entry.ip_address) > 0 and len(previous_entry.ip_address) > 0 and entry.ip_address != previous_entry.ip_address:
                        detail = "ip address updated"
                report.append(entry.date.strftime("%Y-%m-%d %H:%M:%S") + ", " + status + ", " + entry.ip_address + ", " + entry.isp + ", " + detail)
                previous_entry = entry
            except Exception as e:
                print(e)
        return report


class IpAddressResolver:

    def __init__(self):
        self.cache_ip_address = ""
        self.cache_time = datetime.fromtimestamp(555)

    def invalidate_cache(self):
        self.cache_time = datetime.fromtimestamp(555)

    def get_internet_address(self, max_cache_ttl: int = 60) -> str:
        try:
            now = datetime.now()
            if (now - self.cache_time).seconds > max_cache_ttl:
                response = requests.get('http://whatismyip.akamai.com/', timeout=10)
                if (response.status_code >= 200) and (response.status_code < 300):
                    self.cache_ip_address = response.text
                    self.cache_time = now
            return self.cache_ip_address
        except Exception as e:
            return ""


class IpInfo:

    def __init__(self):
        self.cache= dict()
        self.cached_invalidation_time = datetime.fromtimestamp(555)

    def get_ip_info(self, ip: str) -> str:
        try:
            if (datetime.now() - self.cached_invalidation_time).seconds > (4 * 24 * 60 * 60):
                self.cache = dict()
                self.cached_invalidation_time = datetime.now()
            if ip not in self.cache.keys():
                response = requests.get('https://tools.keycdn.com/geo.json?host=' + ip, timeout=60)
                if (response.status_code >= 200) and (response.status_code < 300):
                    data = response.json()
                    self.cache[ip] = data['data']['geo']['isp']
            return self.cache.get(ip, "")
        except Exception as e:
            return ""


class ConnectionTester:

    def __init__(self, connection_log : ConnectionLog):
        self.connection_log = connection_log
        self.address_resolver = IpAddressResolver()
        self.ip_info = IpInfo()

    def listen(self, listener, measure_period_sec, test_uri: str = "http://google.com"):
        threading.Thread(target=self.__measure_periodically, args=(measure_period_sec, test_uri, listener), daemon=True).start()

    def measure(self, test_uri) -> ConnectionInfo:
        try:
            requests.get(test_uri, timeout=7) # test call
            ip_address = self.address_resolver.get_internet_address(max_cache_ttl=112)
            isp = self.ip_info.get_ip_info(ip_address)
            return ConnectionInfo(datetime.now(), True, ip_address, isp)
        except:
            self.address_resolver.invalidate_cache()
            return ConnectionInfo(datetime.now(), False, "", "")

    def __measure_periodically(self, measure_period_sec: int, test_uri: str, listener):
        previous_connection_info = None
        while True:
            try:
                connected_info = self.measure(test_uri)
                if previous_connection_info is None or self.is_connect_state_changed(connected_info, previous_connection_info) or self.is_ip_address_state_changed(connected_info, previous_connection_info):
                    self.connection_log.append(connected_info)
                    listener(connected_info)
                    previous_connection_info = connected_info
            except Exception as e:
                logging.error(e)
            time.sleep(measure_period_sec)

    def is_connect_state_changed(self, current: ConnectionInfo, previous: ConnectionInfo):
       return current.is_connected != previous.is_connected

    def is_ip_address_state_changed(self, current: ConnectionInfo, previous: ConnectionInfo):
        return current.ip_address != previous.ip_address