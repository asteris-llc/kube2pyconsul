"""kube2pyconsul.

Usage:
  kube2pyconsul.py [-v <loglevel>] [--verify-ssl] [--consul-agent=<consul-uri>] [--kube-master=<kubeapi-uri>] [--consul-auth=<user,pass>] [--kube-auth=<user,pass>]
  kube2pyconsul.py (-h | --help)

Options:
  -h --help     Show this screen.
  -v <loglevel>           Set logging level [default: INFO]
  --consul-agent=<consul-uri>  Consul agent location [default: https://127.0.0.1:8500].
  --kube-master=<kubeapi-uri>  Kubeapi location [default: https://127.0.0.1:6443]
  --consul-auth=<user,pass>    Consul http auth credentials [default: None]
  --kube-auth=<user,pass>      Kubernetes http auth credentials [default: None]

"""
from docopt import docopt

import sys
import json
import time
import logging
import requests
import traceback
import multiprocessing

from multiprocessing import Queue
from multiprocessing import Process

args = docopt(__doc__, version='kube2pyconsul 1.0')

logging.basicConfig()
log = multiprocessing.log_to_stderr()
level = logging.getLevelName(args['-v'])
log.setLevel(level)


consul_uri = args['--consul-agent']
consul_auth = tuple(args['--consul-auth'].split(',')) if args['--consul-auth'] != 'None' else None

kubeapi_uri = args['--kube-master']
kube_auth = tuple(args['--kube-auth'].split(',')) if args['--kube-auth'] != 'None' else None

verify_ssl = args['--verify-ssl']


log.info("Starting with: consul={0}, kubeapi={1}".format(consul_uri, kubeapi_uri))

def getservice(event, ports):
    return {"Name": event['object']['metadata']['name'], 
            "ID": '{}-{}'.format(event['object']['metadata']['name'], ports['port']),
            "Address": event['object']['spec']['clusterIP'], 
            "Port": ports['port']}

def services_monitor(queue):
    while True:
        try:
            r = requests.get('{base}/api/v1/services?watch=true'.format(base=kubeapi_uri), 
                                 stream=True, verify=verify_ssl, auth=kube_auth)
            for line in r.iter_lines():
                if line:
                    event = json.loads(line)
                    queue.put(('service', event))
        except Exception as e:
          log.debug(traceback.format_exc())
          log.error(e)
          log.error("Sleeping and restarting afresh.")
          time.sleep(10)

    
def pods_monitor(queue):
    while True:
        try:
            r = requests.get('{base}/api/v1/pods?watch=true'.format(base=kubeapi_uri), 
                                 stream=True, verify=verify_ssl, auth=kube_auth)
            for line in r.iter_lines():
                if line:
                    event = json.loads(line)
                    queue.put(('pod', event))
        except Exception as e:
          log.debug(traceback.format_exc())
          log.error(e)
          log.error("Sleeping and restarting afresh.")
          time.sleep(10)


def registration(queue):
    while True:
        context, event = queue.get(block=True)
        
        if context == 'service':
            if event['type'] == 'ADDED':
                for ports in event['object']['spec']['ports']:
                    service = getservice(event, ports)
                    r = ''
                    
                    while True:
                        try:
                            r = requests.put('{base}/v1/agent/service/register'.format(base=consul_uri), 
                                                  json=service, auth=consul_auth, verify=verify_ssl)
                            break
                        except Exception as e:
                            log.debug(traceback.format_exc())
                            log.error(e)
                            log.error("Sleeping and retrying.")
                            time.sleep(10)
                            
                    if r.status_code == 200:
                        log.info("ADDED service {service} to Consul's catalog".format(service=service))
                    else:
                        log.error("Consul returned non-200 request status code. Could not register service {service}. Continuing on to the next service...".format())
                    sys.stdout.flush()

            elif event['type'] == 'DELETED':
                for ports in event['object']['spec']['ports']:
                    service = getservice(event, ports)
                    r = ''
                    
                    while True:
                        try:
                            r = requests.put('{base}/v1/agent/service/deregister/{name}-{port}'.format(base=consul_uri, name=service['name'], port=service['port']), 
                                             auth=consul_auth, verify=verify_ssl)
                            break
                        except Exception as e:
                            log.debug(traceback.format_exc())
                            log.error(e)
                            log.error("Sleeping and retrying.")
                            time.sleep(10)
                            
                    if r.status_code == 200:
                        log.info("DELETED service {service} from Consul's catalog".format(service=service))
                    else:
                        log.error("Consul returned non-200 request status code. Could not deregister service {service}. Continuing on to the next service...".format())
                    sys.stdout.flush()
                      
        elif context == 'pod':
            pass
        
        
def run():
    q = Queue()
    services_watch = Process(target=services_monitor, args=(q,), name='kube2pyconsul/services')
    pods_watch = Process(target=pods_monitor, args=(q,), name='kube2pyconsul/pods')
    consul_desk = Process(target=registration, args=(q,), name='kube2pyconsul/registration')
    
    services_watch.start()
    pods_watch.start()
    consul_desk.start()
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        services_watch.terminate()
        pods_watch.terminate()
        consul_desk.terminate()
        
        exit()

if __name__ == '__main__':
    run()
