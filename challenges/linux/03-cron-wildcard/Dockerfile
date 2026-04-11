FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openssh-server \
    cron \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN mkdir /var/run/sshd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
RUN echo 'UsePAM yes' >> /etc/ssh/sshd_config

# Create player user
RUN useradd -m -s /bin/bash player && echo 'player:player2026' | chpasswd

# Create world-writable uploads directory
RUN mkdir -p /tmp/uploads && chmod 1777 /tmp/uploads

# Create vulnerable cron job
RUN echo '* * * * * root cd /tmp/uploads && tar czf /tmp/backup.tgz * 2>/dev/null' > /etc/cron.d/backup \
    && chmod 644 /etc/cron.d/backup

# Create flag
RUN echo 'CTF{tar_wildcard_cron_injection}' > /root/flag.txt && chmod 400 /root/flag.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22

CMD ["/entrypoint.sh"]
