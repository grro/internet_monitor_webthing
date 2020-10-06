from speedtest import Speedtest
import threading
import time
from dataclasses import dataclass


@dataclass
class Speed:
    server: str
    downloadspeed: int
    uploadspeed: int
    ping: float
    report_uri: str


class SpeedtestRunner:

    def listen(self, listener, measure_period_sec):
        threading.Thread(target=self.__measure_periodically, args=(measure_period_sec, listener), daemon=True).start()

    def __measure_periodically(self, measure_period_sec: int, listener):
        while True:
            try:
                speed = self.__measure()
                listener(speed)
            except Exception as e:
                pass
            time.sleep(measure_period_sec)

    def __measure(self) -> Speed:
        s = Speedtest()
        s.download()
        s.upload()
        try:
            link = s.results.share()   # POST data to the speedtest.net API to obtain a share results link
        except:
            link = None
            pass
        metrics = s.results.dict()
        return Speed(metrics['server'].get('sponsor', '') + "/" + metrics['server'].get('name', ''), int(metrics['download']), int(metrics['upload']), metrics['ping'], link)
