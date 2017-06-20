#!/usr/bin/python
# -*- coding: utf-8 -*-

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: cloud_service
short_description: Create Service on ManageIQ
description:
  - Create service that can hold vms. Service should be tagget by proper tags for user access.
  - If cloud resources created after this task tagging occured atomaticaly.
version_added: "2.3"
options:
  name:
    description:
    - Service name for new service.
    default: 'Ansible Created'
  state:
    description:
    - Service state. Can be present and service will be created and absent for service retirement.
    choices: [ "present", "absent"]
    default: 'present'
  url:
    description:
    - Cloud service access point - manageiq server.
    default: 'https://manageiq'
  user:
    description:
    - Cloud user name for cloud access.
    required: True
  password:
    description:
    - Cloud user password for cloud access.
    required: True
  workgroup:
    description:
    - Cloud user workgroup for cloud access. Needed because user can have many cloud pools.
    required: True
'''

EXAMPLES = r'''
# Create new service for vms and register service parameters.
cloud_service:
  name: "{{ service_name }}"
  state: present
  url: "{{ cloud_url }}"
  user: "{{ cloud_user }}"
  password: "{{ cloud_password }}"
  workgroup: "{{ cloud_group }}"
register: service

# Remove all services with name service_name
cloud_service:
  name: "{{ service_name }}"
  state: absent
  url: "{{ cloud_url }}"
  user: "{{ cloud_user }}"
  password: "{{ cloud_password }}"
  workgroup: "{{ cloud_group }}"

'''

RETURN = r'''
name:
    description: Created Service name
    returned: success
    type: string
    sample: 'Ansible Created'
guid:
    description: Created Service guid
    returned: success
    type: string
    sample: '36882f5c-5400-11e7-b09a-0050568e42e5'
results:
    description: Deleted Services list
    returned: success
    type: string
    sample: '[{},{},{}]'
'''
