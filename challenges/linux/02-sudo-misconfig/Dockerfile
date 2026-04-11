FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openssh-server \
    vim \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN mkdir /var/run/sshd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
RUN echo 'UsePAM yes' >> /etc/ssh/sshd_config

# Create player user
RUN useradd -m -s /bin/bash player && echo 'player:player2026' | chpasswd

# Configure sudo misconfiguration
RUN echo 'player ALL=(ALL) NOPASSWD: /usr/bin/vim' > /etc/sudoers.d/player \
    && chmod 440 /etc/sudoers.d/player

# Create flag
RUN echo 'CTF{sudo_vim_shell_escape}' > /root/flag.txt && chmod 400 /root/flag.txt

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D", "-e"]
