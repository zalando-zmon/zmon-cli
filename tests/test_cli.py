import yaml
from unittest.mock import MagicMock
from click.testing import CliRunner


from zmon_cli.main import cli
from zmon_cli.client import Zmon


def get_client(config):
    return Zmon('https://zmon-api', token='123')


def test_configure(monkeypatch):
    get = MagicMock()
    monkeypatch.setattr('requests.get', get)

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli, ['configure', '-c', 'test.yaml'], catch_exceptions=False, input='https://example.org\n\n')

        assert 'Writing configuration' in result.output

        with open('test.yaml') as fd:
            data = yaml.safe_load(fd)

        assert data['url'] == 'https://example.org'
        assert 'token' not in data


def test_status(monkeypatch):
    get = MagicMock()
    get.return_value = {
        'workers': [{'name': 'foo', 'check_invocations': 12377, 'last_execution_time': 1}]
    }
    monkeypatch.setattr('zmon_cli.client.Zmon.status', get)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['status'], catch_exceptions=False)

        assert 'foo' in result.output
        assert '12377' in result.output
        assert 'd ago' in result.output


def test_status_zign(monkeypatch):
    get = MagicMock()
    get.return_value = {
        'workers': [{'name': 'foo', 'check_invocations': 12377, 'last_execution_time': 1}]
    }

    get_token = MagicMock()
    get_token.return_value = '1298'

    monkeypatch.setattr('zmon_cli.client.Zmon.status', get)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)
    monkeypatch.setattr('zign.api.get_token', get_token)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo'}, fd)

        result = runner.invoke(cli, ['-c', 'test.yaml', 'status'], catch_exceptions=False)

        assert 'foo' in result.output
        assert '12377' in result.output
        assert 'd ago' in result.output

    get_token.assert_called_with('zmon', ['uid'])


def test_get_alert_definition(monkeypatch):
    get = MagicMock()
    get.return_value = {
        'id': 123, 'check_definition_id': 9, 'name': 'Test', 'condition': '>0', 'foo': None
    }

    monkeypatch.setattr('zmon_cli.client.Zmon.get_alert_definition', get)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': 123}, fd)

        result = runner.invoke(cli, ['-c', 'test.yaml', 'alert', 'get', '123'], catch_exceptions=False)

        assert 'id: 123\ncheck_definition_id: 9\nname: Test\ncondition: |-\n  >0' in result.output.rstrip()


def test_list_alert_definitions(monkeypatch):
    get = MagicMock()
    get.return_value = []

    monkeypatch.setattr('zmon_cli.client.Zmon.get_alert_definitions', get)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': 123}, fd)

        result = runner.invoke(cli, ['-c', 'test.yaml', 'alert', 'l'], catch_exceptions=False)

        out = result.output.rstrip()

        assert 'Id' in out
        assert 'Name' in out
        assert 'Check ID' in out
        assert 'Link' in out


def test_filter_alert_definitions(monkeypatch):
    get = MagicMock()
    get.return_value = [
        {
            'team': 'ZMON', 'responsible_team': 'ZMON', 'name': 'alert-1', 'id': 1, 'status': 'ACTIVE', 'priority': 1,
            'last_modified': 1473418659294, 'last_modified_by': 'user-1', 'check_definition_id': 33
        },
        {
            'team': 'FANCY', 'responsible_team': 'ZMON', 'name': 'alert-2', 'id': 2, 'status': 'ACTIVE', 'priority': 2,
            'last_modified': 1473418659294, 'last_modified_by': 'user-2', 'check_definition_id': 34
        },
    ]

    monkeypatch.setattr('zmon_cli.client.Zmon.get_alert_definitions', get)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': 123}, fd)

        result = runner.invoke(cli, ['-c', 'test.yaml', 'alert', 'f', 'team', 'ZMON'], catch_exceptions=False)

        out = result.output.rstrip()

        assert 'ZMON' in out
        assert 'alert-1' in out
        assert 'ago' in out
        assert 'Link' in out
        assert 'HIGH' in out

        assert 'FANCY' not in out
        assert 'alert-2' not in out
        assert 'MEDIUM' not in out

        result = runner.invoke(
            cli, ['-c', 'test.yaml', 'alert', 'f', 'check_definition_id', '34'], catch_exceptions=False)

        out = result.output.rstrip()

        assert 'ZMON' in out
        assert 'alert-1' not in out

        assert 'ago' in out
        assert 'Link' in out

        assert 'FANCY' in out
        assert 'alert-2' in out
        assert 'MEDIUM' in out


def test_update_check_definition_invalid(monkeypatch):
    monkeypatch.setattr('zmon_cli.config.DEFAULT_CONFIG_FILE', 'test.yaml')

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': '123'}, fd)

        with open('check.yaml', 'w') as fd:
            yaml.safe_dump({}, fd)

        result = runner.invoke(cli, ['-c', 'test.yaml', 'check', 'update', 'check.yaml'], catch_exceptions=False)

        assert 'owning_team' in result.output


