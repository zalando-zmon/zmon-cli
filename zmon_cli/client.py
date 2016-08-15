import ast
import logging
import json
import functools
import re

from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit, SplitResult

import requests

from zmon_cli import __version__


API_VERSION = 'v1'

ZMON_USER_AGENT = 'zmon-client/{}'.format(__version__)

ALERT_DATA = 'status/alert'
ALERT_DEF = 'alert-definitions'
CHECK_DEF = 'check-definitions'
DASHBOARD = 'dashboard'
DOWNTIME = 'downtimes'
ENTITIES = 'entities'
GRAFANA = 'grafana2-dashboards'
GROUPS = 'groups'
MEMBER = 'member'
PHONE = 'phone'
STATUS = 'status'
TOKENS = 'onetime-tokens'

CHECK_DEF_VIEW_URL = '#/check-definitions/view/'
ALERT_DETAILS_VIEW_URL = '#/alert-details/'
DASHBOARD_VIEW_URL = '#/dashboards/views/'
TOKEN_LOGIN_URL = 'tv/'
GRAFANA_DASHBOARD_URL = 'grafana/dashboard/db/'

logger = logging.getLogger(__name__)

parentheses_re = re.compile('[(]+|[)]+')
invalid_entity_id_re = re.compile('[^a-zA-Z0-9-@_.\[\]\:]+')


class JSONDateEncoder(json.JSONEncoder):
    def default(self, obj):
        return obj.isoformat() if isinstance(obj, datetime) else super().default(obj)


class ZmonError(Exception):
    def __init__(self, message=''):
        super().__init__('ZMON client error: {}'.format(message))


class ZmonArgumentError(ZmonError):
    pass


