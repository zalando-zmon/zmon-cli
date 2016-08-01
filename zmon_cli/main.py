import requests

from clickclick import error

from zmon_cli.cmds import cli


def main():
    try:
        cli()
    except requests.HTTPError as e:
        error('HTTP ERROR: {}'.format(e))


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nStopped by user')
