import json

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from requests.exceptions import HTTPError

import zmon_cli.client as client
from zmon_cli.client import Zmon


URL = 'https://some-zmon'
TOKEN = 123


DATE = datetime.now()


@pytest.mark.parametrize('e,expected', [
    ('zmon-ZMON-1.2@[_staging:]', True),
    ('zmon ZMON', False),
    ('zmon!44', False),
    ('zmon#1', False),
    ('zmon(staging)', False),
])
def test_zmon_is_valid_id(monkeypatch, e, expected):
    assert Zmon.is_valid_entity_id(e) == expected


def test_get_entity_id(monkeypatch, fx_ids):
    inp, exp = fx_ids

    print(client.get_valid_entity_id(inp))
    assert client.get_valid_entity_id(inp) == exp


@pytest.mark.parametrize('e1,e2,result', [
    (
        {'id': '1', 'nested': {'k': 'v', 'k2': 'v'}, 'date': DATE},
        {'id': '1', 'nested': {'k2': 'v', 'k': 'v'}, 'date': DATE, 'last_modified': 1234},
        True
    ),
    (
        {'id': '1', 'nested': {'k': 'v', 22: 22}, 'last_modified': 1234},
        {'id': '1', 'nested': {'22': 22, 'k': 'v'}, 'last_modified': 1234567},
        True
    ),
    (
        {'id': '1', 'nested': {'k': 'v', 22: 22, 'k3': {'list': [1, 2, 3]}}},
        {'id': '1', 'nested': {'22': 22, 'k': 'v', 'k3': {'list': [1, 2]}}},
        False
    ),
    (
        {},
        str,  # JSON exception!
        False
    )
])
def test_zmon_compare_entities(monkeypatch, e1, e2, result):
    assert client.compare_entities(e1, e2) == result


def test_zmon_view_urls(monkeypatch):
    zmon = Zmon(URL, token=TOKEN)

    # Checks
    check = {'id': 1}
    assert '{}#/check-definitions/view/1/'.format(URL) == zmon.check_definition_url(check)

    # Alerts
    alert = {'id': 1}
    assert '{}#/alert-details/1/'.format(URL) == zmon.alert_details_url(alert)

    # Dashboard
    dashboard_id = 1
    assert '{}#/dashboards/views/1/'.format(URL) == zmon.dashboard_url(dashboard_id)

    # Token
    token = '1234'
    assert '{}/tv/1234/'.format(URL) == zmon.token_login_url(token)

    # Grafana
    dashboard = {'id': 'grafana-dash'}
    assert '{}/grafana/dashboard/db/grafana-dash/'.format(URL) == zmon.grafana_dashboard_url(dashboard)


def test_zmon_headers(monkeypatch):
    zmon = Zmon(URL, token=TOKEN)
    assert zmon.session.headers['Authorization'] == 'Bearer {}'.format(TOKEN)

    zmon = Zmon(URL, username='user1', password='password')
    assert zmon.session.auth == ('user1', 'password')

    zmon = Zmon(URL, token=TOKEN)
    assert zmon.session.headers['User-Agent'] == client.ZMON_USER_AGENT

    zmon = Zmon(URL, token=TOKEN, user_agent='zmon-client-wrapper/0.5')
    assert zmon.session.headers['User-Agent'] == 'zmon-client-wrapper/0.5'

    zmon = Zmon(URL, token=TOKEN, verify=False)
    assert zmon.session.verify is False


def test_zmon_status(monkeypatch):
    get = MagicMock()
    result = {'status': 'success'}
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    status = zmon.status()

    assert status == result

    get.assert_called_with(zmon.endpoint(client.STATUS))


@pytest.mark.parametrize('q,result', [(None, [{'id': 1}]), ({'type': 'dummy'}, [{'id': 2}])])
def test_zmon_get_entities(monkeypatch, q, result):
    get = MagicMock()
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    res = zmon.get_entities(query=q)

    assert res == result

    params = {'query': json.dumps(q)} if q else None
    get.assert_called_with(zmon.endpoint(client.ENTITIES), params=params)


