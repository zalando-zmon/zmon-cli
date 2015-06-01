import click


def highlight(msg, **kwargs):
    click.secho(' {}'.format(msg), fg='cyan', nl=False, bold=True, **kwargs)
