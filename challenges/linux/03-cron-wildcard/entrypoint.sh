#!/bin/bash
service cron start
exec /usr/sbin/sshd -D -e
