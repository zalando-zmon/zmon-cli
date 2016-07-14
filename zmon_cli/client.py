import os
import logging
import json
import functools
import re

from urllib.parse import urljoin

import requests

from zmon_cli import __version__


ZMON_USER_AGENT = 'zmon-client/{}'.format(__version__)

ENTITIES = 'entities'
DASHBOARD = 'dashboard'
STATUS = 'status'
CHECK_DEF = 'check-definitions'
ALERT_DEF = 'alert-definitions'
TOKENS = 'onetime-tokens'
ALERT_DATA = 'status/alert'
GRAFANA = 'grafana2-dashboards'
GROUPS = 'groups'
MEMBER = 'member'
PHONE = 'phone'

logger = logging.getLogger(__name__)

valid_entity_id_re = re.compile('^[a-z0-9-\[\]\:]+$')


class ZmonError(Exception):
    def __init__(self, message):
        super().__init__('ZMON client error: {}'.format(message))


def logged(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except:
            logger.error('Zmon client failed in: {}'.format(f.__name__))
            raise

    return wrapper


class Zmon:

    def __init__(
            self, url, token=None, username=None, password=None, timeout=10, verify=True, user_agent=ZMON_USER_AGENT):
        self.url = url
        self.timeout = timeout

        self._session = requests.Session()

        self._session.timeout = timeout
        self.user_agent = user_agent

        if username and password and token is None:
            self._session.auth = (username, password)

        self._session.headers.update({'User-Agent': user_agent, 'Content-Type': 'application/json'})

        if token:
            self._session.headers.update({'Authorization': 'Bearer {}'.format(token)})

        if not verify:
            logger.warning('ZMon client will skip SSL verification!')
            requests.packages.urllib3.disable_warnings()
            self._session.verify = False

    @property
    def session(self):
        return self._session

    @staticmethod
    def is_valid_entity_id(entity_id):
        return valid_entity_id_re.match(entity_id) is not None

    def endpoint(self, *args, trailing_slash=True):
        parts = list(args)

        # Ensure trailing slash!
        if trailing_slash:
            parts.append('')

        return urljoin(self.url, os.path.join(*[str(p) for p in parts]))

    def json(self, resp):
        resp.raise_for_status()

        return resp.json()

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

        resp = self.session.get(self.endpoint(ENTITIES, entity_id))
        return self.json(resp)

    @logged
    def add_entity(self, entity):
        """
        Create or update entity on ZMon.

        ZMon PUT entity API doesn't return JSON response.

        :return: Response object.
        """
        if 'id' not in entity or 'type' not in entity:
            raise ZmonError('Entity ID and Type are required.')

        if not self.is_valid_entity_id(entity['id']):
            raise ZmonError('Invalid entity ID.')

        logger.debug('Adding new enitity: {} ...'.format(entity['id']))

        resp = self.session.put(self.endpoint(ENTITIES), json=entity)

        resp.raise_for_status()

        return resp

    @logged
    def delete_entity(self, entity_id) -> bool:
        """
        Delete entity from ZMon.

        ZMon DELETE entity API doesn't return JSON response.

        :return: True if succeeded, False otherwise.
        :rtype: bool
        """
        logger.debug('Removing existing enitity: {} ...'.format(entity_id))

        resp = self.session.delete(self.endpoint(ENTITIES, entity_id))

        resp.raise_for_status()

        return resp.text == '1'

    @logged
    def status(self):
        resp = self.session.get(self.endpoint(STATUS))

        return self.json(resp)

    @logged
    def get_dashboard(self, dashboard_id):
        resp = self.session.get(self.endpoint(DASHBOARD, dashboard_id))

        return self.json(resp)

    @logged
    def update_dashboard(self, dashboard):
        if 'id' in dashboard:
            logger.debug('Updating dashboard with ID: {} ...'.format(dashboard['id']))

            resp = self.session.post(self.endpoint(DASHBOARD, dashboard['id']), json=dashboard)
        else:
            resp = self.session.post(self.endpoint(DASHBOARD), json=dashboard)

        return self.json(resp)

    @logged
    def get_check_definition(self, definition_id):
        resp = self.session.get(self.endpoint(CHECK_DEF, definition_id))

        return self.json(resp)

    @logged
    def update_check_definition(self, check_definition):
        if 'owning_team' not in check_definition:
            raise ZmonError('Check definition must have owning_team')

        if 'status' not in check_definition:
            check_definition['status'] = 'ACTIVE'

        resp = self.session.post(self.endpoint(CHECK_DEF), json=check_definition)

        return self.json(resp)

    @logged
    def delete_check_definition(self, check_definition_id):
        resp = self.session.delete(self.endpoint(CHECK_DEF, check_definition_id))

        resp.raise_for_status()

        return resp

    @logged
    def get_alert_definition(self, alert_id):
        resp = self.session.get(self.endpoint(ALERT_DEF, alert_id))

        return self.json(resp)

    @logged
    def create_alert_definition(self, alert_definition):
        if 'last_modified_by' not in alert_definition:
            raise ZmonError('Alert definition must have last_modified_by')

        if 'status' not in alert_definition:
            alert_definition['status'] = 'ACTIVE'

        resp = self.session.post(self.endpoint(ALERT_DEF), json=alert_definition)

        return self.json(resp)

    @logged
    def update_alert_definition(self, alert_definition):
        if 'last_modified_by' not in alert_definition:
            raise ZmonError('Alert definition must have last_modified_by')

        if 'id' not in alert_definition:
            raise ZmonError('Alert definition must have "id"')

        if 'status' not in alert_definition:
            alert_definition['status'] = 'ACTIVE'

        resp = self.session.put(
            self.endpoint(ALERT_DEF, alert_definition['id']), json=alert_definition)

        return self.json(resp)

    @logged
    def list_tv_tokens(self):
        resp = self.session.get(self.endpoint(TOKENS))

        return self.json(resp)

    @logged
    def get_tv_tokens(self) -> str:
        resp = self.session.post(self.endpoint(TOKENS), json={})

        resp.raise_for_status()

        return resp.text

    @logged
    def get_alert_data(self, alert_id):
        resp = self.session.get(self.endpoint(ALERT_DATA, alert_id, 'all-entities'))

        return self.json(resp)

    @logged
    def get_grafana_dashboard(self, grafana_dashboard_id):
        resp = self.session.get(self.endpoint(GRAFANA, grafana_dashboard_id))

        return self.json(resp)

    @logged
    def update_grafana_dashboard(self, grafana_dashboard):
        if 'id' not in grafana_dashboard:
            raise ZmonError('Grafana dashboard must have id')
        elif 'title' not in grafana_dashboard:
            raise ZmonError('Grafana dashboard must have title')

        resp = self.session.post(self.endpoint(GRAFANA), json=grafana_dashboard)

        return self.json(resp)

    @logged
    def get_groups(self):
        resp = self.session.get(self.endpoint(GROUPS))

        return self.json(resp)

    @logged
    def switch_active_user(self, group_name, user_name) -> bool:
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
    def add_member(self, group_name, user_name) -> bool:
        resp = self.session.put(self.endpoint(GROUPS, group_name, MEMBER, user_name))

        resp.raise_for_status

        return resp.text == '1'

    @logged
    def remove_member(self, group_name, user_name) -> bool:
        resp = self.session.delete(self.endpoint(GROUPS, group_name, MEMBER, user_name))

        resp.raise_for_status()

        return resp.text == '1'

    @logged
    def add_phone(self, member_email, phone_nr) -> bool:
        resp = self.session.put(self.endpoint(GROUPS, member_email, PHONE, phone_nr))

        resp.raise_for_status()

        return resp.text == '1'

    @logged
    def remove_phone(self, member_email, phone_nr) -> bool:
        resp = self.session.delete(self.endpoint(GROUPS, member_email, PHONE, phone_nr))

        resp.raise_for_status()

        return resp.text == '1'

    @logged
    def set_name(self, member_email, member_name):
        resp = self.session.delete(self.endpoint(GROUPS, member_email, PHONE, member_name))

        resp.raise_for_status()

        return resp
