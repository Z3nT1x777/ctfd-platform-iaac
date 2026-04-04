FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server curl python3 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash ctf \
    && echo 'ctf:ctf' | chpasswd \
    && mkdir -p /var/run/sshd

RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config \
    && printf '\nBanner /etc/issue.net\n' >> /etc/ssh/sshd_config

COPY flag.txt /home/ctf/flag.txt
RUN chown ctf:ctf /home/ctf/flag.txt && chmod 400 /home/ctf/flag.txt

COPY app.py /opt/ctf/app.py
COPY requirements.txt /opt/ctf/requirements.txt

RUN printf 'SSH Lab ready\n' > /etc/issue.net

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-e"]