def test_zmon_get_entity(monkeypatch):
    get = MagicMock()
    result = {'id': 1, 'type': 'dummy'}
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    res = zmon.get_entity(1)

    assert res == result

    get.assert_called_with(zmon.endpoint(client.ENTITIES, 1, trailing_slash=False))


@pytest.mark.parametrize('e,result', [
    ({'id': '2', 'type': 'dummy'}, {'id': '2', 'type': 'dummy'}),
    ({'id': '2'}, client.ZmonArgumentError),
    ({'type': 'dummy'}, client.ZmonArgumentError),
    ({'id': 'zmon/1', 'type': 'dummy'}, client.ZmonArgumentError),
])
def test_zmon_add_entity(monkeypatch, e, result):
    fail = True
    if type(result) is dict:
        fail = False

    put = MagicMock()
    resp = MagicMock()
    resp.ok = True
    put.return_value = resp

    monkeypatch.setattr('requests.Session.put', put)

    zmon = Zmon(URL, token=TOKEN)

    if fail:
        with pytest.raises(result):
            zmon.add_entity(e)
    else:
        r = zmon.add_entity(e)
        assert r.ok is True

        put.assert_called_with(zmon.endpoint(client.ENTITIES, trailing_slash=False), json=e)


@pytest.mark.parametrize('result', ['1', '0'])
def test_zmon_delete_entity(monkeypatch, result):
    delete = MagicMock()
    delete.return_value.text = result

    monkeypatch.setattr('requests.Session.delete', delete)

    zmon = Zmon(URL, token=TOKEN)

    deleted = zmon.delete_entity(1)

    assert deleted is (result == '1')

    delete.assert_called_with(zmon.endpoint(client.ENTITIES, 1))


def test_zmon_get_dashboard(monkeypatch):
    get = MagicMock()
    result = {'id': 1, 'type': 'dummy'}
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    res = zmon.get_dashboard(1)

    assert res == result

    get.assert_called_with(zmon.endpoint(client.DASHBOARD, 1))


@pytest.mark.parametrize('d', [{'id': 1}, {'id': ''}])
def test_zmon_update_dashboard(monkeypatch, d):
    post = MagicMock()
    result = 1
    post.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.post', post)

    zmon = Zmon(URL, token=TOKEN)

    res = zmon.update_dashboard(d)
    assert res == result

    url = zmon.endpoint(client.DASHBOARD, 1) if d['id'] else zmon.endpoint(client.DASHBOARD)
    post.assert_called_with(url, json=d)


@pytest.mark.parametrize('text,result', [('{"id": 1, "type": "dummy"}', {'id': 1, 'type': 'dummy'}), ('', HTTPError)])
def test_zmon_get_check_defintion(monkeypatch, text, result):
    get = MagicMock()

    get.return_value.text = text
    get.return_value.json.return_value = result
    if type(result) != dict:
        get.return_value.raise_for_status.side_effect = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    if type(result) == dict:
        res = zmon.get_check_definition(1)

        assert res == result
    else:
        with pytest.raises(result):
            zmon.get_check_definition(1)

    get.assert_called_with(zmon.endpoint(client.CHECK_DEF, 1))


@pytest.mark.parametrize('resp,result', [
    ({'check_definitions': [1, 2]}, [1, 2]),
    ({'check_definitions': []}, [])])
def test_zmon_get_check_defintions(monkeypatch, resp, result):
    get = MagicMock()
    get.return_value.json.return_value = resp

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    res = zmon.get_check_definitions()

    assert res == result

    get.assert_called_with(zmon.endpoint(client.ACTIVE_CHECK_DEF))


