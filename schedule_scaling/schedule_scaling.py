""" Collecting Deployments configured for Scaling """
import os
import json
import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import re
import urllib.request
from crontab import CronTab
import datetime
from socket import gethostname

deployment_script = os.getenv("CRON_SCRIPT_PATH_BASE") + "/deployment-script.py"
hpa_script = os.getenv("CRON_SCRIPT_PATH_BASE") + "/hpa-script.py"
schedule_actions_annotation = "zalando.org/schedule-actions"


def clear_cron(comment):
    """This is needed so that if any one removes his scaling action
    it should not be trigger again"""
    my_cron = CronTab(user="root")
    my_cron.remove_all(comment=comment)
    my_cron.write()


def deployments_for_scale():
    """
    Getting the deployments configured for schedule scaling...
    """
    v1 = client.AppsV1Api()
    scaling_dict = {}
    deployments = v1.list_deployment_for_all_namespaces(watch=False)

    for i in deployments.items:
        if schedule_actions_annotation in i.metadata.annotations:
            deployment = str(i.metadata.namespace + "/" + str(i.metadata.name))
            schedule_actions = parse_content(
                i.metadata.annotations[schedule_actions_annotation], deployment
            )
            scaling_dict[deployment] = schedule_actions

    if not scaling_dict:
        logging.info("No deployment is configured for schedule scaling")

    return scaling_dict


def hpa_for_scale():
    """
    Getting the hpa configured for schedule scaling...
    """

    v1 = client.AutoscalingV1Api()
    scaling_dict = {}

    hpas = v1.list_horizontal_pod_autoscaler_for_all_namespaces(watch=False)

    for i in hpas.items:
        if schedule_actions_annotation in i.metadata.annotations:
            hpa = str(i.metadata.namespace + "/" + str(i.metadata.name))
            schedule_actions = parse_content(
                i.metadata.annotations[schedule_actions_annotation], hpa
            )
            scaling_dict[hpa] = schedule_actions

    if not scaling_dict:
        logging.info("No hpa is configured for schedule scaling")

    return scaling_dict


def deployment_job_creator():
    """Create CronJobs for configured Deployments"""

    deployments__for_scale = deployments_for_scale()

    deployment_job_creator_file = "/tmp/deployment_job_creator.json"
    configmap_name = "kube-schedule-scaler-deployment-status"
    if os.path.isfile(deployment_job_creator_file):
        with open(deployment_job_creator_file, "r") as f:
            old_deployments__for_scale = json.load(f)
            if deployments__for_scale == old_deployments__for_scale:
                patch_configmap(configmap_name=configmap_name)

                return

    cron_comment = "Scheduling_Jobs_Deployment"
    clear_cron(cron_comment)
    for namespace_deployment, schedules in deployments__for_scale.items():
        namespace = namespace_deployment.split("/")[0]
        deployment = namespace_deployment.split("/")[1]
        for i, contents in enumerate(schedules):
            replicas = contents.get("replicas", None)
            if replicas is None:
                print(
                    "[ERROR]",
                    datetime.datetime.now(),
                    "{}, Deployment: {}, Namespace: {} is not set replicas".format(
                        i, deployment, namespace
                    ),
                )
                continue
            schedule = contents.get("schedule", None)
            # print(
            #    "[INFO]",
            #    datetime.datetime.now(),
            #    "{}, Deployment: {}, Namespace: {}, Replicas: {}, Schedule: {}".format(
            #        i, deployment, namespace, replicas, schedule
            #    ),
            # )
            cmd = [
                ". /root/.profile ; python3",
                deployment_script,
                "--namespace",
                namespace,
                "--deployment",
                deployment,
                "--replicas",
                replicas,
                "2>&1 | tee -a",
                os.environ["SCALING_LOG_FILE"],
            ]
            cmd = " ".join(map(str, cmd))
            # print(cmd)
            scaling_cron = CronTab(user="root")
            job = scaling_cron.new(command=cmd)
            try:
                job.set_comment(cron_comment)
                job.setall(schedule)
                scaling_cron.write()
            except Exception as err:
                print(
                    "[ERROR]",
                    datetime.datetime.now(),
                    "Deployment: {} has syntax error in the schedule".format(
                        deployment
                    ),
                    err,
                )
                pass

    with open(deployment_job_creator_file, "w") as f:
        json.dump(deployments__for_scale, f, indent=2)

    create_status_configmap(
        json.dumps(deployments__for_scale, indent=2), configmap_name
    )
    patch_configmap(
        configmap_name=configmap_name,
        configmap_data=json.dumps(deployments__for_scale, indent=2),
    )

    print("[INFO]", datetime.datetime.now(), "Deployment cronjob for scaling: ")
    my_cron = CronTab(user="root")
    for cron in my_cron.find_comment(comment=cron_comment):
        print("[INFO]", datetime.datetime.now(), cron)


