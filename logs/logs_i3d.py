#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# title           : logs_i3d.py
# description     : Retrieves the past two days of Miscreated chat and damage
#                   logs from i3D's control panel. Keep in mind that if i3D
#                   changes their log retrieval interface that this class will
#                   likely break.
#                   This script may be used idependently from the command line.
# author          : Chris Snow - (aka Spafbi)
# python_version  : 3.9.1
# ===================================================
from datetime import datetime, timedelta
from glob import glob
from pytz import timezone
import click
import os
import requests


class i3D_Server:
    # username = ""  # your i3d email
    # password = ""  # i3d password
    # server_id = "753403"  # i3d server ID
    # tz = 'America/Chicago'  # timezone

    def __init__(self, **kwargs):
        password = kwargs.get('password', None)
        username = kwargs.get('username', None)
        self.error = None
        self.local_dir = kwargs.get('local_dir', '.')
        self.remote_tz = timezone(kwargs.get('tz', 'UTC'))
        self.srvr = kwargs.get('server_id', None)
        self.verbose = kwargs.get('verbose', False)
        verbose = self.verbose

        if None in (username, password, self.srvr):
            self.error = 'missing credentials'
            if verbose:
                print('Error: {}'.format(self.error))
            return False
        else:
            self.req_session = requests.Session()
            self.req_session.post('https://customer.i3d.net/login/',
                                  data={"cpusername": username,
                                        "cppassword": password})
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)

    def check_local_dir_files(self, **kwargs):
        directory = kwargs.get("directory", None)
        today = kwargs.get("today", None)
        verbose = kwargs.get("verbose", False)
        yesterday = kwargs.get("yesterday", None)

        if bool(glob('{0}/*{1}.txt*'.format(directory, today))):
            yesterday = '9999-99-99'
            if verbose:
                print("Files with the current date exist.")
        else:
            if verbose:
                print("No files with the current date exist.")
                print("Assuming we need to grab yesterday's files.")

        return yesterday

    def fetch_file(self, url, filename):
        with open(filename, 'w') as f:
            headers = {}
            pos = f.tell()
            if pos:
                headers['Range'] = f'bytes={pos}-'
            response = self.req_session.get(url, headers=headers, stream=True)
            f.write(response.text)

    def get_logs(self):
        """
        This method only grabs the last two days of log files.
        """
        verbose = self.verbose
        today = (
            datetime.utcnow().replace(tzinfo=self.remote_tz) .
            strftime("%Y-%m-%d")
        )
        yesterday = (
            (
             datetime.utcnow().
             replace(tzinfo=self.remote_tz) - timedelta(days=1)
            ).strftime("%Y-%m-%d")
        )

        local_dir_check_args = {
            "directory": self.local_dir,
            "today": today,
            "verbose": verbose,
            "yesterday": yesterday
        }

        yesterday = self.check_local_dir_files(**local_dir_check_args)

        logs = self.req_session.post("https://customer.i3d.net/controlpanel"
                                     "/gaming/game/libs/callback-content.php",
                                     data={"action": "LOGS", "id": self.srvr})

        file_ids = dict()
        key = None
        value = None

        for line in logs.text.split("\n"):
            damage_log = line.find("<td>damagelog_") >= 0
            chat_log = line.find("<td>chatlog_") >= 0
            on_click = line.find("<td><a onclick") >= 0
            if verbose and (damage_log or chat_log or on_click):
                print('damage_log: {}, chat_log: {}, on_click: {}'.format(
                    damage_log, chat_log, on_click))
            if damage_log or chat_log or on_click:
                trash, schtuff = line.strip().split("<td>", 1)
                schtuff = schtuff.strip().replace('</td>', '')
            else:
                continue

            if verbose:
                print('Schtuff: {}'.format(schtuff))

            if "damagelog_" in schtuff or "chatlog_" in schtuff:
                key = schtuff
            elif line.find("<a onclick") >= 0:
                value = schtuff.split("'")[3]
            else:
                continue

            if verbose:
                print('Key: {}, Value: {}'.format(key, value))

            if key is not None and value is not None:
                if today in key or yesterday in key:
                    if self.verbose:
                        print(key, value)
                    file_ids[key] = value
                key = None
                value = None

        for key, value in file_ids.items():
            if verbose:
                print('Log file: {}, Download ID: {}'.format(key, value))

            url = ("https://customer.i3d.net/controlpanel/gaming/game"
                   "/gameserver-log-download.php?log=1"
                   "&server={0}&file={1}".format(self.srvr, value))
            filename = "{}/{}".format(self.local_dir, key)
            self.fetch_file(url, filename)


@click.command()
@click.option('-p', '--password',
              help='FTP password',
              required=True,
              type=str)
@click.option('-u', '--username',
              help='FTP username',
              required=True,
              type=str)
@click.option('-l', '--local_dir',
              default='.',
              help='local log directory',
              required=False,
              type=str)
@click.option('-s', '--server_id',
              help='i3D game server ID',
              required=True,
              type=str)
@click.option('-t', '--timezone',
              default='UTC',
              help='remote server timezone',
              required=False,
              type=str)
@click.option('-v', '--verbose', help='verbose output', is_flag=True)
def main(password, username, local_dir, server_id, timezone, verbose):
    obj_vars = {"password": password,
                "username": username,
                "local_dir": local_dir,
                "server_id": server_id,
                "timezone": timezone,
                "verbose": verbose}

    i3D_Server(**obj_vars).get_logs()


if __name__ == '__main__':
    main()
