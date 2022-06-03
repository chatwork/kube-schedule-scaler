from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time
import datetime
import sys
import random
import os

time.sleep(random.uniform(1, 10))

if os.getenv("KUBERNETES_SERVICE_HOST"):
    # ServiceAccountの権限で実行する
    config.load_incluster_config()
else:
    # $HOME/.kube/config から読み込む
    config.load_kube_config()

v1 = client.AutoscalingV1Api()

time = "%(time)s"
name = "%(name)s"
namespace = "%(namespace)s"
maxReplicas = %(maxReplicas)d
minReplicas = %(minReplicas)d

def patch_hpa(body):
    try:
        v1.patch_namespaced_horizontal_pod_autoscaler(name, namespace, body)
    except ApiException as err:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "HPA {}/{} has not been updated".format(
                namespace, name
            ),
            err,
        )

if maxReplicas > 0 and minReplicas > 0:
    body = {"spec": {"minReplicas": minReplicas, "maxReplicas": maxReplicas}}

    patch_hpa(body)
    hpa = v1.read_namespaced_horizontal_pod_autoscaler(name, namespace)
    if hpa.spec.max_replicas == maxReplicas and hpa.spec.min_replicas == minReplicas:
        print(
            "[INFO]",
            datetime.datetime.now(),
            "HPA {}/{} has been adjusted to maxReplicas to {} at".format(
                namespace, name, maxReplicas
            ),
            time,
        )
        print(
            "[INFO]",
            datetime.datetime.now(),
            "HPA {}/{} has been adjusted to minReplicas to {} at".format(
                namespace, name, minReplicas
            ),
            time,
        )
    else:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "Something went wrong... HPA {}/{} has not been scaled(maxReplicas to {}, minReplicas to {})".format(
                namespace, name, maxReplicas, minReplicas
            ),
        )

elif minReplicas > 0:
    current_hpa = v1.read_namespaced_horizontal_pod_autoscaler(
        "name",
        "namespace"
    )
    currentMaxReplicas = current_hpa.spec.max_replicas

    if currentMaxReplicas:
        if currentMaxReplicas < minReplicas:
            print(
                "[ERROR]",
                datetime.datetime.now(),
                "HPA {}/{} cannot be set minReplicas(desired:{}) larger than maxReplicas(current:{}).".format(
                    namespace, name, minReplicas, currentMaxReplicas
                ),
            )
            sys.exit(1)

    body = {"spec": {"minReplicas": minReplicas}}

    patch_hpa(body)

    hpa = v1.read_namespaced_horizontal_pod_autoscaler(name, namespace)
    if hpa.spec.min_replicas == minReplicas:
        print(
            "[INFO]",
            datetime.datetime.now(),
            "HPA {}/{} has been adjusted to minReplicas to {} at".format(
                namespace, name, minReplicas
            ),
            %(time)s,
        )
    else:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "Something went wrong... HPA {}/{}s has not been scaled(minReplicas to {})".format(
                namespace, name, minReplicas
            ),
        )

elif maxReplicas > 0:
    current_hpa = v1.read_namespaced_horizontal_pod_autoscaler("%(name)s", "%(namespace)s")
    currentMinReplicas = current_hpa.spec.min_replicas

    if currentMinReplicas:
        if currentMinReplicas > maxReplicas:
            print(
                "[ERROR]",
                datetime.datetime.now(),
                "HPA {}/{} cannot be set maxReplicas(desired:{}) larger than minReplicas(current:{}).".format(
                    namespace, name, maxReplicas, currentMinReplicas
                ),
            )
            sys.exit(1)

    body = {"spec": {"maxReplicas": maxReplicas}}
    patch_hpa(body)

    hpa = v1.read_namespaced_horizontal_pod_autoscaler(name, namespace)
    if hpa.spec.max_replicas == maxReplicas:
        print(
            "[INFO]",
            datetime.datetime.now(),
            "HPA {}/{} has been adjusted to maxReplicas to {} at {}".format(
                namespace, name, maxReplicas, time
            ),
        )
    else:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "Something went wrong... HPA {}/{} has not been scaled(maxReplicas to {})".format(
                namespace, name, maxReplicas
            ),
        )
