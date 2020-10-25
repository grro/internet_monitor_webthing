import pathlib
from os import system, remove
from string import Template
from os import listdir
import subprocess


UNIT_TEMPLATE = Template('''
[Unit]
Description=$packagename
After=syslog.target

[Service]
Type=simple
ExecStart=$entrypoint --command listen --hostname $hostname --port $port --verbose $verbose --speedtest_period $speedtest_period --connecttest_period $connecttest_period
SyslogIdentifier=$packagename
StandardOutput=syslog
StandardError=syslog
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
''')


def register(packagename: str, entrypoint: str, hostname: str, port: int, verbose: bool, speedtest_period: int, connecttest_period:int):
    unit = UNIT_TEMPLATE.substitute(packagename=packagename, entrypoint=entrypoint, hostname=hostname, port=port, verbose=verbose, speedtest_period=speedtest_period, connecttest_period=connecttest_period)
    service = packagename + "_" + hostname.encode("ascii").hex() + "_" + str(port) + ".service"
    unit_file_fullname = str(pathlib.Path("/", "etc", "systemd", "system", service))
    with open(unit_file_fullname, "w") as file:
        file.write(unit)
    system("sudo systemctl daemon-reload")
    system("sudo systemctl enable " + service)
    system("sudo systemctl restart " + service)
    system("sudo systemctl status " + service)


def deregister(packagename, hostname: str, port):
    print("deregister " + packagename + " on port " + str(port))

    service = packagename + "_" + hostname.encode("ascii").hex() + "_" + str(port) + ".service"
    unit_file_fullname = str(pathlib.Path("/", "etc", "systemd", "system", service))
    system("sudo systemctl stop " + service)
    system("sudo systemctl disable " + service)
    system("sudo systemctl daemon-reload")
    try:
        remove(unit_file_fullname)
    except Exception as e:
        pass

def printlog(packagename, port):
    service = packagename + "_" + str(port) + ".service"
    system("sudo journalctl -f -u " + service)


def list_installed(packagename: str):
    services = []
    try:
        for file in listdir(pathlib.Path("/", "etc", "systemd", "system")):
            if file.startswith(packagename) and file.endswith('.service'):
                idx = file.rindex('_')
                port = file[idx+1:file.index('.service')]
                host = bytearray.fromhex(file[file[:idx].rindex('_')+1:idx]).decode()
                services.append((file, host, port, is_active(file)))
    except Exception as e:
        pass
    return services


def is_active(serivcename: str):
    cmd = '/bin/systemctl status %s' % serivcename
    proc = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE,encoding='utf8')
    stdout_list = proc.communicate()[0].split('\n')
    for line in stdout_list:
        if 'Active:' in line:
            if '(running)' in line:
                return True
    return False


