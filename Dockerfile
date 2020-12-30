FROM  alpine:3.12.3

ENV PYTHONUNBUFFERED=1
ENV port 8555
ENV speedtest_period 900
ENV connecttest_period 5

RUN apk add --no-cache python3 && \
   if [ ! -e /usr/bin/python ]; then ln -sf python3 /usr/bin/python ; fi && \
   python3 -m ensurepip && \
   rm -r /usr/lib/python*/ensurepip && \
   pip3 install --no-cache --upgrade pip setuptools wheel && \
   if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi
RUN mkdir /tmp/temp_whl_files
COPY dist/*.whl /tmp/temp_whl_files
RUN python3 -m pip install /tmp/temp_whl_files/*.whl
RUN rm -r /tmp/temp_whl_files

CMD netmonitor --command listen --hostname $hostname --port $port --speedtest_period $speedtest_period --connecttest_period $connecttest_period