#!/usr/bin/python
# -*- coding: utf-8 -*-

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: cloud_resource
short_description: Create resource on ManageIQ
description:
  - Create resource that can hold vms.
  - Usable way is create resource after creating service.
version_added: "2.3"
options:
  service_template:
    description:
    - Service templat for cloud resource request.
    default: 'OpenStack Instance'
  url:
    description:
    - Cloud platform access point - manageiq server.
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
  resource_data:
    description:
    - Any data that can be passed to request. See http://manageiq.org/docs/reference/latest/api/examples/order_service
    type: dict
    required: True
'''

EXAMPLES = r'''
# Create some cloud resource:
- name: Create new Cloud Resource
  cloud_resource:
    url: "{{ cloud_url }}"
    user: "{{ cloud_user }}"
    password: "{{ cloud_password }}"
    workgroup: "{{ cloud_group }}"
    service_template: "{{ service_template }}"
    resource_data: "{{ item }}"
      service_template: 'OpenStack Instance'
      custom_role: windows
      src_ems_id: "{{ SPB }}"
      placement_availability_zone: "{{ default_az }}"
      src_vm_id: "{{ windows_server_2k12r2 }}"
      instance_type: "{{ t1_2medium }}"
      number_of_vms: 1
      service_guid: "{{ service.service_guid }}"
'''

RETURN = r'''
request:
    description: Request parameters. See http://manageiq.org/docs/reference/latest/api/examples/order_service
    returned: success
    type: dict
    sample: {}
'''
