import os
import time
from crontab import CronTab
from datetime import datetime
from datetime import timedelta

scaling_cron = CronTab(user="root")
print("[INFO]", datetime.now(), "Running the Jobs of the last 5 minutes")

for target in ["Deployment", "HPA"]:
    scale_jobs = scaling_cron.find_comment("Scheduling_Jobs_" + target)

    for job in scale_jobs:
        # print(job)
        schedule = job.schedule(date_from=datetime.now())
        schedule = str(schedule.get_prev())
        schedule = time.strptime(schedule, "%Y-%m-%d %H:%M:%S")
        retry_execution_threshold = str(datetime.now() - timedelta(minutes=5))
        retry_execution_threshold = time.strptime(
            retry_execution_threshold, "%Y-%m-%d %H:%M:%S.%f"
        )

        if schedule > retry_execution_threshold:
            # 5 7 * * * . /root/.profile ; /usr/bin/python /root/schedule_scaling/deployment-script.py --namespace ... --deployment ... --replicas 9 2>&1 | tee -a ... # Scheduling_Jobs
            schedule_to_execute = str(job).split(";")[1]
            os.system(schedule_to_execute)
