# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import readline
import getpass
import sys
import cmd
import imp
import re
import os
import shlex

from . import restshlib

DEBUG = False

HELP_TEXT = '''Usage: command [<command-option>...]

Cliente commands:
  set <header|setting> <header-key> <header-value>
  unset <header|setting> <header-key>
  show <headers|settings>
  prompt <new-prompt>
  login <username>
  baseurl <host>
  help [<command>]

Rest actions:
  get <url>
  post <url> <data>
  put <url> <data>
  delete <url>
'''

class RestSH(cmd.Cmd, object):
    restshlib = None
    baseurl = "no-host"
    login = "no-user"
    prompt = ""
    cfg_prompt = "%(login)s@%(baseurl)s|restsh> "
    global_data = {}
    history_file = os.path.expanduser("~/.restsh-history")
    history_file_max_lines = 1000

    def __init__(self, *args, **kwargs):
        self.restshlib = restshlib.RestSHLib(global_data=self.global_data)
        self.prompt = self.cfg_prompt % {"login": self.login, "baseurl": self.baseurl}

        readline.read_history_file(self.history_file)
        readline.set_history_length(self.history_file_max_lines)
        super(RestSH, self).__init__(*args, **kwargs)

    def __del__(self):
        readline.write_history_file(self.history_file)

    def postcmd(self, stop, line):
        super(RestSH, self).postcmd(stop, line)
        self.prompt = self.cfg_prompt % {"login": self.login, "baseurl": self.baseurl}

    def _print_response(self, response):
        if self.restshlib.settings.get('print_request', "1") in ["1","yes","true"]:
            print("Request:")
            print("  url: {0}".format(response.request.full_url))
            print("  data: {0}".format(response.request.data))
            print("  headers:")

            for header in response.request.headers.iteritems():
                print("    {0}: {1}".format(header[0], header[1]))

        if self.restshlib.settings.get('print_body', "1") in ["1","yes","true"]:
            print("Response body:\n{0}".format(response.text))

        if self.restshlib.settings.get('print_headers', "1") in ["1","yes","true"]:
            print("Response headers:")
            for header in response.headers.iteritems():
                print("  {0}: {1}".format(header[0], header[1]))

        if self.restshlib.settings.get('print_status', "1") in ["1","yes","true"]:
            print("Status Code: {0}".format(response.status_code))

    def do_reload(self, params):
        imp.reload(restshlib)
        self.restshlib = restshlib.RestSHLib(global_data=self.global_data)

    def do_help(self, params):
        """
        Show help information. Example: help set
        """
        
        if params:
            super(RestSH, self).do_help(params)
        else:
            print(HELP_TEXT)

    def do_quit(self, params):
        '''Quit restsh'''
        sys.exit()

    def do_EOF(self, params):
        '''Quit restsh'''
        sys.exit()

    def do_setenv(self, params):
        args = shlex.split(params)
        if len(args) % 2 != 0:
            raise ValueError("Invalid parameters")

        while True:
            key, value = args[:2]
            args = args[2:]

            self.global_data[key] = value

            if len(args) == 0:
                break

    def do_delenv(self, params):
        args = shlex.split(params)

        if len(args) < 1:
            raise ValueError("Invalid parameters")

        for arg in args:
            if arg in self.global_data:
                del self.global_data[arg]

    def do_set(self, params):
        """
        Set headers and settings variables. Example: set settings auth_method digest
        """

        args = shlex.split(params)
        if len(args) != 3:
            raise ValueError("Invalid number of parameters")
        else:
            (typ, key, value) = args

        if typ == "header":
            self.restshlib.set_header(key, value)
        elif typ == "setting":
            self.restshlib.set_setting(key, value)
        else:
            raise ValueError("Invalid type of variables")

    def do_unset(self, params):
        '''Unset headers and settings variables. Example: unset settings auth_method'''
        args = shlex.split(params)
        if len(args) != 2:
            raise ValueError("Invalid number of parameters")
        else:
            (typ, key) = args
        if typ == "header":
            self.restshlib.unset_header(key)
        elif typ == "setting":
            self.restshlib.unset_setting(key)
        else:
            raise ValueError("Invalid type of variables")

    def do_show(self, params):
        '''Show headers and settings variables. Example: show settings'''
        args = shlex.split(params)
        if len(args) != 1:
            raise ValueError("Invalid number of parameters")
        else:
            (typ,) = args
        if typ == "headers":
            for header in self.restshlib.headers.iteritems():
                print("{0}: {1}".format(header[0], header[1]))
        elif typ == "settings":
            for setting in self.restshlib.settings.iteritems():
                print("{0}: {1}".format(setting[0], setting[1]))
        else:
            raise ValueError("Invalid type of variables")

    def do_baseurl(self, params):
        '''Set the base url for all requests. Example: baseurl http://testserver.com/api'''
        args = shlex.split(params)
        if len(args) != 1:
            raise ValueError("Invalid number of parameters")
        else:
            (baseurl,) = args

        self.baseurl = baseurl
        self.restshlib.set_base_url(self.baseurl)

    def do_login(self, params):
        '''Set HTTP AUTH login username and password. Example: login myusername'''
        args = shlex.split(params)
        if len(args) != 1:
            raise ValueError("Invalid number of parameters")
        else:
            (username,) = args
        self.login = username
        password = getpass.getpass('Password: ')
        self.restshlib.set_auth(self.login, password, self.restshlib.settings.get('auth_method', 'basic'))

    def do_get(self, params):
        """
        Send get request. Example: get /url
        """

        try:
            url, data = re.split(r'\s+', params, 1)
        except ValueError:
            url, data = params, {}

        response = self.restshlib.get(url, data)
        self._print_response(response)

    def do_post(self, params):
        """
        Send post request. Example: post /url key=value test=test
        """
        
        try:
            url, data = re.split(r'\s+', params, 1)
        except ValueError:
            url, data = params, {}

        response = self.restshlib.post(url, data)
        self._print_response(response)

    def do_put(self, params):
        """
        Send put request. Example: put /url key=value test=test
        """

        try:
            url, data = re.split(r'\s+', params, 1)
        except ValueError:
            url, data = params, {}

        response = self.restshlib.put(url, data)
        self._print_response(response)

    def do_delete(self, params):
        """
        Send delete request. Example: delete /url
        """

        try:
            url, data = re.split(r'\s+', params, 1)
        except ValueError:
            url, data = params, {}

        response = self.restshlib.delete(url, data)
        self._print_response(response)

    def do_prompt(self, params):
        '''Change restsh prompt. Example: prompt "restsh> "'''
        args = shlex.split(params)
        if len(args) != 1:
            raise ValueError("Invalid number of parameters")
        else:
            (prompt,) = args
        self.cfg_prompt = prompt
