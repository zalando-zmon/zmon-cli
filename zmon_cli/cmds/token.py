from datetime import datetime

import click

from clickclick import AliasedGroup, Action, ok

from zmon_cli.cmds.command import cli, get_client, yaml_output_option, pretty_json
from zmon_cli.output import Output


########################################################################################################################
# TOKENS
########################################################################################################################

@cli.group('onetime-tokens', cls=AliasedGroup)
@click.pass_obj
def tv_tokens(obj):
    """Manage onetime tokens for Monitors/View only login"""
    pass


@tv_tokens.command('get')
@click.pass_obj
def get_tv_token(obj):
    """Retrieve a new token"""
    client = get_client(obj.config)

    with Action('Retrieving new one-time token ...', nl=True):
        token = client.get_onetime_token()
        ok(client.token_login_url(token.strip('"')))


@tv_tokens.command('list')
@click.pass_obj
@yaml_output_option
@pretty_json
def list_tv_token(obj, output, pretty):
    """List onetime tokens for your user"""
    client = get_client(obj.config)

    with Output('Retrieving onetime tokens ...', nl=True, output=output, pretty_json=pretty) as act:
        tokens = client.list_onetime_tokens()

        for t in tokens:
            t['created'] = datetime.fromtimestamp(t['created'] / 1000)
            if t['bound_at'] is not None:
                t['bound_at'] = datetime.fromtimestamp(t['bound_at'] / 1000)

        act.echo(tokens)