@pytest.mark.parametrize('c,result', [
    (
        {'id': '2', 'owning_team': 'Zmon', 'command': 'return True'},
        {'id': '2', 'owning_team': 'Zmon', 'command': 'return True', 'status': 'ACTIVE'}
    ),
    (
        {'id': '2', 'owning_team': 'Zmon', 'command': 'return True', 'status': 'INACTIVE'},
        {'id': '2', 'owning_team': 'Zmon', 'command': 'return True', 'status': 'INACTIVE'}
    ),
    ({'id': '2'}, client.ZmonArgumentError),
    ({'id': '2', 'owning_team': 'Zmon', 'command': 'def x('}, client.ZmonError),
])
def test_zmon_update_check_defintion(monkeypatch, c, result):
    fail = True
    if type(result) is dict:
        fail = False

    post = MagicMock()
    post.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.post', post)

    zmon = Zmon(URL, token=TOKEN)

    if fail:
        with pytest.raises(result):
            zmon.update_check_definition(c)
    else:
        check = zmon.update_check_definition(c)
        assert check == result

        post.assert_called_with(zmon.endpoint(client.CHECK_DEF), json=c)


@pytest.mark.parametrize('result', [True, False])
def test_zmon_delete_check_definition(monkeypatch, result):
    delete = MagicMock()
    delete.return_value.ok = result

    monkeypatch.setattr('requests.Session.delete', delete)

    zmon = Zmon(URL, token=TOKEN)

    res = zmon.delete_check_definition(1)

    assert res.ok is result

    delete.assert_called_with(zmon.endpoint(client.CHECK_DEF, 1))


def test_zmon_get_alert_defintion(monkeypatch):
    get = MagicMock()
    result = {'id': 1, 'type': 'dummy'}
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    check = zmon.get_alert_definition(1)

    assert check == result

    get.assert_called_with(zmon.endpoint(client.ALERT_DEF, 1))


@pytest.mark.parametrize('resp,result', [
    ({'alert_definitions': [1, 2]}, [1, 2]),
    ({'alert_definitions': []}, [])])
def test_zmon_get_alert_defintions(monkeypatch, resp, result):
    get = MagicMock()
    get.return_value.json.return_value = resp

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    res = zmon.get_alert_definitions()

    assert res == result

    get.assert_called_with(zmon.endpoint(client.ACTIVE_ALERT_DEF))


@pytest.mark.parametrize('a,result', [
    (
        {'check_definition_id': '4545', 'last_modified_by': 'user1'},
        {'check_definition_id': '4545', 'last_modified_by': 'user1', 'status': 'ACTIVE'}
    ),
    (
        {'check_definition_id': '4545', 'last_modified_by': 'user1', 'status': 'INACTIVE'},
        {'check_definition_id': '4545', 'last_modified_by': 'user1', 'status': 'INACTIVE'}
    ),
    (
        {'check_definition_id': '4545'},
        client.ZmonArgumentError
    ),
    (
        {'last_modified_by': 'user1'},
        client.ZmonArgumentError
    ),
])
def test_zmon_create_alert_defintion(monkeypatch, a, result):
    fail = True
    if type(result) is dict:
        fail = False

    post = MagicMock()
    post.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.post', post)

    zmon = Zmon(URL, token=TOKEN)

    if fail:
        with pytest.raises(result):
            zmon.create_alert_definition(a)
    else:
        check = zmon.create_alert_definition(a)
        assert check == result

        post.assert_called_with(zmon.endpoint(client.ALERT_DEF), json=a)


@pytest.mark.parametrize('a,result', [
    (
        {'id': 3434, 'check_definition_id': '4545', 'last_modified_by': 'user1'},
        {'id': 3434, 'check_definition_id': '4545', 'last_modified_by': 'user1', 'status': 'ACTIVE'}
    ),
    (
        {'id': 3434, 'check_definition_id': '4545', 'last_modified_by': 'user1', 'status': 'INACTIVE'},
        {'id': 3434, 'check_definition_id': '4545', 'last_modified_by': 'user1', 'status': 'INACTIVE'}
    ),
    (
        {'check_definition_id': '4545', 'last_modified_by': 'user1'},
        client.ZmonArgumentError
    ),
    (
        {'id': 3434, 'check_definition_id': '4545'},
        client.ZmonArgumentError
    ),
    (
        {'id': 3434, 'last_modified_by': 'user1'},
        client.ZmonArgumentError
    ),
])
def test_zmon_update_alert_defintion(monkeypatch, a, result):
    fail = True
    if type(result) is dict:
        fail = False

    put = MagicMock()
    put.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.put', put)

    zmon = Zmon(URL, token=TOKEN)

    if fail:
        with pytest.raises(result):
            zmon.update_alert_definition(a)
    else:
        check = zmon.update_alert_definition(a)
        assert check == result

        put.assert_called_with(zmon.endpoint(client.ALERT_DEF, a['id']), json=a)


