#!/usr/bin/python
# -*- coding: utf-8 -*-

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: cloud_resources
short_description: Create resources on ManageIQ
description:
  - Create resources that can hold vms.
  - Usable way is create resource after creating service.
version_added: "2.3"
options:
  service_template:
    description:
    - Service templat for cloud resources request.
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
    type: list
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
      - service_template: 'OpenStack Instance'
        custom_role: windows
        src_ems_id: "{{ SPB }}"
        placement_availability_zone: "{{ default_az }}"
        src_vm_id: "{{ windows_server_2k12r2 }}"
        instance_type: "{{ t1_2medium }}"
        number_of_vms: 1
        service_guid: "{{ service.service_guid }}"
      - service_template: 'OpenStack Instance'
        custom_role: rabbitmq
        src_ems_id: "{{ SPB }}"
        placement_availability_zone: "{{ default_az }}"
        src_vm_id: "{{ rhel7 }}"
        instance_type: "{{ t1_2medium }}"
        number_of_vms: 1
        service_guid: "{{ service.service_guid }}"
'''

RETURN = r'''
requests:
    description: Request parameters. See http://manageiq.org/docs/reference/latest/api/examples/order_service
    returned: success
    type: list
    sample: []
vms:
    description: VMs provisioned during cloud resource creations. This list can be used for dinamyc inventory in next tasks.
    returned: success
    type: list
    sample: []
'''
