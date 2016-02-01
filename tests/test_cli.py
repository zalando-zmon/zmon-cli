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
        with open('config.yaml', 'w') as fd:
            yaml.dump({}, fd)
        result = runner.invoke(cli, ['-c', 'config.yaml', 'status'], catch_exceptions=False)
        assert 'foo' in result.output
        assert '12377' in result.output
        assert 'd ago' in result.output