def test_zmon_delete_alert_definition(monkeypatch):
    delete = MagicMock()
    result = {'status': 'success'}
    delete.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.delete', delete)

    zmon = Zmon(URL, token=TOKEN)

    res = zmon.delete_alert_definition(1)

    assert res == result

    delete.assert_called_with(zmon.endpoint(client.ALERT_DEF, 1))


def test_zmon_alert_data(monkeypatch):
    get = MagicMock()
    result = {'entity-1': []}
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    check = zmon.get_alert_data(1)

    assert check == result

    get.assert_called_with(zmon.endpoint(client.ALERT_DATA, 1, 'all-entities'))


def test_zmon_search(monkeypatch):
    get = MagicMock()
    result = {'alerts': []}
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    q = 'health check'
    search = zmon.search(q)

    assert search == result

    get.assert_called_with(zmon.endpoint(client.SEARCH), params={'query': q})


def test_zmon_search_team(monkeypatch):
    get = MagicMock()
    result = {'alerts': []}
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    q = 'health check'
    teams = ['team-1', 'team-2']
    search = zmon.search(q, teams)

    assert search == result

    get.assert_called_with(zmon.endpoint(client.SEARCH), params={'query': q, 'teams': 'team-1,team-2'})


def test_zmon_list_tokens(monkeypatch):
    get = MagicMock()
    result = [1, 2, 3]
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    check = zmon.list_onetime_tokens()

    assert check == result

    get.assert_called_with(zmon.endpoint(client.TOKENS))


def test_zmon_get_token(monkeypatch):
    post = MagicMock()
    result = '1111'
    post.return_value.text = result

    monkeypatch.setattr('requests.Session.post', post)

    zmon = Zmon(URL, token=TOKEN)

    check = zmon.get_onetime_token()

    assert check == result

    post.assert_called_with(zmon.endpoint(client.TOKENS), json={})


def test_zmon_get_grafana_dashboard(monkeypatch):
    get = MagicMock()
    result = {'dashboard': {}}
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    check = zmon.get_grafana_dashboard(1)

    assert check == result

    get.assert_called_with(zmon.endpoint(client.GRAFANA, 1))


@pytest.mark.parametrize('g,result', [
    (
        {'dashboard': {'id': 3434, 'title': 'grafana dash'}},
        {'dashboard': {'id': 3434, 'title': 'grafana dash'}},
    ),
    (
        {'dashboard': {'title': 'grafana dash'}},
        client.ZmonArgumentError
    ),
    (
        {'dashboard': {'id': 3434}},
        client.ZmonArgumentError
    ),
])
def test_zmon_update_grafana_dashboard(monkeypatch, g, result):
    fail = True
    if type(result) is dict:
        fail = False

    post = MagicMock()
    post.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.post', post)

    zmon = Zmon(URL, token=TOKEN)

    if fail:
        with pytest.raises(result):
            zmon.update_grafana_dashboard(g)
    else:
        check = zmon.update_grafana_dashboard(g)
        assert check == result

        post.assert_called_with(zmon.endpoint(client.GRAFANA), json=g)


