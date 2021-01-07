from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional
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
    ip_info: Dict[str, str]


class ConnectionLog:

    def __init__(self, filename:str = None):
        if filename is None:
            dir = os.path.join("var", "lib", "netmonitor")
            os.makedirs(dir, exist_ok=True)
            self.filename = os.path.join(dir, "log.p")
        else:
            self.filename = filename

        try:
            with open(self.filename, "rb") as file:
                self.entries = pickle.load(file)
        except Exception as e:
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

    def newest(self) -> Optional[ConnectionInfo]:
        if len(self.entries) > 0:
            return self.entries[-1]
        else:
            return None

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
                report.append(entry.date.strftime("%Y-%m-%d %H:%M:%S") + ", " + status + ", " + entry.ip_address + ", " + entry.ip_info['isp'] + ", " + detail)
                previous_entry = entry
            except Exception as e:
                print(e)
        return report


class IpAddressResolver:

    def __init__(self):
        self.cache_ip_address = ""
        self.cache_time = datetime.fromtimestamp(555)

    def get_internet_address(self, max_cache_ttl: int = 0) -> str:
        try:
            now = datetime.now()
            if max_cache_ttl == 0 or (now - self.cache_time).seconds > max_cache_ttl:
                response = requests.get('http://whatismyip.akamai.com/', timeout=60)
                if (response.status_code >= 200) and (response.status_code < 300):
                    self.cache_ip_address = response.text
                    self.cache_time = now
                    logging.info('ip address resolved ' + self.cache_ip_address)
            return self.cache_ip_address
        except Exception as e:
            return ""


class IpInfo:

    EMPTY_INFO = { 'isp': '',
                   'city' : '',
                   'latitude' : '',
                   'longitude' : '' }

    def __init__(self):
        self.cache= dict()
        self.cached_invalidation_time = datetime.fromtimestamp(555)

    def get_ip_info(self, ip: str) -> Dict[str, str]:
        try:
            if (datetime.now() - self.cached_invalidation_time).seconds > (5 * 24 * 60 * 60):
                self.cache = dict()
                self.cached_invalidation_time = datetime.now()
                logging.info('ip info cache invalidated')
            if ip not in self.cache.keys():
                response = requests.get('https://tools.keycdn.com/geo.json?host=' + ip, timeout=60)
                if (response.status_code >= 200) and (response.status_code < 300):
                    data = response.json()
                    self.cache[ip] = { 'isp': data['data']['geo'].get('isp', ''),
                                       'city' : data['data']['geo'].get('city', ''),
                                       'latitude' : str(data['data']['geo'].get('latitude', '')),
                                       'longitude' : str(data['data']['geo'].get('longitude', '')),
                                       }
                    logging.info('ip info fetched ' + ip + ":" + str(self.cache[ip]))
            return self.cache.get(ip, IpInfo.EMPTY_INFO)
        except Exception as e:
            return IpInfo.EMPTY_INFO


class ConnectionTester:

    def __init__(self, connection_log : ConnectionLog):
        self.connection_log = connection_log
        self.address_resolver = IpAddressResolver()
        self.ip_info = IpInfo()

    def listen(self, listener, measure_period_sec, test_uri: str = "http://google.com"):
        threading.Thread(target=self.__measure_periodically, args=(measure_period_sec, test_uri, listener), daemon=True).start()

    def measure(self, test_uri, max_cache_ttl: int) -> ConnectionInfo:
        try:
            requests.get(test_uri, timeout=10) # test call
            ip_address = self.address_resolver.get_internet_address(max_cache_ttl)
            ip_info = self.ip_info.get_ip_info(ip_address)
            return ConnectionInfo(datetime.now(), True, ip_address, ip_info)
        except:
            return ConnectionInfo(datetime.now(), False, "", IpInfo.EMPTY_INFO)

    def __measure_periodically(self, measure_period_sec: int, test_uri: str, listener):
        while True:
            previous_connection_info = self.connection_log.newest()
            try:
                if previous_connection_info is None or not previous_connection_info.is_connected:
                    connected_info = self.measure(test_uri, max_cache_ttl=0)
                else:
                    connected_info = self.measure(test_uri, max_cache_ttl=4 * 60)
                if previous_connection_info is None or self.is_connect_state_changed(connected_info, previous_connection_info) or self.is_ip_address_state_changed(connected_info, previous_connection_info):
                    self.connection_log.append(connected_info)
                    listener(connected_info)
            except Exception as e:
                logging.error(e)
            time.sleep(measure_period_sec)

    def is_connect_state_changed(self, current: ConnectionInfo, previous: ConnectionInfo):
       return current.is_connected != previous.is_connected

    def is_ip_address_state_changed(self, current: ConnectionInfo, previous: ConnectionInfo):
        return current.ip_address != previous.ip_address