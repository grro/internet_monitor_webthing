import os
import logging
import argparse
from pi_internet_webthing.internet import run_server
from pi_internet_webthing.unit import register, deregister, printlog

PACKAGENAME = 'pi_internet_webthing'
ENTRY_POINT = "internet"
DESCRIPTION = "A web connected local internet info agent running on Raspberry Pi"


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('--command', metavar='command', required=True, type=str, help='the command. Supported commands are: listen (run the webthing service), register (register and starts the webthing service as a systemd unit, deregister (deregisters the systemd unit), log (prints the log)')
    parser.add_argument('--port', metavar='port', required=True, type=int, help='the port of the webthing serivce')
    parser.add_argument('--speedtest_period', metavar='speedtest_period', required=False, type=int, default= 15*60, help='the speedtest period in sec')
    parser.add_argument('--connecttest_period', metavar='connecttest_period', required=False, type=int, default= 5, help='the connecttest period in sec')
    args = parser.parse_args()

    if args.command == 'listen':
        print("running " + PACKAGENAME + " on port " + str(args.port) + " with speedtest_period " + str(args.speedtest_period) + "sec and connecttest_period " + str(args.connecttest_period) + "sec")
        run_server(int(args.port), DESCRIPTION, args.speedtest_period, args.connecttest_period)
    elif args.command == 'register':
        print("register " + PACKAGENAME + " on port " + str(args.port) + " with speedtest_period " + str(args.speedtest_period) + "sec and connecttest_period " + str(args.connecttest_period) + "sec")
        register(PACKAGENAME, ENTRY_POINT, int(args.port), args.speedtest_period, args.connecttest_period)
    elif args.command == 'deregister':
        deregister(PACKAGENAME, int(args.port))
    elif args.command == 'log':
        printlog(PACKAGENAME, int(args.port))
    else:
        print("usage " + ENTRY_POINT + " --help")


if __name__ == '__main__':
    log_level = os.environ.get("LOGLEVEL", "INFO")
    logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level=logging.getLevelName(log_level), datefmt='%Y-%m-%d %H:%M:%S')
    main()

