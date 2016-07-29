import click

from clickclick import Action, error, warning

from zmon_cli.cmds.cli import cli


@cli.group(invoke_without_command=True)
@click.pass_context
def groups(ctx):
    """Manage contact groups"""
    if not ctx.invoked_subcommand:
        with Action('Retrieving groups ...'):
            groups = ctx.obj.client.get_groups()

            if len(groups) == 0:
                warning('No groups found!')

            for g in groups:
                print('Name: {} Id: {}'.format(g['name'], g['id']))

                print('\tMembers:')
                for m in g['members']:
                    member = ctx.obj.client.get_member(m)
                    print('\t\t{} {} {}'.format(member['name'], member['email'], member['phones']))

                print('\tActive:')
                for m in g['active']:
                    member = ctx.obj.client.get_member(m)
                    print('\t\t{} {} {}'.format(member['name'], member['email'], member['phones']))


@groups.command('switch')
@click.argument('group_name')
@click.argument('user_name')
@click.pass_context
def switch_active(ctx, group_name, user_name):
    with Action('Switching active user ...'):
        switched = ctx.obj.client.switch_active_user(group_name, user_name)
        if not switched:
            error('Failed to switch')


@cli.group()
@click.pass_context
def members(ctx):
    """Manage group membership"""
    pass


@members.command('add')
@click.argument('group_name')
@click.argument('user_name')
@click.pass_context
def member_add(ctx, group_name, user_name):
    with Action('Adding user ...'):
        added = ctx.obj.client.add_member(group_name, user_name)

        if not added:
            error('Failed to add member')


@members.command('remove')
@click.argument('group_name')
@click.argument('user_name')
@click.pass_context
def member_remove(ctx, group_name, user_name):
    with Action('Removing user ...'):
        removed = ctx.obj.client.remove_member(group_name, user_name)

        if not removed:
            error('Failed to remove member')


@members.command('add-phone')
@click.argument('member_email')
@click.argument('phone_nr')
@click.pass_context
def add_phone(ctx, member_email, phone_nr):
    with Action('Adding phone ...'):
        added = ctx.obj.client.add_phone(member_email, phone_nr)

        if not added:
            error('Failed to add phone')


@members.command('remove-phone')
@click.argument('member_email')
@click.argument('phone_nr')
@click.pass_context
def remove_phone(ctx, member_email, phone_nr):
    with Action('Removing phone number ...'):
        removed = ctx.obj.client.remove_phone(member_email, phone_nr)

        if not removed:
            error('Failed to remove phone')


@members.command('change-name')
@click.argument('member_email')
@click.argument('member_name')
@click.pass_context
def set_name(ctx, member_email, member_name):
    with Action('Changing user name ...'):
        ctx.obj.client.set_name(member_email, member_name)
