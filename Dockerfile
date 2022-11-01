FROM ubuntu:22.04
MAINTAINER "sakamoto@chatwork.com"

# Install python tools and dev packages
RUN apt update -y \
    && apt upgrade -y \
    && apt upgrade -y openssl \
    && apt install -q -y --no-install-recommends  python3-pip python3-setuptools python3-wheel gcc cron tini \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

# set python 3 as the default python version
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

COPY ./requirements.txt /root/
RUN pip3 install --upgrade pip requests setuptools pipenv
RUN pip3 install -r /root/requirements.txt

ADD schedule_scaling /root/schedule_scaling
COPY ./run_missed_jobs.py /root
RUN chmod a+x /root/run_missed_jobs.py
COPY ./startup.sh /root
RUN chmod a+x /root/startup.sh
ENTRYPOINT ["tini",  "--", "/root/startup.sh"]
