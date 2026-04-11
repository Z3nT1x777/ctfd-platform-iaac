FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openssh-server \
    gcc \
    binutils \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN mkdir /var/run/sshd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
RUN echo 'UsePAM yes' >> /etc/ssh/sshd_config

# Create player user
RUN useradd -m -s /bin/bash player && echo 'player:player2026' | chpasswd

# Inline the vulnerable C source and compile the SUID binary
RUN printf '#include <stdlib.h>\n\
#include <unistd.h>\n\
#include <stdio.h>\n\
\n\
int main() {\n\
    setresuid(0, 0, 0);\n\
    setresgid(0, 0, 0);\n\
    printf("[*] Running system diagnostics...\\n");\n\
    system("sysinfo");\n\
    return 0;\n\
}\n' > /tmp/syscheck.c \
    && gcc -o /usr/local/bin/syscheck /tmp/syscheck.c \
    && chmod 4755 /usr/local/bin/syscheck \
    && chown root:root /usr/local/bin/syscheck \
    && rm /tmp/syscheck.c

# Remove gcc to avoid making it too easy (strings still available via binutils)
RUN apt-get remove -y gcc && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Create flag
RUN echo 'CTF{path_hijack_suid_custom_binary}' > /root/flag.txt && chmod 400 /root/flag.txt

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D", "-e"]