def test_update_check_definition(monkeypatch):
    monkeypatch.setattr('zmon_cli.config.DEFAULT_CONFIG_FILE', 'test.yaml')

    post = MagicMock()
    post.return_value = {'id': 7}
    monkeypatch.setattr('zmon_cli.client.Zmon.update_check_definition', post)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': '123'}, fd)

        with open('check.yaml', 'w') as fd:
            yaml.safe_dump({'owning_team': 'myteam', 'command': 'do_stuff()'}, fd)

        result = runner.invoke(cli, ['-c', 'test.yaml', 'check', 'update', 'check.yaml'], catch_exceptions=False)

        assert '/check-definitions/view/7' in result.output


def test_get_check_definition(monkeypatch):
    get = MagicMock()
    get.return_value = {
        'id': 123, 'name': 'Test', 'command': 'http().json()'
    }

    monkeypatch.setattr('zmon_cli.client.Zmon.get_check_definition', get)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': 123}, fd)

        result = runner.invoke(cli, ['-c', 'test.yaml', 'check', 'get', '123'], catch_exceptions=False)

        assert 'id: 123\nname: Test\ncommand: |-\n  http().json()' in result.output.rstrip()

        result = runner.invoke(cli, ['-c', 'test.yaml', 'check', 'get', '123', '-o', 'json'], catch_exceptions=False)

        out = result.output.rstrip()
        assert '"name": "Test"' in out
        assert '"id": 123' in out
        assert '"command": "http().json()"' in out


def test_list_check_definitions(monkeypatch):
    get = MagicMock()
    get.return_value = []

    monkeypatch.setattr('zmon_cli.client.Zmon.get_check_definitions', get)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': 123}, fd)

        result = runner.invoke(cli, ['-c', 'test.yaml', 'check', 'l'], catch_exceptions=False)

        out = result.output.rstrip()

        assert 'Id' in out
        assert 'Name' in out
        assert 'Owning Team' in out
        assert 'Link' in out


def test_filter_check_definitions(monkeypatch):
    get = MagicMock()
    get.return_value = [
        {
            'owning_team': 'ZMON', 'name': 'check-1', 'id': 1, 'status': 'ACTIVE', 'last_modified': 1473418659294,
            'last_modified_by': 'user-1'
        },
        {
            'owning_team': 'FANCY', 'name': 'check-2', 'id': 2, 'status': 'ACTIVE', 'last_modified': 1473418659294,
            'last_modified_by': 'user-2'
        },
    ]

    monkeypatch.setattr('zmon_cli.client.Zmon.get_check_definitions', get)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': 123}, fd)

        result = runner.invoke(cli, ['-c', 'test.yaml', 'check', 'f', 'owning_team', 'ZMON'], catch_exceptions=False)

        out = result.output.rstrip()

        assert 'ZMON' in out
        assert 'check-1' in out
        assert 'ago' in out
        assert 'Link' in out

        assert 'FANCY' not in out
        assert 'check-2' not in out


def test_filter_entities(monkeypatch):
    get = MagicMock()
    get.return_value = [
        {'id': 'e-1', 'type': 'instance', 'application_id': 'app-1', 'last_modified': '2017-01-01 01:01:01.000'}
    ]

    monkeypatch.setattr('zmon_cli.client.Zmon.get_entities', get)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': 123}, fd)

        result = runner.invoke(
            cli, ['-c', 'test.yaml', 'e', 'f', 'type', 'instance', 'application_id', 'app-1'], catch_exceptions=False)

        out = result.output.rstrip()

        assert 'e-1' in out
        assert 'app-1' in out

        get.assert_called_with(query={'type': 'instance', 'application_id': 'app-1'})


def test_search(monkeypatch):
    get = MagicMock()
    get.return_value = {'alerts': [], 'checks': [], 'dashboards': [], 'grafana_dashboards': []}

    monkeypatch.setattr('zmon_cli.client.Zmon.search', get)
    monkeypatch.setattr('zmon_cli.cmds.command.get_client', get_client)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': '123'}, fd)

        result = runner.invoke(
            cli, ['-c', 'test.yaml', 'search', 'zmon', '-t', 'team-1', '--team', 'team-2'], catch_exceptions=False)

        assert 'Alerts:' in result.output
        assert 'Checks:' in result.output
        assert 'Dashboards:' in result.output
        assert 'Grafana Dashboards:' in result.output

    get.return_value = {'alerts': [], 'checks': [], 'dashboards': [], 'grafana_dashboards': [
        {
            "id": "eagleeye-operational-dashboard",
            "team": "",
            "title": "EagleEye operational dashboard"
        }
    ]}

    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo', 'token': '123'}, fd)

        result = runner.invoke(
            cli, ['-c', 'test.yaml', 'search', 'eagle'], catch_exceptions=False)

        assert 'eagle' in result.output
