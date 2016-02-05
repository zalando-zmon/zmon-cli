import yaml
from unittest.mock import MagicMock
from click.testing import CliRunner

from zmon_cli.main import cli


def test_status(monkeypatch):
    get = MagicMock()
    get.return_value.json.return_value = {'workers': [{'name': 'foo', 'check_invocations': 12377, 'last_execution_time': 1}]}
    monkeypatch.setattr('zmon_cli.main.get', get)
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['status'], catch_exceptions=False)
        assert 'foo' in result.output
        assert '12377' in result.output
        assert 'd ago' in result.output


def test_status_zign(monkeypatch):
    get = MagicMock()
    get.return_value.json.return_value = {'workers': [{'name': 'foo', 'check_invocations': 12377, 'last_execution_time': 1}]}
    get_token = MagicMock()
    get_token.return_value = '1298'
    monkeypatch.setattr('requests.get', get)
    monkeypatch.setattr('zign.api.get_token', get_token)
    monkeypatch.setattr('zmon_cli.main.DEFAULT_CONFIG_FILE', 'test.yaml')
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('test.yaml', 'w') as fd:
            yaml.dump({'url': 'foo'}, fd)
        result = runner.invoke(cli, ['status'], catch_exceptions=False)
        assert 'foo' in result.output
        assert '12377' in result.output
        assert 'd ago' in result.output
    get_token.assert_called_with('zmon', ['uid'])


def test_get_alert_definition(monkeypatch):
    get = MagicMock()
    get.return_value.json.return_value = {'id': 123, 'check_definition_id': 9, 'name': 'Test', 'condition': '>0', 'foo': None}
    monkeypatch.setattr('zmon_cli.main.get', get)
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['alert', 'get', '123'], catch_exceptions=False)
        assert 'id: 123\ncheck_definition_id: 9\nname: Test\ncondition: |-\n  >0' == result.output.rstrip()