def logged(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            logger.error('ZMON client failed in: {}'.format(f.__name__))
            raise

    return wrapper


def compare_entities(e1, e2):
    try:
        e1_copy = e1.copy()
        e1_copy.pop('last_modified', None)

        e2_copy = e2.copy()
        e2_copy.pop('last_modified', None)

        return (json.loads(json.dumps(e1_copy, cls=JSONDateEncoder)) ==
                json.loads(json.dumps(e2_copy, cls=JSONDateEncoder)))
    except:
        # We failed during json serialiazation/deserialization, fallback to *not-equal*!
        logger.exception('Failed in `compare_entities`')
        return False


def get_valid_entity_id(e):
    return invalid_entity_id_re.sub('-', parentheses_re.sub(lambda m: '[' if '(' in m.group() else ']', e.lower()))


class Zmon:

    def __init__(
            self, url, token=None, username=None, password=None, timeout=10, verify=True, user_agent=ZMON_USER_AGENT):
        self.timeout = timeout

        split = urlsplit(url)
        self.base_url = urlunsplit(SplitResult(split.scheme, split.netloc, '', '', ''))
        self.url = urljoin(self.base_url, self._join_path(['api', API_VERSION, '']))

        self._session = requests.Session()

        self._session.timeout = timeout
        self.user_agent = user_agent

        if username and password and token is None:
            self._session.auth = (username, password)

        self._session.headers.update({'User-Agent': user_agent, 'Content-Type': 'application/json'})

        if token:
            self._session.headers.update({'Authorization': 'Bearer {}'.format(token)})

        if not verify:
            logger.warning('ZMON client will skip SSL verification!')
            requests.packages.urllib3.disable_warnings()
            self._session.verify = False

    @property
    def session(self):
        return self._session

    @staticmethod
    def is_valid_entity_id(entity_id):
        return invalid_entity_id_re.search(entity_id) is None

    @staticmethod
    def validate_check_command(src):
        try:
            ast.parse(src)
        except Exception as e:
            raise ZmonError('Invalid check command: {}'.format(e))

    def _join_path(self, parts):
        return '/'.join(str(p).strip('/') for p in parts)

    def endpoint(self, *args, trailing_slash=True, base_url=None):
        parts = list(args)

        # Ensure trailing slash!
        if trailing_slash:
            parts.append('')

        url = self.url if not base_url else base_url

        return urljoin(url, self._join_path(parts))

    def json(self, resp):
        resp.raise_for_status()
        return resp.json()

########################################################################################################################
# DEEPLINKS
########################################################################################################################

    def check_definition_url(self, check_definition):
        return self.endpoint(CHECK_DEF_VIEW_URL, check_definition['id'], base_url=self.base_url)

    def alert_details_url(self, alert):
        return self.endpoint(ALERT_DETAILS_VIEW_URL, alert['id'], base_url=self.base_url)

    def dashboard_url(self, dashboard_id):
        return self.endpoint(DASHBOARD_VIEW_URL, dashboard_id, base_url=self.base_url)

    def token_login_url(self, token):
        return self.endpoint(TOKEN_LOGIN_URL, token, base_url=self.base_url)

    def grafana_dashboard_url(self, dashboard):
        return self.endpoint(GRAFANA_DASHBOARD_URL, dashboard['id'], base_url=self.base_url)

    @logged
    def status(self):
        resp = self.session.get(self.endpoint(STATUS))

        return self.json(resp)

########################################################################################################################
# ENTITIES
########################################################################################################################

    @logged
    def get_entities(self, query=None):
        query_str = json.dumps(query) if query else ''
        logger.debug('Retrieving entities with query: {} ...'.format(query_str))

        params = {'query': query_str} if query else None

        resp = self.session.get(self.endpoint(ENTITIES), params=params)

        return self.json(resp)

    @logged
    def get_entity(self, entity_id):
        logger.debug('Retrieving entities with id: {} ...'.format(entity_id))

        resp = self.session.get(self.endpoint(ENTITIES, entity_id, trailing_slash=False))
        return self.json(resp)

    @logged
    def add_entity(self, entity):
        """
        Create or update entity on ZMON.

        ZMON PUT entity API doesn't return JSON response.

        :return: Response object.
        """
        if 'id' not in entity or 'type' not in entity:
            raise ZmonArgumentError('Entity ID and Type are required.')

        if not self.is_valid_entity_id(entity['id']):
            raise ZmonArgumentError('Invalid entity ID.')

        logger.debug('Adding new entity: {} ...'.format(entity['id']))

        resp = self.session.put(self.endpoint(ENTITIES, trailing_slash=False), json=entity)

        resp.raise_for_status()

        return resp

    @logged
    def delete_entity(self, entity_id) -> bool:
        """
        Delete entity from ZMON.

        ZMON DELETE entity API doesn't return JSON response.

        :return: True if succeeded, False otherwise.
        :rtype: bool
        """
        logger.debug('Removing existing entity: {} ...'.format(entity_id))

        resp = self.session.delete(self.endpoint(ENTITIES, entity_id))

        resp.raise_for_status()

        return resp.text == '1'

########################################################################################################################
# DASHBOARD
########################################################################################################################

    @logged
    def get_dashboard(self, dashboard_id):
        resp = self.session.get(self.endpoint(DASHBOARD, dashboard_id))

        return self.json(resp)

    @logged
    def update_dashboard(self, dashboard):
        if 'id' in dashboard and dashboard['id']:
            logger.debug('Updating dashboard with ID: {} ...'.format(dashboard['id']))

            resp = self.session.post(self.endpoint(DASHBOARD, dashboard['id']), json=dashboard)

            return self.json(resp)
        else:
            # new dashboard
            logger.debug('Adding new dashboard ...')
            resp = self.session.post(self.endpoint(DASHBOARD), json=dashboard)

        resp.raise_for_status()

        return self.json(resp)

########################################################################################################################
# CHECK-DEFS
########################################################################################################################

    @logged
    def get_check_definition(self, definition_id):
        resp = self.session.get(self.endpoint(CHECK_DEF, definition_id))

        return self.json(resp)

    @logged
    def update_check_definition(self, check_definition):
        if 'owning_team' not in check_definition:
            raise ZmonArgumentError('Check definition must have owning_team')

        if 'status' not in check_definition:
            check_definition['status'] = 'ACTIVE'

        self.validate_check_command(check_definition['command'])

        resp = self.session.post(self.endpoint(CHECK_DEF), json=check_definition)

        return self.json(resp)

    @logged
    def delete_check_definition(self, check_definition_id):
        resp = self.session.delete(self.endpoint(CHECK_DEF, check_definition_id))

        resp.raise_for_status()

        return resp

########################################################################################################################
# ALERT-DEFS & DATA
########################################################################################################################

    @logged
    def get_alert_definition(self, alert_id):
        resp = self.session.get(self.endpoint(ALERT_DEF, alert_id))

        return self.json(resp)

    @logged
    def create_alert_definition(self, alert_definition):
        if 'last_modified_by' not in alert_definition:
            raise ZmonArgumentError('Alert definition must have last_modified_by')

        if 'status' not in alert_definition:
            alert_definition['status'] = 'ACTIVE'

        if 'check_definition_id' not in alert_definition:
            raise ZmonArgumentError('Alert defintion must have "check_definition_id"')

        resp = self.session.post(self.endpoint(ALERT_DEF), json=alert_definition)

        return self.json(resp)

    @logged
    def update_alert_definition(self, alert_definition):
        if 'last_modified_by' not in alert_definition:
            raise ZmonArgumentError('Alert definition must have "last_modified_by"')

        if 'id' not in alert_definition:
            raise ZmonArgumentError('Alert definition must have "id"')

        if 'check_definition_id' not in alert_definition:
            raise ZmonArgumentError('Alert defintion must have "check_definition_id"')

        if 'status' not in alert_definition:
            alert_definition['status'] = 'ACTIVE'

        resp = self.session.put(
            self.endpoint(ALERT_DEF, alert_definition['id']), json=alert_definition)

        return self.json(resp)

    @logged
    def delete_alert_definition(self, alert_definition_id):
        resp = self.session.delete(self.endpoint(ALERT_DEF, alert_definition_id))

        return self.json(resp)

    @logged
    def get_alert_data(self, alert_id):
        resp = self.session.get(self.endpoint(ALERT_DATA, alert_id, 'all-entities'))

        return self.json(resp)

########################################################################################################################
# ONETIME-TOKENS
########################################################################################################################

    @logged
    def list_onetime_tokens(self):
        resp = self.session.get(self.endpoint(TOKENS))

        return self.json(resp)

    @logged
    def get_onetime_token(self):
        resp = self.session.post(self.endpoint(TOKENS), json={})

        resp.raise_for_status()

        return resp.text

########################################################################################################################
# GRAFANA
########################################################################################################################

    @logged
    def get_grafana_dashboard(self, grafana_dashboard_id):
        resp = self.session.get(self.endpoint(GRAFANA, grafana_dashboard_id))

        return self.json(resp)

    @logged
    def update_grafana_dashboard(self, grafana_dashboard):
        if 'id' not in grafana_dashboard['dashboard']:
            raise ZmonArgumentError('Grafana dashboard must have id')
        elif 'title' not in grafana_dashboard['dashboard']:
            raise ZmonArgumentError('Grafana dashboard must have title')

        resp = self.session.post(self.endpoint(GRAFANA), json=grafana_dashboard)

        return self.json(resp)

########################################################################################################################
# DOWNTIMES
########################################################################################################################

    @logged
    def create_downtime(self, downtime):
        if not downtime.get('entities'):
            raise ZmonArgumentError('At least one entity ID should be specified')

        if not downtime.get('start_time') or not downtime.get('end_time'):
            raise ZmonArgumentError('Downtime must specify "start_time" and "end_time"')

        resp = self.session.post(self.endpoint(DOWNTIME), json=downtime)

        return self.json(resp)

########################################################################################################################
# GROUPS - MEMBERS - ???
########################################################################################################################

    @logged
    def get_groups(self):
        resp = self.session.get(self.endpoint(GROUPS))

        return self.json(resp)

    @logged
    def switch_active_user(self, group_name, user_name):
        resp = self.session.delete(self.endpoint(GROUPS, group_name, 'active'))

        if not resp.ok:
            logger.error('Failed to de-activate group: {}'.format(group_name))
            resp.raise_for_status()

        logger.debug('Switching active user: {}'.format(user_name))

        resp = self.session.put(self.endpoint(GROUPS, group_name, 'active', user_name))

        if not resp.ok:
            logger.error('Failed to switch active user {}'.format(user_name))
            resp.raise_for_status()

        return resp.text == '1'

    @logged
    def add_member(self, group_name, user_name):
        resp = self.session.put(self.endpoint(GROUPS, group_name, MEMBER, user_name))

        resp.raise_for_status

        return resp.text == '1'

    @logged
    def remove_member(self, group_name, user_name):
        resp = self.session.delete(self.endpoint(GROUPS, group_name, MEMBER, user_name))

        resp.raise_for_status()

        return resp.text == '1'

    @logged
    def add_phone(self, member_email, phone_nr):
        resp = self.session.put(self.endpoint(GROUPS, member_email, PHONE, phone_nr))

        resp.raise_for_status()

        return resp.text == '1'

    @logged
    def remove_phone(self, member_email, phone_nr):
        resp = self.session.delete(self.endpoint(GROUPS, member_email, PHONE, phone_nr))

        resp.raise_for_status()

        return resp.text == '1'

    @logged
    def set_name(self, member_email, member_name):
        resp = self.session.put(self.endpoint(GROUPS, member_email, PHONE, member_name))

        resp.raise_for_status()

        return resp
