import click

from clickclick import Action

from zmon_cli.cmds.command import cli, get_client


@cli.group(invoke_without_command=True)
@click.pass_context
def groups(ctx):
    """Manage contact groups"""
    client = get_client(ctx.obj.config)

    if not ctx.invoked_subcommand:
        with Action('Retrieving groups ...', nl=True) as act:
            groups = client.get_groups()

            if len(groups) == 0:
                act.warning('No groups found!')

            for g in groups:
                print('Name: {} Id: {}'.format(g['name'], g['id']))

                print('\tMembers:')
                for m in g['members']:
                    member = client.get_member(m)
                    print('\t\t{} {} {}'.format(member['name'], member['email'], member['phones']))

                print('\tActive:')
                for m in g['active']:
                    member = client.get_member(m)
                    print('\t\t{} {} {}'.format(member['name'], member['email'], member['phones']))


@groups.command('switch')
@click.argument('group_name')
@click.argument('user_name')
@click.pass_obj
def switch_active(obj, group_name, user_name):
    client = get_client(obj.config)

    with Action('Switching active user ...') as act:
        switched = client.switch_active_user(group_name, user_name)
        if not switched:
            act.error('Failed to switch')


@cli.group()
@click.pass_obj
def members(obj):
    """Manage group membership"""
    pass


@members.command('add')
@click.argument('group_name')
@click.argument('user_name')
@click.pass_obj
def member_add(obj, group_name, user_name):
    client = get_client(obj.config)

    with Action('Adding user ...') as act:
        added = client.add_member(group_name, user_name)

        if not added:
            act.error('Failed to add member')


@members.command('remove')
@click.argument('group_name')
@click.argument('user_name')
@click.pass_obj
def member_remove(obj, group_name, user_name):
    client = get_client(obj.config)

    with Action('Removing user ...') as act:
        removed = client.remove_member(group_name, user_name)

        if not removed:
            act.error('Failed to remove member')


@members.command('add-phone')
@click.argument('member_email')
@click.argument('phone_nr')
@click.pass_obj
def add_phone(obj, member_email, phone_nr):
    client = get_client(obj.config)

    with Action('Adding phone ...') as act:
        added = client.add_phone(member_email, phone_nr)

        if not added:
            act.error('Failed to add phone')


@members.command('remove-phone')
@click.argument('member_email')
@click.argument('phone_nr')
@click.pass_obj
def remove_phone(obj, member_email, phone_nr):
    client = get_client(obj.config)

    with Action('Removing phone number ...') as act:
        removed = client.remove_phone(member_email, phone_nr)

        if not removed:
            act.error('Failed to remove phone')


@members.command('change-name')
@click.argument('member_email')
@click.argument('member_name')
@click.pass_obj
def set_name(obj, member_email, member_name):
    client = get_client(obj.config)

    with Action('Changing user name ...'):
        client.set_name(member_email, member_name)


@members.command('help')
@click.pass_context
def help(ctx):
    print(ctx.parent.get_help())
