from speedtest import Speedtest
from dataclasses import dataclass
import threading
import time
import logging


@dataclass
class Speed:
    server: str
    downloadspeed: int
    uploadspeed: int
    ping: float
    report_uri: str


class SpeedtestRunner:

    def __init__(self, listener):
        self.listener = listener

    def run_periodically(self, measure_period_sec: int):
        threading.Thread(target=self.__measure_periodically, args=(measure_period_sec,), daemon=True).start()

    def __measure_periodically(self, measure_period_sec: int):
        while True:
            try:
                speed = self.measure()
                self.listener(speed)
            except Exception as e:
                logging.error(e)
            time.sleep(measure_period_sec)

    def measure(self) -> Speed:
        s = Speedtest()
        s.download()
        s.upload()
        try:
            link = s.results.share()   # POST data to the speedtest.net API to obtain a share results link
        except:
            link = None
        metrics = s.results.dict()
        return Speed(metrics['server'].get('sponsor', '') + "/" + metrics['server'].get('name', ''), int(metrics['download']), int(metrics['upload']), metrics['ping'], link)
