from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time
import datetime
import sys
import random
import os
import argparse


def _patch_hpa(client, hpa, namespace, body):
    try:
        client.patch_namespaced_horizontal_pod_autoscaler(hpa, namespace, body)

    except ApiException as err:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "ApiException! HPA {}/{} has not been updated with body: {}. err: {}".format(
                namespace, hpa, body, err
            ),
        )
        return
    except Exception as err:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "Exception! Something went wrong... HPA {}/{} has not been scaled with body: {}".format(
                namespace,
                hpa,
                body,
                err,
            ),
        )
        return

    print(
        "[INFO]",
        datetime.datetime.now(),
        "HPA {}/{} has been updated to {}".format(namespace, hpa, body),
    )


def patch_hpa(client, hpa, namespace, max_replicas, min_replicas):
    body = ""
    if max_replicas > 0 and min_replicas > 0:
        body = {"spec": {"minReplicas": min_replicas, "maxReplicas": max_replicas}}

    elif min_replicas > 0:
        body = {"spec": {"minReplicas": min_replicas}}

    elif max_replicas > 0:
        body = {"spec": {"maxReplicas": max_replicas}}

    _patch_hpa(client, hpa, namespace, body)


def main():
    parser = argparse.ArgumentParser(description="deployment scaling replicas")
    parser.add_argument(
        "--namespace", "-n", type=str, required=True, help="hpa namespace"
    )
    parser.add_argument("--hpa", type=str, required=True, help="hpa name")
    parser.add_argument(
        "--min_replicas", type=int, help="minReplicas number", default=-1
    )
    parser.add_argument(
        "--max_replicas", type=int, help="maxReplicas number", default=-1
    )
    args = parser.parse_args()

    # jitter
    time.sleep(random.uniform(1, 10))

    if os.getenv("KUBERNETES_SERVICE_HOST"):
        config.load_incluster_config()
    else:
        config.load_kube_config()

    v1 = client.AutoscalingV1Api()

    patch_hpa(
        client=v1,
        hpa=args.hpa,
        namespace=args.namespace,
        max_replicas=args.max_replicas,
        min_replicas=args.min_replicas,
    )


if __name__ == "__main__":
    main()
