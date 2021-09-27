#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# title           : rcon.py
# description     : Sends commands to Miscreated RCON
# author          : Chris Snow - (aka Spafbi)
# python_version  : 3.9.2
# ===================================================
import hashlib
import logging
import socket
import time
import xmlrpc.client


class MiscreatedRCON:
    """
    A simple class which may be used for sending commands to a Miscreated RCON.
    I've tried to allow for single commands, multiple commands, and automatic
    retries.
    """

    def __init__(self, **kwargs):
        """
        Args:
            host (str): a FQDN or IP address
            port (int): The RCON listener port
            password (str): The RCON password
        Returns:
            None: But only when one of the required dictionary values is
                  missing
        """
        logging.debug("Initializing MiscreatedRCON object")

        # assign class variables based on
        self.ip = kwargs.get('host', False)
        self.port = kwargs.get('port', False)
        self.password = kwargs.get('password', False)
        self.server = None
        logging.debug(kwargs)
        logging.debug(f"Passed values: host={self.ip}, port={self.port}, " \
                      f"password={self.password}")

        """
        We can't connect to the server if any of these are false, so return
        None
        """
        if False in (self.ip, self.port, self.password):
            logging.critical("One or more required RCON values was not passed:")
            if not self.ip:
                logging.critical("    > host")
            if not self.port:
                logging.critical("    > port")
            if not self.password:
                logging.critical("    > password")
            return None

        # assemble the RCON server URL
        server_url = f'http://{self.ip}:{int(self.port)}/rpc2'
        logging.debug(f'server_url: {server_url}')

        # start the connection
        self.server = xmlrpc.client.ServerProxy(
            server_url, transport=SpecialTransport(), allow_none=True)

    def challenge_rcon(self, **kwargs):
        """
        Authenticate with a Miscreated RCON
        Args:
            retry (int): The number of iterations to attempt
        Returns:
            None: If we couldn't authenticate with the server at all - usually
                  due to a bad password.
            True: If authentication is successful
            Fale: If authentication failed for some other reason - timeout or
                  the RCON interface is already in use elsewhere.
        """
        # attempt to successfully challenge the server
        # make attemps up to 'retry' value
        retry = kwargs.get('retry', 10)
        retry_max = retry
        authentication = None
        while retry > 0:
            """
            attempt to authenticate with the uptime and the password md5
            with : between
            """
            this_retry = retry_max+1 - retry
            logging.debug(f"Challenge attempt: {this_retry}")
            socket.setdefaulttimeout(5)
            try:
                challenge = self.server.challenge()
                if isinstance(float(challenge), float):
                    retry = 0
            except:
                this_sleep_time=0.25
                logging.debug(f"Challenge failed: sleeping {this_sleep_time} seconds")
                challenge = None
                # add a small wait before retry in case RCON is busy
                time.sleep(this_sleep_time)
            socket.setdefaulttimeout(None)
            authentication = f"{challenge}:{self.password}"
            logging.debug(f"authentication: {authentication}")
            retry -= 1

        # check to see if we are authorized
        if None in (authentication, challenge):
            logging.debug("failed to authorize")
            return None

        # Check for the proper return from the authentication attempt
        md5 = hashlib.md5(authentication.encode('utf-8')).hexdigest()
        logging.debug(f"authentication_md5: {md5}")

        # This forces a 5 second timeout for socket connections
        socket.setdefaulttimeout(5)
        this_auth = self.server.authenticate(md5)
        # Restore default timeout for socket connections
        socket.setdefaulttimeout(None)

        if this_auth == 'authorized':
            logging.debug("Successful challenge and authorization")
            return True

        if 'Illegal Command' not in this_auth:
            '''The following message is displayed on the command line, but
                is not otherwise handled'''
            this_message = f'Authentication failed: {this_auth}'
            logging.debug(this_message)
            print(this_message)
        return False

    def do_authentication(self, retry=5):
        """
        Authenticate by challenging RCON
        Args:
            retry (int): number of attempts to make
        Returns:
            challenge (object): challenge object
            success (bool): whether or not the challenge was successful
        """
        try:
            logging.debug("Attempting RCON challenge")
            challenge = self.challenge_rcon(retry=retry)
            return challenge, True
        except OSError as e_error:
            if 'timed out' in str(e_error):
                return False, False

    def exec_cmd(self, cmd):
        """
        Execute a command having parameters
        Args:
            cmd (str): A command to be executed
        Returns:
            cmd_result (str): Value returned from RCON
            success (bool): whether or not the command was successful
        """
        try:
            # This forces a 5 second timeout for socket connections
            socket.setdefaulttimeout(5)
            cmd_result = self.server.__getattr__(cmd)().strip()

            # Restore default timeout for socket connections
            socket.setdefaulttimeout(None)
            return cmd_result, True
        except OSError as except_e:
            logging.debug(except_e)
            return False, False

    def exec_cmd_params(self, cmd, params):
        """
        Execute a command having parameters
        Args:
            cmd (str): A command to be executed
            params (int): Parameters for the command
        Returns:
            cmd_result (str): Value returned from RCON
            success (bool): whether or not the command was successful
        """
        try:
            # This forces a 5 second timeout for socket connections
            socket.setdefaulttimeout(5)
            cmd_result = self.server.__getattr__(cmd)(params).strip()

            # Restore default timeout for socket connections
            socket.setdefaulttimeout(None)
            return cmd_result, True
        except OSError as except_e:
            # I've commented out the following line... I think that we want to
            # "return False, False" regardless of whether or not the cause is a
            # timeout.
            # if 'timed out' in str(except_e):
            logging.debug(except_e)
            return False, False

    def multi_rcon(self, **kwargs):
        """
        Send multiple commands to a Miscreated RCON server.
        Args:
            commands (list): A list of commands to be executed
            retry (int): The number of iterations to attempt until successful
        Returns:
            dictionary:
                success (bool): Only false if the commands passed is not a list
                returned (dict): Commands as keys; results as values.
        """
        commands = kwargs.get('commands', None)
        retry = kwargs.get('retry', 10)

        result = dict()
        result['success'] = None
        result['returned'] = dict()
        # test to make sure 'commands' is a list
        if type(commands) is not list:
            result['returned'][0] = 'List not passed for commands'
            result['success'] = False
            return result
        for command in commands:
            result['returned'][command] = self.send_command(command=command,
                                                            retry=retry)
            result['success'] = True
        return result

    def send_command(self, **kwargs):
        """
        Send a command to a Miscreated RCON server
        Args:
            command (str): A command to be executed
            retry (int): The number of iterations to attempt until successful
        Returns:
            dictionary:
                success (bool): Whether or not the command was sent
                                successfully
                returned (str): Value returned from RCON
        """
        command = kwargs.get('command', None)
        retry = kwargs.get('retry', 10)

        status = dict()

        if command is None:  # Return a status if there's no command
            status['success'] = False
            status['returned'] = 'No command was passed'
            return status

        cmd_list = command.split(' ')
        cmd = cmd_list.pop(0)  # first thing sent is always a command
        # we popped out the 0 before so the rest are the command params
        params = ' '.join(cmd_list) if cmd_list else ''

        # set some default values used for testing
        auth_attempt = 0
        authenticated = False
        challenge = None
        cmd_result = None
        status['returned'] = dict()
        status['success'] = None
        success = False

        # Okay... Let's assume we're already authenticated and try executing
        # the RCON commands without first authenticating.
        if params:  # Call the appropriate method is the command has spaces
            cmd_result, authenticated = self.exec_cmd_params(cmd, params)
        else:  # Call the appropriate method is the command has no spaces
            cmd_result, authenticated = self.exec_cmd(cmd)

        # this tests to see if we got a challenge error
        success = self.is_cmd_success(cmd_result)

        # this test the result known command errors
        status['success'] = self.is_bad_results_11(cmd_result, success)
        status['returned'] = cmd_result  # the rcon output is in here

        invalid_command = True if status['returned'].strip() == "Illegal Command" else False

        if status['success'] and not invalid_command:
            return status

        # reset default values used for testing
        authenticated = False
        cmd_result = None
        status['returned'] = dict()
        status['success'] = None
        success = False
        
        # Okay - so we need to try again, but authenticate this time.
        # Try to execute the command until it's successful or exceeds attempts
        while not success:
            while not authenticated:  # Time to authenticate (maybe again)
                challenge, authenticated = self.do_authentication(retry)
                if challenge is False:  # what to do if we failed to auth
                    authenticated = False
                    auth_attempt += 1
                    if auth_attempt > 3:  # Try three times then die
                        status['success'] = False
                        status['returned'] = 'Could not authenticate with RCON'
                        return status
                    time.sleep(0.25)

            if params:  # Call the appropriate method is the command has spaces
                cmd_result, authenticated = self.exec_cmd_params(cmd, params)
            else:  # Call the appropriate method is the command has no spaces
                cmd_result, authenticated = self.exec_cmd(cmd)

            # this tests to see if we got a challenge error
            success = self.is_cmd_success(cmd_result)

        # this test the result known command errors
        status['success'] = self.is_bad_results_11(cmd_result, success)
        status['returned'] = cmd_result  # the rcon output is in here

        return status

    def is_bad_results_11(self, value, success):
        if value and value is not None:
            value = value[:11]
        # the passed value should contain only the first 11 characters of the
        # rcon result
        # list containing known bad strings
        bad_results_11 = ('[Whitelist]')
        if not len(value):  # Sometimes RCON returns nothing, and that's okay
            return success
        if value in bad_results_11:  # If a match is found return False
            return False
        return success

    def is_cmd_success(self, result):
        if result in ('[Whitelist] Invalid command: challenge', None):
            return False
        return True