@pytest.mark.parametrize('d,result', [
    (
        {'entities': [1], 'start_time': 111, 'end_time': 222},
        {'entities': [1], 'start_time': 111, 'end_time': 222},
    ),
    (
        {'entities': [], 'start_time': 111, 'end_time': 222},
        client.ZmonArgumentError
    ),
    (
        {'start_time': 111, 'end_time': 222},
        client.ZmonArgumentError
    ),
    (
        {'entities': [1, 2], 'end_time': 222},
        client.ZmonArgumentError
    ),
    (
        {'entities': [1], 'start_time': 111},
        client.ZmonArgumentError
    ),
])
def test_zmon_create_downtime(monkeypatch, d, result):
    fail = True
    if type(result) is dict:
        fail = False

    post = MagicMock()
    post.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.post', post)

    zmon = Zmon(URL, token=TOKEN)

    if fail:
        with pytest.raises(result):
            zmon.create_downtime(d)
    else:
        check = zmon.create_downtime(d)
        assert check == result

        post.assert_called_with(zmon.endpoint(client.DOWNTIME), json=d)


def test_zmon_get_groups(monkeypatch):
    get = MagicMock()
    result = [1, 2, 3]
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    check = zmon.get_groups()

    assert check == result

    get.assert_called_with(zmon.endpoint(client.GROUPS))


@pytest.mark.parametrize('success', [(True, True), (False, None), (True, False)])
def test_zmon_switch_active_user(monkeypatch, success):
    del_success, put_success = success

    delete = MagicMock()
    delete.return_value.ok = del_success
    if not del_success:
        delete.return_value.raise_for_status.side_effect = RuntimeError

    put = MagicMock()
    put.return_value.ok = put_success
    put.return_value.text = '1'
    if not put_success:
        put.return_value.raise_for_status.side_effect = RuntimeError

    monkeypatch.setattr('requests.Session.delete', delete)
    monkeypatch.setattr('requests.Session.put', put)

    zmon = Zmon(URL, token=TOKEN)

    if not del_success or not put_success:
        with pytest.raises(RuntimeError):
            zmon.switch_active_user('g', 'u')
    else:
        switched = zmon.switch_active_user('g', 'u')
        assert switched is True

    delete.assert_called_with(zmon.endpoint(client.GROUPS, 'g', 'active'))
    if del_success:
        put.assert_called_with(zmon.endpoint(client.GROUPS, 'g', 'active', 'u'))


def test_zmon_add_member(monkeypatch):
    put = MagicMock()
    put.return_value.text = '1'

    monkeypatch.setattr('requests.Session.put', put)

    zmon = Zmon(URL, token=TOKEN)

    added = zmon.add_member('group', 'user1')

    assert added is True

    put.assert_called_with(zmon.endpoint(client.GROUPS, 'group', client.MEMBER, 'user1'))


def test_zmon_remove_member(monkeypatch):
    delete = MagicMock()
    delete.return_value.text = '1'

    monkeypatch.setattr('requests.Session.delete', delete)

    zmon = Zmon(URL, token=TOKEN)

    deleted = zmon.remove_member('group', 'user1')

    assert deleted is True

    delete.assert_called_with(zmon.endpoint(client.GROUPS, 'group', client.MEMBER, 'user1'))


def test_zmon_add_phone(monkeypatch):
    put = MagicMock()
    put.return_value.text = '1'

    monkeypatch.setattr('requests.Session.put', put)

    zmon = Zmon(URL, token=TOKEN)

    added = zmon.add_phone('user1@something', '12345')

    assert added is True

    put.assert_called_with(zmon.endpoint(client.GROUPS, 'user1@something', client.PHONE, '12345'))


def test_zmon_remove_phone(monkeypatch):
    delete = MagicMock()
    delete.return_value.text = '1'

    monkeypatch.setattr('requests.Session.delete', delete)

    zmon = Zmon(URL, token=TOKEN)

    deleted = zmon.remove_phone('user1@something', '12345')

    assert deleted is True

    delete.assert_called_with(zmon.endpoint(client.GROUPS, 'user1@something', client.PHONE, '12345'))


def test_zmon_set_name(monkeypatch):
    put = MagicMock()
    put.return_value = MagicMock()

    monkeypatch.setattr('requests.Session.put', put)

    zmon = Zmon(URL, token=TOKEN)

    zmon.add_phone('user1@something', 'user1')

    put.assert_called_with(zmon.endpoint(client.GROUPS, 'user1@something', client.PHONE, 'user1'))
