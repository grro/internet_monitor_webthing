from pi_internet_webthing.connectivity_monitor import InternetConnectivityMonitorWebthing
from pi_internet_webthing.speedtest_monitor import InternetSpeedMonitorWebthing
from webthing import (MultipleThings, WebThingServer)
import logging


def run_server(port, description: str, speedtest_period: int, connecttest_period: int, connecttest_url: str):
    services = []
    if speedtest_period > 0:
        services.append(InternetSpeedMonitorWebthing(description, speedtest_period))
    if connecttest_period > 0:
        services.append(InternetConnectivityMonitorWebthing(description, connecttest_period, connecttest_url))

    if len(services) > 0:
        print("running Internet " + ", ".join([service.get_title() for service in services]) + " on port " + str(port))
        server = WebThingServer(MultipleThings(services, "internet monitor"), port=port)
        try:
            logging.info('starting the server')
            server.start()
        except KeyboardInterrupt:
            logging.info('stopping the server')
            server.stop()
            logging.info('done')
    else:
        print("no service activated")