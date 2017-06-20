# manageiq-ansible
Ansible playbook example for ManageIQ cloud management platform

Example of describing infra by extra-vars:

```
---
cloud_url: 'https://manageiq'
cloud_user: igor.tiunov

cloud_group: 'devops'

service_name: 'My Environment'
service_template: 'OpenStack Instance'

cloud_resources:
  - service_template: "{{ service_template }}"
    custom_role: windows
    src_ems_id: "{{ SPB }}"
    placement_availability_zone: "{{ default_az }}"
    src_vm_id: "{{ windows_server_2k12r2 }}"
    instance_type: "{{ t1_2medium }}"
    number_of_vms: 2
    service_guid: "{{ service.service_guid }}"
  - service_template: "{{ service_template }}"
    custom_role: rabbitmq
    src_ems_id: "{{ SPB }}"
    placement_availability_zone: "{{ default_az }}"
    src_vm_id: "{{ rhel7 }}"
    instance_type: "{{ t1_2medium }}"
    number_of_vms: 4
    service_guid: "{{ service.service_guid }}"

```

Playbook with these settings will create 6 virtual instances. Cloud resources is the any parameters that can be passed to service order request (http://manageiq.org/docs/reference/latest/api/examples/order_service)
