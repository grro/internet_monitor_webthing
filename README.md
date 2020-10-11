# pi_internet_webthing
A web connected local internet speed and connectivity monitor 

This project provides a [webthing API](https://iot.mozilla.org/wot/) to a internet monitor agent.

The pi_internet_webthing package exposes an http webthing endpoint which supports reading the internet speed results 
as well as the internet connectivity results via http 
E.g. 
```
# webthing has been started on host 192.168.0.23

# internet speed
curl http://192.168.0.23:8433/0/properties
{
   "test_period": 900,
   "downloadspeed": 215.2,
   "uploadspeed": 11,
   "ping": 17.763,
   "testdate": "2020-10-11T13:44:51.346706",
   "speedtest_server": "Mobile Breitbandnetze GmbH/Freisbach",
   "speedtest_report_uri": "http://www.speedtest.net/result/10231336474.png"
}

# connectivity 
curl http://192.168.0.23:8433/1/properties
{
   "test_url": "http://google.com",
   "test_period": 5,
   "connected": true,
   "ip_address": "95.88.57.72"
}
```

To install this software you may use [PIP](https://realpython.com/what-is-pip/) package manager such as shown below
```
sudo pip install pi_internet_webthing
```

After this installation you may start the webthing http endpoint inside your python code or via command line using
```
sudo netmonitor --command listen --port 8433 --speedtest_period 900 --connecttest_period 5 
```
Here, the webthing API will be bind to the local port 8433. The internet speed montior as well as the connectivity monitor will be started.
The speed test will be executed each 15 min (900 sec), the connectivity test will be executed each 5 sec.  

Alternatively to the *listen* command, you can use the *register* command to register and start the webthing service as systemd unit. 
By doing this the webthing service will be started automatically on boot. Starting the server manually using the *listen* command is no longer necessary. 
```
sudo netmonitor --command register --port 8433 --speedtest_period 900 --connecttest_period 5 
```  
