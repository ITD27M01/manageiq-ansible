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

    REQUEST_TIMEOUT = 30 # Minutes

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
        expires_on = parse(self.auth_data['expires_on']).astimezone(pytz.timezone('UTC')).replace(tzinfo=None)
        delta = datetime.utcnow() - expires_on

        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'X-Auth-Token': self.auth_data['auth_token'],
                   'X-MIQ-Group': self.workgroup}
        api_url = "{0}/api".format(self.url)
        response = requests.get(api_url, headers=headers, verify=self.VERIFY_SSL)

        if response.status_code == 401 or (delta.days < 1 and delta.seconds < 10):
            # Authentication
            auth_url = "{0}/api/auth".format(self.url)
            auth_data = base64.b64encode("%s:%s" % (self.user, self.password))
            headers = {'Authorization': "Basic %s" % auth_data,
                       'Accept': 'application/json',
                       'Content-Type': 'application/json',
                       'X-MIQ-Group': self.workgroup}
            response = requests.get(auth_url, headers=headers, verify=self.VERIFY_SSL)

            if not response.status_code // 100 == 2:
                    if response.status_code == 404:
                        raise Exception('Please, check request parameters')
                    elif response.status_code == 401:
                        display.vvv("Response status code: %d" % response.status_code)
                        display.vvv("Response error: %s" % response.json()['error'])
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
                response = requests.post(url, headers=headers, data=json.dumps(data), verify=self.VERIFY_SSL)

            if method == 'get':
                response = requests.get(url, headers=headers, verify=self.VERIFY_SSL)

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
        service_template_name = str(self._task.args.get('service_template', self.DEFAULT_SERVICE_TEMPLATE))

        resource_data = dict(self._task.args.get('resource_data', self.DEFAULT_RESOURCE_DATA))
        display.vvv(json.dumps(resource_data))
        timeout = int(self._task.args.get('timeout', self.REQUEST_TIMEOUT))

        self.auth()

        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}

        # Service Catalogs
        service_catalogs_url = "{0}/api/service_catalogs?expand=resources&attributes=name,id".format(self.url)
        service_catalogs_data = self.return_json_object('get', service_catalogs_url, headers)
        service_catalogs = service_catalogs_data['resources']

        for service_catalog in service_catalogs:
                service_templates = service_catalog['service_templates']['resources']
                for service_template in service_templates:
                    service_template_data = self.return_json_object('get', "%s?expand=resources&attributes=name,id" % service_template['href'], headers)
                    if service_template_data['name'] == service_template_name:
                        service_template_id = service_template_data['id']
                        service_catalog_id = service_catalog['id']

        # Order Service
        if self._play_context.check_mode:
            display.vvv("cloud_service: skipping for check_mode")
            return dict(skipped=True, changed=True)

        try:
            request_data = {}
            request_data['action'] = 'order'
            request_data['resource'] = {}
            request_data['resource'] = resource_data
            request_data['resource']['href'] = "{0}/api/service_templates/%d".format(self.url) % service_template_id
            display.vvv(json.dumps(request_data))
            request = self.return_json_object('post', "{0}/api/service_catalogs/%d/service_templates".format(self.url) % service_catalog_id, headers, request_data)
        except:
            raise Exception('Please, check request parameters')

        request['result'] = request['results'][0]
        request_url = "{0}/api/requests/%s".format(self.url) % request['result']['id']

        # Set timeout to 30 minutes
        wait_count = timeout * 2
        wait = 0
        while request['result']['request_state'] != 'finished' and wait < wait_count:
            display.vvv("cloud_resource: wait untill request finished")
            time.sleep(30)
            request = {}
            request['result'] = self.return_json_object('get', request_url, headers)
            wait += 1

        # Check request status
        if request['result']['status'] != 'Ok':
            result['failed'] = True
            result['warnings'].append('WARNING: Failed to provision cloud resources.')
            result['msg'] = 'Failed to provision cloud resources.'

        result['request'] = request['result']
        result['changed'] = True

        return result