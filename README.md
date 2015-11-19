# Usage
```
# python kube2pyconsul.py --help
kube2pyconsul.

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
```

Running a docker container:
```
# docker run -ti zogg/kube2pyconsul:1.0 --consul-agent=https://10.0.0.4:8500 \
                                        --kube-master=https://10.10.64.1:6443 \
                                        --consul-auth=user,pass \
                                        --kube-auth=user,pass
```
