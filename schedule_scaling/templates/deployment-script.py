from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time
import datetime
import random
import os

time.sleep(random.uniform(1, 10))

if os.getenv("KUBERNETES_SERVICE_HOST"):
    # ServiceAccountの権限で実行する
    config.load_incluster_config()
else:
    # $HOME/.kube/config から読み込む
    config.load_kube_config()

v1 = client.AppsV1Api()

time = "%(time)s"
namespace = "%(namespace)s"
name = "%(name)s"
replicas = %(replicas)d

if replicas > -1:
    body = {"spec": {"replicas": replicas}}
    try:
        v1.patch_namespaced_deployment(name, namespace, body)
    except ApiException as err:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "deployment default/reserve-node has not been patched",
            err,
        )

deployment = v1.read_namespaced_deployment(name, namespace)
if deployment.spec.replicas == replicas:
    print(
        "[INFO]",
        datetime.datetime.now(),
        "Deployment {}/{} has been scaled successfully to {} replica at {}".format(
            namespace, name, replicas, time
        ),
    )
else:
    print(
        "[ERROR]",
        datetime.datetime.now(),
        "Something went wrong... deployment %(namespace)s/%(name)s has not been scaled to %(replicas)s"
    )
