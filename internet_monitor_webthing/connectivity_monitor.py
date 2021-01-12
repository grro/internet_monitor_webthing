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

    def __str__(self):
        return self.date.strftime("%Y-%m-%d %H:%M:%S") + " " + str(self.is_connected)


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
                logging.info("log file " + self.filename + " read. " + str(len(self.entries)) +  " entries found")
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
        self.cache_reset_time = datetime.now()
        self.entry_cached_time = datetime.fromtimestamp(555)

    def clear_cache(self):
        self.cache_reset_time = datetime.now()
        self.entry_cached_time = datetime.fromtimestamp(555)

    def get_max_cache_time_sec(self):
        duration_since_last_reset = (datetime.now() - self.cache_reset_time).seconds + 1
        if duration_since_last_reset < 5 * 60:
            return 10
        elif duration_since_last_reset < 15 * 60:
            return 30
        elif duration_since_last_reset < 60 * 60:
            return 60
        else:
            return 500  # ~8 min

    def get_internet_address(self) -> str:
        try:
            now = datetime.now()
            cache_entry_age = now - self.entry_cached_time
            if cache_entry_age.seconds > self.get_max_cache_time_sec():
                response = requests.get('http://whatismyip.akamai.com/', timeout=60)
                if (response.status_code >= 200) and (response.status_code < 300):
                    self.cache_ip_address = response.text
                    self.entry_cached_time = now
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
        threading.Thread(target=self.measure_periodically, args=(measure_period_sec, test_uri, listener), daemon=True).start()

    def measure(self, test_uri) -> ConnectionInfo:
        # first trial
        connected = self.is_connected(test_uri, 5)
        if not connected:
            self.address_resolver.clear_cache()
            # second trial
            logging.info("first connect call failed. try second one")
            connected = self.is_connected(test_uri, 10)
        if connected:
            ip_address = self.address_resolver.get_internet_address()
            ip_info = self.ip_info.get_ip_info(ip_address)
            return ConnectionInfo(datetime.now(), True, ip_address, ip_info)
        else:
            self.address_resolver.clear_cache()
            return ConnectionInfo(datetime.now(), False, "", IpInfo.EMPTY_INFO)

    def is_connected(self, test_uri, timeout: int) -> bool:
        try:
            requests.get(test_uri, timeout=timeout) # test call
            return True
        except Exception as e:
            logging.error("connect call " + test_uri + " failed", e)
            return False

    def measure_periodically(self, measure_period_sec: int, test_uri: str, listener):
        initial_log_entry = self.connection_log.newest()
        logging.info("current state: " + str(self.connection_log.newest()))
        listener(initial_log_entry)

        while True:
            sleep_time_sec = measure_period_sec
            previous_info = self.connection_log.newest()
            try:
                if previous_info is None or not previous_info.is_connected:
                    self.address_resolver.clear_cache()
                info = self.measure(test_uri)
                if previous_info is None or (info.is_connected != previous_info.is_connected) or (info.ip_address != previous_info.ip_address):
                    self.connection_log.append(info)
                    listener(info)
                if not info.is_connected:
                    sleep_time_sec = 1.5
            except Exception as e:
                logging.error(e)
            time.sleep(sleep_time_sec)
