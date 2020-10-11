import logging
import argparse
from pi_internet_webthing.internet import run_server
from pi_internet_webthing.unit import register, deregister, printlog, list_installed

PACKAGENAME = 'pi_internet_webthing'
ENTRY_POINT = "netmonitor"
DESCRIPTION = "A web connected local internet speed and connectivity monitor"



def print_info():
    print("usage " + ENTRY_POINT + " --help for command options")
    print("example commands")
    print(" sudo " + ENTRY_POINT + " --command register --port 9496 --speedtest_period 900 --connecttest_period 5 --connecttest_url http://google.com" )
    print(" sudo " + ENTRY_POINT + " --command listen --port 9496 --speedtest_period 900 --connecttest_period 5 --connecttest_url http://google.com")
    if len(list_installed(PACKAGENAME)) > 0:
        print("example commands for registered services")
        for service_info in list_installed(PACKAGENAME):
            port = service_info[1]
            is_active = service_info[2]
            print(" sudo " + ENTRY_POINT + " --command log --port " + port)
            if is_active:
                print(" sudo " + ENTRY_POINT + " --command deregister --port " + port)


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('--command', metavar='command', required=False, type=str, help='the command. Supported commands are: listen (run the webthing service), register (register and starts the webthing service as a systemd unit, deregister (deregisters the systemd unit), log (prints the log)')
    parser.add_argument('--port', metavar='port', required=False, type=int, help='the port of the webthing serivce')
    parser.add_argument('--speedtest_period', metavar='speedtest_period', required=False, type=int, default=0, help='the speedtest period in sec')
    parser.add_argument('--connecttest_period', metavar='connecttest_period', required=False, type=int, default=0, help='the connecttest period in sec')
    parser.add_argument('--connecttest_url', metavar='connecttest_url', required=False, type=str, default="http://google.com", help='the url to connect runnig the connect test')
    args = parser.parse_args()

    if args.command is None or (args.speedtest_period == 0 and args.connecttest_period == 0) :
        print_info()
    elif args.command == 'listen':
        if args.port is None:
            print("--port is mandatory")
        else:
            run_server(int(args.port), DESCRIPTION, args.speedtest_period, args.connecttest_period, args.connecttest_url)
    elif args.command == 'register':
        if args.port is None:
            print("--port is mandatory")
        else:
            print("register " + PACKAGENAME + " on port " + str(args.port) + " with speedtest_period " + str(args.speedtest_period) + "sec and connecttest_period " + str(args.connecttest_period) + "sec")
            register(PACKAGENAME, ENTRY_POINT, int(args.port), args.speedtest_period, args.connecttest_period)
    elif args.command == 'deregister':
        if args.port is None:
            print("--port is mandatory")
        else:
            deregister(PACKAGENAME, int(args.port))
    elif args.command == 'log':
        if args.port is None:
            print("--port is mandatory")
        else:
            printlog(PACKAGENAME, int(args.port))
    else:
        print("usage " + ENTRY_POINT + " --help")


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    main()

