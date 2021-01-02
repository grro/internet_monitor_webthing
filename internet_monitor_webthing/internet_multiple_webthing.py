from typing import List
from webthing.utils import get_addresses
from internet_monitor_webthing.connectivity_monitor_webthing import InternetConnectivityMonitorWebthing
from internet_monitor_webthing.speedtest_monitor_webthing import InternetSpeedMonitorWebthing
from webthing import (MultipleThings, WebThingServer)
import threading
import logging
import time



class UpdateHosts:

    def __init__(self, hosts: List[str], port : int):
        self.hosts = hosts
        self.port = port
        self.running = True

    def start(self):
        threading.Thread(target=self.run).start()

    def run(self):
        time.sleep(60)
        while self.running:
            for address in get_addresses():
                if address not in self.hosts:
                    self.hosts.extend([
                        address,
                        '{}:{}'.format(address, self.port),
                    ])
                    logging.info("hosts extended with " + address)
            time.sleep(3 * 60 * 60)

    def cancel(self):
        self.running = False


def run_server(hostname: str, port: int, description: str, speedtest_period: int, connecttest_period: int, connecttest_url: str):
    services = []
    if speedtest_period > 0:
        services.append(InternetSpeedMonitorWebthing(description, speedtest_period))
    if connecttest_period > 0:
        services.append(InternetConnectivityMonitorWebthing(description, connecttest_period, connecttest_url))

    if len(services) > 0:
        print("running Internet " + ", ".join([service.get_title() for service in services]) + " on " + hostname + ":" + str(port))
        if len(hostname) > 0:
            logging.info("using hostname: " + hostname)
            server = WebThingServer(MultipleThings(services, "Internet Monitor"), hostname=hostname, port=port)
        else:
            server = WebThingServer(MultipleThings(services, "Internet Monitor"), port=port)

        hosts_updater = UpdateHosts(server.hosts, port)
        try:
            logging.info('starting the server')
            logging.info("supported host headers: " + str(server.hosts))
            hosts_updater.start()
            server.start()
        except KeyboardInterrupt:
            logging.info('stopping the server')
            hosts_updater.cancel()
            server.stop()
            logging.info('done')
    else:
        print("no service activated")