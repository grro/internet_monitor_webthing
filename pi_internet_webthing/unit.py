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
ExecStart=$entrypoint --command listen --port $port --speedtest_period $speedtest_period --connecttest_period $connecttest_period
SyslogIdentifier=$packagename
StandardOutput=syslog
StandardError=syslog
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
''')


def register(packagename, entrypoint, port, speedtest_period, connecttest_period):
    unit = UNIT_TEMPLATE.substitute(packagename=packagename, entrypoint=entrypoint, port=port, speedtest_period=speedtest_period, connecttest_period=connecttest_period)
    service = packagename + "_" + str(port) + ".service"
    unit_file_fullname = str(pathlib.Path("/", "etc", "systemd", "system", service))
    with open(unit_file_fullname, "w") as file:
        file.write(unit)
    system("sudo systemctl daemon-reload")
    system("sudo systemctl enable " + service)
    system("sudo systemctl restart " + service)
    system("sudo systemctl status " + service)


def deregister(packagename, port):
    print("deregister " + packagename + " on port " + str(port))

    service = packagename + "_" + str(port) + ".service"
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
                port = file[file.rindex('_')+1:file.index('.service')]
                services.append((file, port, is_active(file)))
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

