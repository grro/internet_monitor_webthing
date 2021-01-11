FROM python:3.9.1-alpine

ENV port 8433
ENV speedtest_period 900
ENV connecttest_period 10

LABEL org.label-schema.schema-version="1.0" \
      org.label-schema.name="InternetspeedAndConnectivityMonitor" \
      org.label-schema.description="A web connected local internet speed and connectivity monitor. It implements an internet monitor agent providing a speed monitor [WebThing API](https://iot.mozilla.org/wot/) as well as a connectivity monitor [WebThing API](https://iot.mozilla.org/wot/)" \
      org.label-schema.url="https://github.com/grro/internet_monitor_webthing" \
      org.label-schema.docker.cmd="docker run -p 8433:8433 grro/internet-monitor"

ADD . /tmp/
WORKDIR /tmp/
RUN  python /tmp/setup.py install
WORKDIR /
RUN rm -r /tmp/

CMD netmonitor --command listen --port $port --speedtest_period $speedtest_period --connecttest_period $connecttest_period
