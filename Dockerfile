FROM  alpine:3.12.3

ENV PYTHONUNBUFFERED=1
ENV port 8555
ENV speedtest_period 900
ENV connecttest_period 5

RUN apk add --no-cache python3
RUN if [ ! -e /usr/bin/python ]; then ln -sf python3 /usr/bin/python ; fi
RUN python3 -m ensurepip
RUN rm -r /usr/lib/python*/ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools wheel
RUN if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi
COPY dist/*.whl .
RUN ls
RUN python3 -m pip install *.whl
RUN ls

CMD netmonitor --command listen --hostname $hostname --port $port --speedtest_period $speedtest_period --connecttest_period $connecttest_period