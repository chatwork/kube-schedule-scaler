#!/bin/bash

LOG_DIR=/var/log/kubernetes/scaling

if [ ! -e ${LOG_DIR} ]; then
  mkdir -p ${LOG_DIR}
fi

export SCALING_LOG_FILE=${LOG_DIR}/scaling.log

if [ ! -e ${SCALING_LOG_FILE} ]; then
  touch ${SCALING_LOG_FILE}
fi

# Starting Cron
export CRON_SCRIPT_PATH_BASE="/root/schedule_scaling"

/usr/sbin/cron -f &

cron_pid=$!
status=$?
if [ $status -ne 0 ]; then
  echo "[ERROR] $datetime Failed to start Cron daemon: $status"
  exit $status
fi

datetime=`date "+%Y-%m-%d %H:%M:%S.%6N"`
echo "[INFO] $datetime cron_pid: $cron_pid"

# Exporting Env variables
env >> /etc/environment
status=$?
datetime=`date "+%Y-%m-%d %H:%M:%S.%6N"`
if [ $status -ne 0 ]; then
  echo "[ERROR] $datetime Failed to export env variables: $status"
  exit $status
fi

# Creating the main cron
datetime=`date "+%Y-%m-%d %H:%M:%S.%6N"`
echo "[INFO] $datetime Creating the main cron"
echo "
## The main script to collect the deployments to be scaled ##
*/3 * * * * sleep 7; . /root/.profile; python3 /root/schedule_scaling/schedule_scaling.py >> ${SCALING_LOG_FILE} 2>&1
" | /usr/bin/crontab -

# Running the main Script at the beginning
datetime=`date "+%Y-%m-%d %H:%M:%S.%6N"`
echo "[INFO] $datetime Running the main script at the beginning"
python3 /root/schedule_scaling/schedule_scaling.py

#echo "[INFO] $datetime confirm cronjob for the begging"
#crontab -l

# Run once at the startup of container
datetime=`date "+%Y-%m-%d %H:%M:%S.%6N"`
echo "[INFO] $datetime Run once at the startup of container"
sleep 2; python3 /root/run_missed_jobs.py >> ${SCALING_LOG_FILE} 2>&1

trap 'jobs -p | xargs kill; sleep 10; echo === Finish this script ===; exit 0' SIGTERM

# Getting the Scaling Activities
tail -f ${SCALING_LOG_FILE}
