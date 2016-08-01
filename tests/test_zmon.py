import json

import pytest

from mock import MagicMock

import zmon_cli.client as client
from zmon_cli.client import Zmon


URL = 'https://some-zmon'
TOKEN = 123


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

    status = zmon.get_entities(query=q)

    assert status == result

    params = {'query': json.dumps(q)} if q else None
    get.assert_called_with(zmon.endpoint(client.ENTITIES), params=params)


def test_zmon_get_entity(monkeypatch):
    get = MagicMock()
    result = {'id': 1, 'type': 'dummy'}
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    status = zmon.get_entity(1)

    assert status == result

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

    status = zmon.get_dashboard(1)

    assert status == result

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


def test_zmon_get_check_defintion(monkeypatch):
    get = MagicMock()
    result = {'id': 1, 'type': 'dummy'}
    get.return_value.json.return_value = result

    monkeypatch.setattr('requests.Session.get', get)

    zmon = Zmon(URL, token=TOKEN)

    check = zmon.get_check_definition(1)

    assert check == result

    get.assert_called_with(zmon.endpoint(client.CHECK_DEF, 1))


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