def hpa_job_creator():
    """Create CronJobs for configured hpa"""

    hpa__for_scale = hpa_for_scale()
    # print("[INFO]", datetime.datetime.now(), "HPA collected for scaling: ")

    hpa_job_creator_file = "/tmp/hpa_job_creator.json"
    configmap_name = "kube-schedule-scaler-hpa-status"
    if os.path.isfile(hpa_job_creator_file):
        with open(hpa_job_creator_file, "r") as f:
            old_hpa__for_scale = json.load(f)
            if hpa__for_scale == old_hpa__for_scale:
                patch_configmap(configmap_name=configmap_name)

                return

    cron_comment = "Scheduling_Jobs_HPA"
    clear_cron(cron_comment)
    for namespace_hpa, schedules in hpa__for_scale.items():
        namespace = namespace_hpa.split("/")[0]
        hpa = namespace_hpa.split("/")[1]
        for i, contents in enumerate(schedules):
            minReplicas = contents.get("minReplicas", None)
            maxReplicas = contents.get("maxReplicas", None)

            if maxReplicas == 0 or maxReplicas == "0":
                print(
                    "[ERROR]",
                    datetime.datetime.now(),
                    "HPA: {}, Namespace: {},  MaxReplicas: {} is not set to 0".format(
                        hpa, namespace, maxReplicas
                    ),
                )
                continue

            if minReplicas == 0 or minReplicas == "0":
                print(
                    "[ERROR]",
                    datetime.datetime.now(),
                    "HPA: {}, Namespace: {}, MinReplicas: {} is not set to 0".format(
                        hpa, namespace, minReplicas
                    ),
                )
                continue

            schedule = contents.get("schedule", None)
            # print(
            #    "[INFO]",
            #    datetime.datetime.now(),
            #    "{}, HPA: {}, Namespace: {}, MinReplicas: {}, MaxReplicas: {}, Schedule: {}".format(
            #        i, hpa, namespace, minReplicas, maxReplicas, schedule
            #    ),
            # )

            if minReplicas is not None and maxReplicas is not None:
                cmd = [
                    ". /root/.profile ; python3",
                    hpa_script,
                    "--namespace",
                    namespace,
                    "--hpa",
                    hpa,
                    "--min_replicas",
                    minReplicas,
                    "--max_replicas",
                    maxReplicas,
                    "2>&1 | tee -a",
                    os.environ["SCALING_LOG_FILE"],
                ]

            elif minReplicas is not None:
                cmd = [
                    ". /root/.profile ; python3",
                    hpa_script,
                    "--namespace",
                    namespace,
                    "--hpa",
                    hpa,
                    "--min_replicas",
                    minReplicas,
                    "2>&1 | tee -a",
                    os.environ["SCALING_LOG_FILE"],
                ]

            elif maxReplicas is not None:
                cmd = [
                    ". /root/.profile ; python3",
                    hpa_script,
                    "--namespace",
                    namespace,
                    "--hpa",
                    hpa,
                    "--max_replicas",
                    maxReplicas,
                    "2>&1 | tee -a",
                    os.environ["SCALING_LOG_FILE"],
                ]

            cmd = " ".join(map(str, cmd))
            # print(cmd)
            scaling_cron = CronTab(user="root")
            job = scaling_cron.new(command=cmd)
            try:
                job.set_comment(cron_comment)
                job.setall(schedule)
                scaling_cron.write()
            except Exception as err:
                print(
                    "[ERROR]",
                    datetime.datetime.now(),
                    "HPA: {} has syntax error in the schedule".format(hpa),
                    err,
                )
                pass

    with open(hpa_job_creator_file, "w") as f:
        json.dump(hpa__for_scale, f, indent=2)

    create_status_configmap(json.dumps(hpa__for_scale, indent=2), configmap_name)
    patch_configmap(
        configmap_name=configmap_name,
        configmap_data=json.dumps(hpa__for_scale, indent=2),
    )

    print("[INFO]", datetime.datetime.now(), "HPA cronjob for scaling: ")
    my_cron = CronTab(user="root")
    for cron in my_cron.find_comment(comment=cron_comment):
        print("[INFO]", datetime.datetime.now(), cron)


