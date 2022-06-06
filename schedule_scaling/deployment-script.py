from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time
import datetime
import random
import os
import sys
import argparse


def patch_deployment(client, deployment, namespace, replicas):
    body = {"spec": {"replicas": replicas}}

    try:
        client.patch_namespaced_deployment(deployment, namespace, body)
    except ApiException as err:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "deployment {}/{} has not been patched".format(namespace, deployment),
            err,
        )
        return
    except Exception as err:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "Exception! Something went wrong... HPA {}/{} has not been scaled with body: {}".format(
                namespace,
                deployment,
                body,
                err,
            ),
        )
        return

    print(
        "[INFO]",
        datetime.datetime.now(),
        "Deployment {}/{} has been updated to {}".format(namespace, deployment, body),
    )


def main():
    parser = argparse.ArgumentParser(description="deployment scaling replicas")
    parser.add_argument(
        "--namespace", "-n", type=str, required=True, help="deployment namespace"
    )
    parser.add_argument(
        "--deployment", "--deploy", type=str, required=True, help="deployment name"
    )
    parser.add_argument(
        "--replicas", type=int, required=True, help="replicas number", default=-1
    )
    args = parser.parse_args()

    time.sleep(random.uniform(1, 10))

    if os.getenv("KUBERNETES_SERVICE_HOST"):
        config.load_incluster_config()
    else:
        config.load_kube_config()

    v1 = client.AppsV1Api()

    patch_deployment(
        client=v1,
        deployment=args.deployment,
        namespace=args.namespace,
        replicas=args.replicas,
    )


if __name__ == "__main__":
    main()
