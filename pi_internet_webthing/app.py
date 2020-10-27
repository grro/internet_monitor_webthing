from os import system, remove
from os import listdir
import pathlib
import logging
import subprocess
import argparse



class App:

    def __init__(self, packagename: str, entrypoint: str, description: str):
        self.unit = Unit(packagename)
        self.packagename = packagename
        self.entrypoint = entrypoint
        self.desription = description

    def do_add_argument(self, parser):
        pass

    def do_process_command(self, command:str, hostname: str, port: int, verbose: bool, args):
        return False

    def do_additional_listen_example_params(self):
        return ""

    def print_info(self):
        print("usage " + self.entrypoint + " --help for command options")
        print("example commands")
        print(" sudo " + self.entrypoint + " --command register --hostname 192.168.0.23 --port 9496 " + self.do_additional_listen_example_params())
        print(" sudo " + self.entrypoint + " --command listen --hostname 192.168.0.23 --port 9496 " + self.do_additional_listen_example_params())
        if len(self.unit.list_installed()) > 0:
            print("example commands for registered services")
            for service_info in self.unit.list_installed():
                host = service_info[1]
                port = service_info[2]
                is_active = service_info[3]
                print(" sudo " + self.entrypoint + " --command log --hostname " + host + " --port " + port)
                if is_active:
                    print(" sudo " + self.entrypoint + " --command deregister --hostname " + host + " --port " + port)


    def handle_command(self):
        parser = argparse.ArgumentParser(description=self.desription)
        parser.add_argument('--command', metavar='command', required=False, type=str, help='the command. Supported commands are: listen (run the webthing service), register (register and starts the webthing service as a systemd unit, deregister (deregisters the systemd unit), log (prints the log)')
        parser.add_argument('--port', metavar='port', required=False, type=int, help='the port of the webthing serivce')
        parser.add_argument('--hostname', metavar='hostname', required=False, type=str, help='the hostname of the webthing serivce')
        parser.add_argument('--verbose', metavar='verbose', required=False, type=bool, default=False, help='activates verbose output')
        self.do_add_argument(parser)
        args = parser.parse_args()

        if args.verbose:
            log_level=logging.DEBUG
        else:
            log_level=logging.INFO
        logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level=log_level, datefmt='%Y-%m-%d %H:%M:%S')

        if args.command is None:
            self.print_info()
        elif args.command == 'deregister':
            if args.hostname is None:
                print("--hostname is mandatory")
            elif args.port is None:
                print("--port is mandatory")
            else:
                self.unit.deregister(args.hostname, int(args.port))
        elif args.command == 'log':
            if args.hostname is None:
                print("--hostname is mandatory")
            elif args.port is None:
                print("--port is mandatory")
            else:
                self.unit.printlog(int(args.port))
        else:
            if args.hostname is not None and args.port is not None:
                if self.do_process_command(args.command, args.hostname, args.port, args.verbose, args):
                    return
        print("usage " + self.entrypoint + " --help")



class Unit:

    def __init__(self, packagename: str):
        self.packagename = packagename

    def register(self, hostname: str, port: int, unit: str):
        service = self.packagename + "_" + hostname.encode("ascii").hex() + "_" + str(port) + ".service"
        unit_file_fullname = str(pathlib.Path("/", "etc", "systemd", "system", service))
        with open(unit_file_fullname, "w") as file:
            file.write(unit)
        system("sudo systemctl daemon-reload")
        system("sudo systemctl enable " + service)
        system("sudo systemctl restart " + service)
        system("sudo systemctl status " + service)

    def deregister(self, hostname: str, port: int):
        service = self.packagename + "_" + hostname.encode("ascii").hex() + "_" + str(port) + ".service"
        unit_file_fullname = str(pathlib.Path("/", "etc", "systemd", "system", service))
        system("sudo systemctl stop " + service)
        system("sudo systemctl disable " + service)
        system("sudo systemctl daemon-reload")
        try:
            remove(unit_file_fullname)
        except Exception as e:
            pass

    def printlog(self, port:int):
        service = self.packagename + "_" + str(port) + ".service"
        system("sudo journalctl -f -u " + service)


    def list_installed(self):
        services = []
        try:
            for file in listdir(pathlib.Path("/", "etc", "systemd", "system")):
                if file.startswith(self.packagename) and file.endswith('.service'):
                    idx = file.rindex('_')
                    port = file[idx+1:file.index('.service')]
                    host = bytearray.fromhex(file[file[:idx].rindex('_')+1:idx]).decode()
                    services.append((file, host, port, self.is_active(file)))
        except Exception as e:
            pass
        return services

    def is_active(self, servicename: str):
        cmd = '/bin/systemctl status %s' % servicename
        proc = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE,encoding='utf8')
        stdout_list = proc.communicate()[0].split('\n')
        for line in stdout_list:
            if 'Active:' in line:
                if '(running)' in line:
                    return True
        return False
