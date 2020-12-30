from internet_monitor_webthing.connectivity_monitor_webthing import InternetConnectivityMonitorWebthing
from internet_monitor_webthing.speedtest_monitor_webthing import InternetSpeedMonitorWebthing
from webthing import (MultipleThings, WebThingServer)
import logging


def run_server(hostname: str, port: int, description: str, speedtest_period: int, connecttest_period: int, connecttest_url: str):
    services = []
    if speedtest_period > 0:
        services.append(InternetSpeedMonitorWebthing(description, speedtest_period))
    if connecttest_period > 0:
        services.append(InternetConnectivityMonitorWebthing(description, connecttest_period, connecttest_url))

    if len(services) > 0:
        print("running Internet " + ", ".join([service.get_title() for service in services]) + " on " + hostname + ":" + str(port))
        if len(hostname) > 0:
            server = WebThingServer(MultipleThings(services, "Internet Monitor"), hostname=hostname, port=port)
        else:
            server = WebThingServer(MultipleThings(services, "Internet Monitor"), port=port)
        try:
            logging.info('starting the server')
            logging.info("hosts: " + ", ".join(server.hosts))
            server.start()
        except KeyboardInterrupt:
            logging.info('stopping the server')
            server.stop()
            logging.info('done')
    else:
        print("no service activated")