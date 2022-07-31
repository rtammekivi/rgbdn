#!/bin/sh
ansible-playbook -i pie.lan, site.yml -e ansible_user=pi $@