def parse_content(content, identifier):
    if content is None:
        return []

    if is_valid_url(content):
        schedules = fetch_schedule_actions_from_url(content)

        if schedules is None:
            return []

        return parse_schedules(schedules, identifier)

    return parse_schedules(content, identifier)


def is_valid_url(url):
    return re.search("^(https?)://(\\S+)\.(\\S{2,}?)(/\\S+)?$", url, re.I) != None


def fetch_schedule_actions_from_url(url):
    request = urllib.request.urlopen(url)
    try:
        content = request.read().decode("utf-8")
    except:
        content = None
    finally:
        request.close()

    return content


def parse_schedules(schedules, identifier):
    try:
        return json.loads(schedules)
    except Exception as err:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "{} - Error in parsing JSON {} with error".format(identifier, schedules),
            err,
        )
        return []


def _create_configmap_object(name, namespace, configmap_data):
    # Configureate ConfigMap metadata
    metadata = client.V1ObjectMeta(
        name=name,
        namespace=namespace,
    )
    configmap_object = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        data=dict(schedules=configmap_data),
        metadata=metadata,
    )
    return configmap_object


def create_status_configmap(configmap_data, configmap_name):
    v1 = client.CoreV1Api()

    if os.getenv("NAMESPACE"):
        namespace = os.getenv("NAMESPACE")
    else:
        namespace = "kube-system"

    configmap_names = []
    for configmap in v1.list_namespaced_config_map(namespace, watch=False).items:
        configmap_names.append(configmap.metadata.name)

    if configmap_name not in configmap_names:
        configmap_object = _create_configmap_object(
            configmap_name, namespace, configmap_data
        )
        try:
            v1.create_namespaced_config_map(
                namespace=namespace,
                body=configmap_object,
            )

        except ApiException as e:
            print(
                "[ERROR]",
                datetime.datetime.now(),
                "{} has not created.".format(configmap_name),
            )


def patch_configmap(configmap_name, configmap_data=None):
    v1 = client.CoreV1Api()

    if configmap_data is None:
        body = {
            "metadata": {
                "annotations": {
                    "kube-schedule-scaler/last-updated": datetime.datetime.now(),
                    "kube-schedule-scaler/checked-by": gethostname(),
                }
            }
        }

    else:
        body = {
            "metadata": {
                "annotations": {
                    "kube-schedule-scaler/last-updated": datetime.datetime.now(),
                    "kube-schedule-scaler/checked-by": gethostname(),
                }
            },
            "data": {
                "schedules": configmap_data,
            },
        }

    if os.getenv("NAMESPACE"):
        namespace = os.getenv("NAMESPACE")
    else:
        namespace = "kube-system"

    try:
        v1.patch_namespaced_config_map(configmap_name, namespace, body)
    except ApiException as err:
        print(
            "[ERROR]",
            datetime.datetime.now(),
            "{} has not patched.".format(configmap_name),
            err,
        )


def main():
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        config.load_incluster_config()
    else:
        config.load_kube_config()

    deployment_job_creator()
    hpa_job_creator()


if __name__ == "__main__":
    main()