class SpecialTransport(xmlrpc.client.Transport):
    """
    Summary: XMLRPC client transport used for chatting with a Miscreated RCON.

    Description: This is a very simple client for communicating with a
                 Miscreated server using RCON.
    """

    user_agent = 'spafbi-misrcon'

    def send_content(self, connection, request_body):
        """
        Summary: Method used to send content.

        Description: This method sends content to an Miscreated RCON.
        """
        connection.putheader("Connection", "keep-alive")
        connection.putheader("Content-Type", "text/xml")
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)


def main():
    """
    Summary: Default method if this modules is run as __main__.
    """
    import argparse
    from os.path import basename

    # Just grabbing this script's filename
    prog = basename(__file__)
    description = f"""Spafbi's RCON module and command-line utility:\r
                     {prog} may be used as either a Python 3 module, or as a
                     standalone command-line utility."""

    # Set up argparse to help people use this as a CLI utility
    parser = argparse.ArgumentParser(prog=prog, description=description)

    parser.add_argument('-s', '--server', type=str, required=False,
                        help="""Either a FQDN or IP address of the game server
                             - defaults to localhost""", default="127.0.0.1")
    parser.add_argument('-r', '--rcon-port', type=int, required=False,
                        help="""RCON port: Will be overriden if a game port is
                             specified - defaults to 64094""", default=64094)
    parser.add_argument('-g', '--game-port', type=int, required=False,
                        help="""Game port: Optional - If specified the RCON
                                port will be calculated from this value -
                                defaults to 64090""", default=64090)
    parser.add_argument('-p', '--password', type=str, required=True,
                        help="""The RCON password : This is a required
                                argumment""")
    parser.add_argument('-c', '--command', metavar='"COMMAND"', type=str,
                        required=False,
                        help="""An RCON command: Commands containing spaces or
                                special characters will need to be in quotes or
                                otherwise properly escaped.
                                Server status will be returned if no command is
                                specified.""", default="status")
    parser.add_argument('-v', '--verbose', action='store_true', required=False,
                        help="""Verbose logging""")

    # Parse our arguments!
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    '''If a non-default game port is specified then calculate the proper RCON
       listener port'''
    if args.game_port == 64090:
        port = args.rcon_port
    else:
        port = args.game_port + 4

    # Set up RCON class
    this_rcon = MiscreatedRCON(host=args.server,
                               password=args.password,
                               port=port)
    try:
        result = this_rcon.send_command(command=args.command)
    except:
        result = {"success": False,
                  "returned": None}

    if result['success']:
        if len(result['returned']):
            print(result['returned'])
        else:
            print('<empty result - ok>')
        exit(0)

    print("<Oops - something went wrong>")
    exit(1)


if __name__ == '__main__':
    main()
