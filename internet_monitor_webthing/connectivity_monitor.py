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


class ConnectionLog:

    def __init__(self, filename:str = None):
        if filename is None:
            dir = os.path.join("var", "lib", "netmonitor3")
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
            status = "connected" if entry.is_connected else "disconnected"
            detail = ""
            if previous_entry is not None:
                elapsed_sec = int((entry.date - previous_entry.date).total_seconds())
                if entry.is_connected and not previous_entry.is_connected:
                    detail = "reconnected after " + self.print_duration(elapsed_sec)
                elif len(entry.ip_address) > 0 and len(previous_entry.ip_address) > 0 and entry.ip_address != previous_entry.ip_address:
                    detail = "ip address updated"
            report.append(entry.date.strftime("%Y-%m-%d %H:%M:%S") + ", " + status + ", " + entry.ip_address + ", " + detail)
            previous_entry = entry
        return report


class IpAddressResolver:

    def __init__(self):
        self.cache_ip_address = ""
        self.cache_time = datetime.fromtimestamp(555)

    def __invalidate_cache(self):
        self.cache_ip_address = ""
        self.cache_time = datetime.fromtimestamp(555)

    def get_internet_address(self, max_cache_ttl: int = 60) -> str:
        try:
            now = datetime.now()
            if (now - self.cache_time).seconds > max_cache_ttl:
                response = requests.get('http://whatismyip.akamai.com/')
                if (response.status_code >= 200) and (response.status_code < 300):
                    self.cache_ip_address = response.text
                    self.cache_time = now
            return self.cache_ip_address
        except Exception as e:
            return ""


class ConnectionTester:

    def __init__(self, connection_log : ConnectionLog):
        self.connection_log = connection_log
        self.address_resolver = IpAddressResolver()

    def listen(self, listener, measure_period_sec, test_uri: str = "http://google.com"):
        threading.Thread(target=self.__measure_periodically, args=(measure_period_sec, test_uri, listener), daemon=True).start()

    def measure(self, test_uri) -> ConnectionInfo:
        try:
            requests.get(test_uri) # test call
            ip_address = self.address_resolver.get_internet_address(60)
            return ConnectionInfo(datetime.now(), True, ip_address)
        except:
            return ConnectionInfo(datetime.now(), False, "")

    def __measure_periodically(self, measure_period_sec: int, test_uri: str, listener):
        previous_connection_info = None
        while True:
            try:
                connected_info = self.measure(test_uri)
                if previous_connection_info is None or  connected_info.is_connected != previous_connection_info.is_connected or connected_info.ip_address != previous_connection_info.ip_address:
                    self.connection_log.append(connected_info)
                    listener(connected_info)
                previous_connection_info = connected_info
            except Exception as e:
                logging.error(e)
            time.sleep(measure_period_sec)



log = ConnectionLog("c:\\temp\\test.p")
print(log.filename)

log.append(ConnectionInfo(datetime.strptime("2020-12-28 14:22:12.17512", '%Y-%m-%d %H:%M:%S.%f'), True, "75.45.2.1"))
log.append(ConnectionInfo(datetime.strptime("2020-12-28 15:3:13.17512", '%Y-%m-%d %H:%M:%S.%f'), False, ""))
log.append(ConnectionInfo(datetime.strptime("2020-12-28 16:3:13.17512", '%Y-%m-%d %H:%M:%S.%f'), True, ""))
log.append(ConnectionInfo(datetime.strptime("2020-12-28 17:3:13.17512", '%Y-%m-%d %H:%M:%S.%f'), True, "54.5.3.2"))
log.append(ConnectionInfo(datetime.strptime("2020-12-28 18:3:13.17512", '%Y-%m-%d %H:%M:%S.%f'), False, ""))
log.append(ConnectionInfo(datetime.strptime("2020-12-28 18:13:09.17512", '%Y-%m-%d %H:%M:%S.%f'), True, "45.3.3.2"))
log.append(ConnectionInfo(datetime.strptime("2020-12-28 20:3:13.17512", '%Y-%m-%d %H:%M:%S.%f'), True, "122.4.3.2"))


print("\nall")
for entry in log.entries:
    print(entry)

print("\nreport")
for entry in log.to_report():
    print(entry)
