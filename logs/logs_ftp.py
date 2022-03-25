#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# title           : logs_ftp.py
# description     : Retrieves the past two days of Miscreated logs using FTP
#                   This script may be used idependently from the command line.
# author          : Chris Snow - (aka Spafbi)
# python_version  : 3.9.1
# ===================================================
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path
from pytz import timezone
import click
import ftplib
import logging
import os
import ssl
import pytz


class ImplicitFTP_TLS(ftplib.FTP_TLS):
    """FTP_TLS subclass that automatically wraps sockets in SSL to support implicit FTPS."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sock = None

    @property
    def sock(self):
        """Return the socket."""
        return self._sock

    @sock.setter
    def sock(self, value):
        """When modifying the socket, ensure that it is ssl wrapped."""
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._sock = value


class MyFTP_TLS(ftplib.FTP_TLS):
    """Explicit FTPS, with shared TLS session"""
    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn,
                                            server_hostname=self.host,
                                            session=self.sock.session)
        return conn, size

class FTPServer:
    def __init__(self, **kwargs):
        self.host = kwargs.get('host', False)
        self.local_dir = Path(kwargs.get('local_dir', '.'))
        self.local_dir = Path(kwargs.get('local_dir', '.'))
        self.password = kwargs.get('password', False)
        self.port = kwargs.get('port', 21)
        self.remote_dir = kwargs.get('remote_dir', False)
        self.remote_tz = timezone(kwargs.get('tz', 'UTC'))
        self.use_tls = kwargs.get('use_tls', False) # Values: False, implicit FTPS, explicit FTPS
        self.username = kwargs.get('username', False)
        self.verbose = kwargs.get('verbose', False)

        if self.use_tls == "explicit":
            logging.debug('Using explicit TLS')
            self.ftp = MyFTP_TLS()
        elif self.use_tls == "implicit":
            logging.debug('Using implicit TLS')
            self.ftp = ImplicitFTP_TLS()
        else:
            logging.debug('NOT using TLS')
            self.ftp = ftplib.FTP()
            
    def authenticate_and_cd(self):
        if not self.min_requirement_check():
            return False

        try:
            self.ftp.connect(host=self.host, port=self.port)
        except ftplib.all_errors as e:
            logging.info('Could not establish connection with the target FTP server')
            logging.debug(e)
            return False

        try:
            self.ftp.login(user=self.username, passwd=self.password)
            if self.use_tls:
                self.ftp.prot_p()
            if self.use_tls == "explicit":
                self.ftp.set_pasv(True)
        except ftplib.all_errors as e:
            logging.info('FTP authentication failure')
            logging.debug(e)
            return False

        if self.remote_dir:
            return self.change_remote_directory()

        return True

    def change_remote_directory(self):
        try:
            self.ftp.cwd(self.remote_dir)
        except ftplib.all_errors as e:
            logging.info('Could not change remote directory')
            logging.debug(e)
            return False

        return True

    def get_file(self, **kwargs):
        localfilename = kwargs.get('localfilename', None)
        logging.debug(f'localfilename: {localfilename}')
        remotefilename = kwargs.get('remotefilename', None)
        logging.debug(f'remotefilename: {remotefilename}')
        resume = kwargs.get('resume', True)

        if None in (remotefilename, localfilename):
            return False

        if os.path.isfile(localfilename):
            logging.debug('Local file exists - resuming...')

        if resume:
            localfile = open(localfilename, 'ab')
            resume_from = os.path.getsize(localfilename)
        else:
            localfile = open(localfilename, 'w')
            resume_from = 0

        try:
            self.ftp.retrbinary('RETR ' + remotefilename,
                            localfile.write, 1024, resume_from)
        except ftplib.all_errors as e:
            logging.debug('Could not retrieve remote file')
            logging.debug(e)
        
        localfile.close()

    def get_logs(self):
        """
        This method only grabs the last two days of log files.
        """
        local_dir = self.local_dir
        remote_timezone = self.remote_tz
        IST = pytz.timezone(f'{remote_timezone}')
        this_now = datetime.now(IST)
        today = this_now.strftime("%Y-%m-%d")
        yesterday = (
            (
                this_now.replace(tzinfo=remote_timezone) - timedelta(days=1)
            ).strftime("%Y-%m-%d")
        )

        if bool(glob(f'{local_dir}/*{today}.txt*')):
            logging.debug("Files with the current date exist")
            yesterday = '9999-99-99'
        else:
            logging.debug("No files with the current date exist")
            logging.debug("Assuming we need to grab yesterday's files")

        ls = []
        
        try:
            logging.debug("Attempting to list remote path...")
            ls = self.ftp.nlst()
            # self.ftp.retrlines('LIST', ls.append) // Old method for getting file list
        except ftplib.all_errors as e:
            logging.debug(e)
        
        logging.debug(f'ls: {ls}')
        
        for f in ls:
            if today in f or yesterday in f:
                if "chatlog" in f:
                    pos = f.find("chatlog")
                elif "damagelog" in f:
                    pos = f.find("damagelog")
                filename = f"{f}\r"[pos:].strip()
                logging.debug(f"Grabbing: {filename}")
                if not os.path.exists(local_dir):
                    os.makedirs(local_dir)
                localfilename = f"{local_dir}/{filename}"
                self.get_file(remotefilename=filename,
                              localfilename=localfilename,
                              resume=True)
        try:
            self.ftp.quit()
        except ftplib.all_errors as e:
            logging.debug(e)

    def min_requirement_check(self):
        if False in (self.host, self.password, self.username):
            logging.debug('Value missing from required FTP credentials')
            if not self.host:
                logging.debug('host missing')
            if not self.password:
                logging.debug('password missing')
            if not self.username:
                logging.debug('username missing')
            return False
        return True


@click.command()
@click.option('-h', '--host',
              help='target FTP host or IP',
              required=True,
              type=str)
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
@click.option('-r', '--remote_dir',
              default='',
              help='remote log directory',
              required=False,
              type=str)
@click.option('-t', '--timezone',
              default='UTC',
              help='remote server timezone',
              required=False,
              type=str)
@click.option('--logfile',
              default=False,
              help='file to use for log output',
              required=False,
              type=str)
@click.option('-v', '--verbose', help='verbose output', is_flag=True)
def main(host,
         local_dir,
         logfile,
         password,
         remote_dir,
         timezone,
         username,
         verbose):
    
    # Set up logging
    if verbose and logfile:
        logging.basicConfig(filename=logfile,level=logging.DEBUG)
    elif not verbose and logfile:
        logging.basicConfig(filename=logfile,level=logging.INFO)
    elif verbose and not logfile:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug('Debug logging enabled')

    if not len(remote_dir):
        remote_dir = False
    obj_vars = {"host": host,
                "password": password,
                "username": username,
                "local_dir": local_dir,
                "remote_dir": remote_dir,
                "timezone": timezone,
                "verbose": verbose}

    logging.debug(f'obj_vars: {obj_vars}')

    this_server = FTPServer(**obj_vars)
    if this_server.authenticate_and_cd():
        this_server.get_logs()


if __name__ == '__main__':
    main()
