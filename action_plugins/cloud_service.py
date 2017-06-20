# (c) 2016, Tiunov Igor igortiunov@gmail.com
# CI-required python3 boilerplate
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import requests
import base64

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

    DEFAULT_CLOUD_URL = 'https://manageiq'
    DEFAULT_STATE = 'present'
    DEFAULT_SERVICE_NAME = 'Ansible Created'

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
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        result['warnings'] = []

        self.url = str(self._task.args.get('url', self.DEFAULT_CLOUD_URL))
        self.user = str(self._task.args.get('user', None))
        self.password = str(self._task.args.get('password', None))
        self.workgroup = str(self._task.args.get('workgroup', None))
        service_name = str(self._task.args.get('name', self.DEFAULT_SERVICE_NAME))
        state = str(self._task.args.get('state', self.DEFAULT_STATE))
        self.auth()

        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}

        # Get Services
        service_url = "{0}/api/services?filter[]=name='%s'&expand=resources&attributes=name,id,guid".format(self.url) % service_name
        services_output = self.return_json_object('get', service_url, headers)
        services = services_output['resources']

        service = [ item for item in services if item['name'] == service_name ]
        service_url = "{0}/api/services".format(self.url)

        if state == 'present':
            if len(service) == 0:
                if self._play_context.check_mode:
                    result['changed'] = True
                    result['warnings'].append('WARNING: name and guid of service does not registered because service is no created in check mode.')
                    return result

                # Create service
                service_url = "{0}/api/services".format(self.url)
                service_data = {'action': 'create',
                                'name': service_name,
                                'display': 'true'}
                service_output = self.return_json_object('post', service_url, headers, service_data)
                service = service_output['results']
                service = service[0]
                changed = True
            else:
                service = service[0]
                changed = False

            result['service_name'] = service['name']
            result['service_guid'] = service['guid']
        else:
            if len(service) == 0:
                changed = False
            else:
                if self._play_context.check_mode:
                    return dict(changed=True)

                service_url = "{0}/api/services".format(self.url)
                service_data = {'action': 'retire',
                                'resources': service}

                service_output = self.return_json_object('post', service_url, headers, service_data)

                changed = True
                result['results'] = service_output['results']

        result['changed'] = changed

        return result
