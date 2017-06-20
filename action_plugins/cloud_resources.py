# (c) 2016, Tiunov Igor igortiunov@gmail.com
# CI-required python3 boilerplate
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import requests
import base64
import time

from dateutil.parser import parse
from datetime import datetime
import pytz

from ansible.plugins.action import ActionBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

# Disable requests.* SSL warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    VERIFY_SSL = False

    if not VERIFY_SSL:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    REQUEST_TIMEOUT = 30  # Minutes

    DEFAULT_CLOUD_URL = 'https://manageiq'
    DEFAULT_SERVICE_TEMPLATE = 'OpenStack Instance'
    DEFAULT_RESOURCE_DATA = {}

    url = DEFAULT_CLOUD_URL
    user = ''
    password = ''
    workgroup = ''
    auth_data = {'auth_token': '',
                 'expires_on': "%s" % datetime.utcnow().replace(tzinfo=pytz.utc)}

    def auth(self):
        expires_on = parse(self.auth_data['expires_on']).astimezone(
            pytz.timezone('UTC')).replace(tzinfo=None)
        delta = datetime.utcnow() - expires_on

        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'X-Auth-Token': self.auth_data['auth_token'],
                   'X-MIQ-Group': self.workgroup}
        api_url = "{0}/api".format(self.url)
        response = requests.get(
            api_url, headers=headers, verify=self.VERIFY_SSL)

        if response.status_code == 401 or (delta.days < 1 and delta.seconds < 10):
            # Authentication
            auth_url = "{0}/api/auth".format(self.url)
            auth_data = base64.b64encode("%s:%s" % (self.user, self.password))
            headers = {'Authorization': "Basic %s" % auth_data,
                       'Accept': 'application/json',
                       'Content-Type': 'application/json',
                       'X-MIQ-Group': self.workgroup}
            response = requests.get(
                auth_url, headers=headers, verify=self.VERIFY_SSL)

            if not response.status_code // 100 == 2:
                if response.status_code == 404:
                    raise Exception('Please, check request parameters')
                elif response.status_code == 401:
                    display.vvv("Response status code: %d" %
                                response.status_code)
                    display.vvv("Response error: %s" %
                                response.json()['error'])
                    raise Exception('Unauthorized')
            else:
                self.auth_data = response.json()

    # Send requests to CFME API
    def return_json_object(self, method, url, headers={}, data={}):
        self.auth()
        headers['X-Auth-Token'] = self.auth_data['auth_token']
        headers['X-MIQ-Group'] = self.workgroup
        try:
            if method == 'post':
                response = requests.post(
                    url, headers=headers, data=json.dumps(data), verify=self.VERIFY_SSL)

            if method == 'get':
                response = requests.get(
                    url, headers=headers, verify=self.VERIFY_SSL)

        except requests.exceptions.RequestException as e:
            raise Exception("Error: {0}".format(e))

        # if status code not in 200-299 range
        if not response.status_code // 100 == 2:
            raise Exception('Please, check request parameters')
        else:
            return response.json()

    def run(self, tmp=None, task_vars=None):
        self._supports_check_mode = True
        self._supports_async = True

        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        result['warnings'] = []

        self.url = str(self._task.args.get('url', self.DEFAULT_CLOUD_URL))
        self.user = str(self._task.args.get('user', None))
        self.password = str(self._task.args.get('password', None))
        self.workgroup = str(self._task.args.get('workgroup', None))

        resources_data = list(self._task.args.get(
            'resources_data', self.DEFAULT_RESOURCE_DATA))

        timeout = int(self._task.args.get('timeout', self.REQUEST_TIMEOUT))

        self.auth()

        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}

        # TODO: Need to implement idempotency
        # Order Service
        if self._play_context.check_mode:
            display.vvv("cloud_service: skipping for check_mode")
            return dict(skipped=True, changed=True)

        result['requests'] = []
        requests = []
        for resource_data in resources_data:

            service_template_name = str(resource_data.get(
                'service_template', self.DEFAULT_SERVICE_TEMPLATE))

            del resource_data['service_template']
            # Service Catalogs
            service_catalogs_url = "{0}/api/service_catalogs?expand=resources&attributes=name,id".format(
                self.url)
            service_catalogs_data = self.return_json_object(
                'get', service_catalogs_url, headers)
            service_catalogs = service_catalogs_data['resources']

            for service_catalog in service_catalogs:
                service_templates = service_catalog[
                    'service_templates']['resources']
                for service_template in service_templates:
                    service_template_data = self.return_json_object(
                        'get', "%s?expand=resources&attributes=name,id" % service_template['href'], headers)
                    if service_template_data['name'] == service_template_name:
                        service_template_id = service_template_data['id']
                        service_catalog_id = service_catalog['id']

            # There is custom check of idempotency
            if resource_data['service_guid'] and resource_data['custom_role']:
                limit = 5
                page = 0
                last_page = False

                vms = []

                while not last_page:
                    offset = page * limit
                    ret = self.return_json_object('get', "%s/api/vms?offset=%s&limit=%s&expand=resources&attributes=id,name,custom_attributes,direct_service&filter[]=direct_service.guid=%s" % (
                        self.url, offset, limit, resource_data['service_guid']), headers)
                    vms += ret['resources']
                    if ret['subcount'] < limit:
                        last_page = True
                    page += 1

                ids = []
                number_of_vms = 0
                for vm in vms:
                    custom_attributes = vm['custom_attributes']
                    roles = [item for item in custom_attributes if item[
                        'name'] == 'role']
                    for role in roles:
                        if role['value'] == resource_data['custom_role'] and vm.get('retirement_state', 'notnow') != 'retiring':
                            number_of_vms += 1
                            ids.append(vm['id'])

            resource_data['number_of_vms'] = resource_data.get('number_of_vms', 0) - number_of_vms

            request_data = {}
            request_data['action'] = 'order'
            request_data['resource'] = resource_data
            request_data['resource']['href'] = "{0}/api/service_templates/%d".format(self.url) % service_template_id

            if resource_data['number_of_vms'] > 0:
                requests.append(self.return_json_object(
                    'post', "{0}/api/service_catalogs/%d/service_templates".format(self.url) % service_catalog_id, headers, request_data))
            else:
                for index in range(resource_data['number_of_vms'], 0):
                    result['requests'].append(self.return_json_object(
                        'post', "{0}/api/vms/%d".format(self.url) % ids[index], headers, {"action": "retire"}))
                    changed = True

        if requests:
            # Set timeout to 30 minutes
            wait_count = timeout * 2
            wait = 0
            overal_status = 'Ok'
            status = 'active'

            while status != 'finished' and wait < wait_count:
                display.vvv("cloud_resources: wait untill request is finished")
                time.sleep(30)
                wait += 1
                status = 'finished'

                for request in requests:
                    request_url = "{0}/api/requests/%s".format(
                        self.url) % request['results'][0]['id']
                    request_status = {}
                    request_status = self.return_json_object(
                        'get', request_url, headers)
                    display.vvv(request_status['message'])
                    if request_status['request_state'] != 'finished':
                        status = 'active'
                    else:
                        if request_status['status'] != 'Ok':
                            overal_status = request_status['message']

                        result['requests'].append(request_status)

            changed = True
            # Check request status
            if overal_status != 'Ok' or status != 'finished':
                result['failed'] = True
                result['warnings'].append(
                    "WARNING: Failed to provision cloud resources. %s" % overal_status)
                result[
                    'msg'] = "Failed to provision cloud resources. %s" % overal_status

        else:
            if not result['requests']:
                changed = False

        result['vms'] = []
        for resource_data in resources_data:
            if resource_data['service_guid']:
                limit = 5
                page = 0
                last_page = False

                while not last_page:
                    offset = page * limit
                    ret = self.return_json_object('get', "%s/api/vms?offset=%s&limit=%s&expand=resources&attributes=id,name,custom_attributes,ipaddresses,platform,os_image_name,retirement_state,direct_service&filter[]=direct_service.guid=%s" % (
                        self.url, offset, limit, resource_data['service_guid']), headers)
                    result['vms'] += ret['resources']
                    if ret['subcount'] < limit:
                        last_page = True
                    page += 1

        result['changed'] = changed

        return result
