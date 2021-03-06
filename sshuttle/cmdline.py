import re
import socket
import sshuttle.helpers as helpers
import sshuttle.client as client
import sshuttle.firewall as firewall
import sshuttle.hostwatch as hostwatch
import sshuttle.ssyslog as ssyslog
from sshuttle.options import parser, parse_ipport
from sshuttle.helpers import family_ip_tuple, log, Fatal


def main():
    opt = parser.parse_args()

    if opt.daemon:
        opt.syslog = 1
    if opt.wrap:
        import sshuttle.ssnet as ssnet
        ssnet.MAX_CHANNEL = opt.wrap
    if opt.latency_buffer_size:
        import sshuttle.ssnet as ssnet
        ssnet.LATENCY_BUFFER_SIZE = opt.latency_buffer_size
    helpers.verbose = opt.verbose

    try:
        if opt.firewall:
            if opt.subnets or opt.subnets_file:
                parser.error('exactly zero arguments expected')
            return firewall.main(opt.method, opt.syslog)
        elif opt.hostwatch:
            return hostwatch.hw_main(opt.subnets, opt.auto_hosts)
        else:
            includes = opt.subnets + opt.subnets_file
            excludes = opt.exclude
            if opt.no_firewall:
                includes = []
                excludes = []
                opt.auto_hosts = False
                opt.auto_nets = False

            if not any((includes, opt.auto_nets, opt.no_firewall)):
                parser.error('at least one subnet, subnet file, -N, '
                             'or --no-firewall expected')
            remotename = opt.remote
            if remotename == '' or remotename == '-':
                remotename = None
            nslist = [family_ip_tuple(ns) for ns in opt.ns_hosts]
            if opt.seed_hosts:
                sh = re.split(r'[\s,]+', (opt.seed_hosts or "").strip())
            elif opt.auto_hosts:
                sh = []
            else:
                sh = None
            if opt.listen:
                ipport_v6 = None
                ipport_v4 = None
                lst = opt.listen.split(",")
                for ip in lst:
                    family, ip, port = parse_ipport(ip)
                    if family == socket.AF_INET6:
                        ipport_v6 = (ip, port)
                    else:
                        ipport_v4 = (ip, port)
            else:
                # parse_ipport4('127.0.0.1:0')
                ipport_v4 = "auto"
                # parse_ipport6('[::1]:0')
                ipport_v6 = "auto" if not opt.disable_ipv6 else None
            if opt.syslog:
                ssyslog.start_syslog()
                ssyslog.close_stdin()
                ssyslog.stdout_to_syslog()
                ssyslog.stderr_to_syslog()
            dns_port = opt.dns_port if opt.dns else -1
            return_code = client.main(ipport_v6, ipport_v4,
                                      opt.ssh_cmd,
                                      remotename,
                                      opt.python,
                                      opt.latency_control,
                                      dns_port,
                                      nslist,
                                      opt.method,
                                      sh,
                                      opt.auto_hosts,
                                      opt.auto_nets,
                                      includes,
                                      excludes,
                                      opt.daemon,
                                      opt.to_ns,
                                      opt.pidfile,
                                      opt.user,
                                      opt.sudo_pythonpath)

            if return_code == 0:
                log('Normal exit code, exiting...')
            else:
                log('Abnormal exit code %d detected, failing...' % return_code)
            return return_code

    except Fatal as e:
        log('fatal: %s\n' % e)
        return 99
    except KeyboardInterrupt:
        log('\n')
        log('Keyboard interrupt: exiting.\n')
        return 1
