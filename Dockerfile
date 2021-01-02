FROM python:3.9.1-slim

ENV port 8555
ENV speedtest_period 900
ENV connecttest_period 5

ADD . /tmp/
WORKDIR /tmp/
RUN  python /tmp/setup.py install
WORKDIR /
RUN rm -r /tmp/

CMD netmonitor --command listen --hostname $hostname --port $port --speedtest_period $speedtest_period --connecttest_period $connecttest_period
