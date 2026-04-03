# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Ubuntu 22.04 LTS
  config.vm.box = "ubuntu/jammy64"
  config.vm.hostname = "ctf-platform"

  # Network: static IP for access from Windows host
  config.vm.network "private_network", ip: "192.168.56.10"
  # Port forwarding (backup if private_network fails)
  config.vm.network "forwarded_port", guest: 80, host: 8000   # CTFd
  config.vm.network "forwarded_port", guest: 8080, host: 8080 # GitLab
  config.vm.network "forwarded_port", guest: 3000, host: 3000 # Grafana

  # VM Resources
  config.vm.provider "virtualbox" do |vb|
    vb.name = "ctf-platform-vm"
    vb.memory = "8192"  # 8 GB RAM
    vb.cpus = 4
    vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"] # enable host DNS resolver
  end

  # Shared folder
  config.vm.synced_folder ".", "/vagrant", type: "virtualbox"

  # Initial provisioning (base installation)
  config.vm.provision "shell", inline: <<-SHELL
    export DEBIAN_FRONTEND=noninteractive

    # Update system
    apt-get update
    apt-get upgrade -y

    # Install basic tools
    apt-get install -y git curl wget vim net-tools

    # Install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker vagrant

    # Install Docker Compose plugin
    apt-get install -y docker-compose-plugin

    # Install a modern Ansible runtime and required collections
    apt-get install -y python3-pip
    python3 -m pip install --upgrade pip ansible
    ansible-galaxy collection install community.docker

    echo "✅ Initial provisioning done!"
    echo "🚀 Base provisioning done"
  SHELL

  # Run Ansible from a non-shared directory to avoid Vagrant/Ansible edge cases
  config.vm.provision "shell", privileged: true, inline: <<-SHELL
    set -e

    rm -rf /root/ctf-ansible
    mkdir -p /root/ctf-ansible
    cp -a /vagrant/ansible/. /root/ctf-ansible/
    chmod -R go-w /root/ctf-ansible

    cd /root/ctf-ansible
    ansible-playbook -i inventory playbooks/main.yml
  SHELL
end
