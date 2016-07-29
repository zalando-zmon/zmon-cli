from datetime import datetime

import click

from clickclick import AliasedGroup, Action

from zmon_cli.cmds.cli import cli
from zmon_cli.output import dump_yaml


########################################################################################################################
# TOKENS
########################################################################################################################

@cli.group('onetime-tokens', cls=AliasedGroup)
@click.pass_context
def tv_tokens(ctx):
    """Manage onetime tokens for TVs/View only login"""
    pass


@tv_tokens.command('get')
@click.pass_context
def get_tv_token(ctx):
    """Retrieve a new token"""
    with Action('Retrieving new one-time token ...'):
        token = ctx.obj.client.get_tv_token()
        print(token)


@tv_tokens.command('list')
@click.pass_context
def list_tv_token(ctx):
    """List onetime tokens for your user"""
    with Action('Retrieving onetime tokens ...'):
        tokens = ctx.obj.client.list_tv_tokens()

        for t in tokens:
            t['created'] = datetime.fromtimestamp(t['created'] / 1000)
            if t['bound_at'] is not None:
                t['bound_at'] = datetime.fromtimestamp(t['bound_at'] / 1000)

        print(dump_yaml(tokens))
