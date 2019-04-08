# -*- coding: utf-8
# settings: Define Settings, main class handling GlobaLeeaks runtime settings
# ******
from __future__ import print_function

import getpass
import os
import platform
import re
import sys

# pylint: enable=no-name-in-module
from optparse import OptionParser

from globaleaks import __version__
from globaleaks.orm import make_db_uri, set_db_uri
from globaleaks.utils.singleton import Singleton

this_directory = os.path.dirname(__file__)

possible_client_paths = [
    '/var/globaleaks/client',
    '/usr/share/globaleaks/client/',
    os.path.abspath(os.path.join(this_directory, '../../client/build/')),
    os.path.abspath(os.path.join(this_directory, '../../client/app/'))
]


external_counted_events = {
    'new_submission': 0,
    'finalized_submission': 0,
    'anon_requests': 0,
    'file_uploaded': 0,
}


class SettingsClass(object):
    __metaclass__ = Singleton

    def __init__(self):
        # command line parsing utils
        self.parser = OptionParser()
        self.cmdline_options = None

        # version
        self.version_string = __version__

        # testing
        # This variable is to be able to hook/bypass code when unit-tests are run
        self.testing = False

        # daemonize the process
        self.nodaemon = False

        self.bind_address = '0.0.0.0'
        self.bind_remote_ports = [80, 443]
        self.bind_local_ports = [8082, 8083]

        self.db_type = 'sqlite'

        # debug defaults
        self.orm_debug = False

        # files and paths
        self.src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.backend_script = os.path.abspath(os.path.join(self.src_path, 'globaleaks/backend.py'))

        self.pid_path = '/var/run/globaleaks'
        self.working_path = '/var/globaleaks'

        # TODO(bug-fix-italian-style) why is this set to the 2nd entry in the possible
        # client paths...? please fix.
        self.client_path = '/usr/share/globaleaks/client'
        for path in possible_client_paths:
            if os.path.exists(path):
                self.client_path = path
                break

        self.authentication_lifetime = 3600

        self.accept_submissions = True

        # statistical, referred to latest period
        # and resetted by session_management sched
        self.failed_login_attempts = 0

        # static file rules
        self.staticfile_regexp = r'(.*)'
        self.staticfile_overwrite = False

        self.local_hosts = ['127.0.0.1', 'localhost']

        self.onionservice = None

        # Default request time uniform value
        self.side_channels_guard = 150

        # SOCKS default
        self.socks_host = "127.0.0.1"
        self.socks_port = 9050

        self.key_bits = 2048
        self.csr_sign_bits = 512

        self.notification_limit = 30
        self.jobs_operation_limit = 20

        self.user = getpass.getuser()
        self.group = getpass.getuser()

        # Initialize to None since Windows doesn't have a direct 1:1 concept
        # of uid/gid.
        self.uid = None
        self.gid = None

        if platform.system() != 'Windows':
            self.uid = os.getuid()
            self.gid = os.getgid()

        self.devel_mode = False
        self.disable_swap = False

        # Number of failed login enough to generate an alarm
        self.failed_login_alarm = 5

        # Number of minutes in which a user is prevented to login in case of triggered alarm
        self.failed_login_block_time = 5

        # Limit for log sizes and number of log files
        # https://github.com/globaleaks/GlobaLeaks/issues/1578
        self.log_size = 10000000  # 10MB
        self.log_file_size = 1000000  # 1MB
        self.num_log_files = self.log_size / self.log_file_size

        self.AES_key_id_regexp = u'[A-Za-z0-9]{16}'
        self.AES_file_regexp = r'(.*)\.aes'
        self.AES_file_regexp_comp = re.compile(self.AES_file_regexp)
        self.AES_keyfile_prefix = "aeskey-"

        self.exceptions_email_hourly_limit = 20

        self.enable_input_length_checks = True

        self.mail_timeout = 15  # seconds
        self.mail_attempts_limit = 3  # per mail limit

        self.acme_directory_url = 'https://acme-v02.api.letsencrypt.org/directory'

        self.enable_api_cache = True

        self.eval_paths()

    def eval_paths(self):
        self.config_file_path = '/etc/globaleaks'
        self.pidfile_path = os.path.join(self.pid_path, 'globaleaks.pid')
        self.files_path = os.path.abspath(os.path.join(self.working_path, 'files'))

        self.log_path = os.path.abspath(os.path.join(self.working_path, 'log'))
        self.attachments_path = os.path.abspath(os.path.join(self.working_path, 'attachments'))
        self.tmp_path = os.path.abspath(os.path.join(self.working_path, 'tmp'))
        self.backup_path = os.path.abspath(os.path.join(self.working_path, 'backups'))
        self.static_db_source = os.path.abspath(os.path.join(self.src_path, 'globaleaks', 'db'))

        self.db_schema = os.path.join(self.static_db_source, 'sqlite.sql')
        self.db_file_path = os.path.abspath(os.path.join(self.working_path, 'globaleaks.db'))

        self.logfile = os.path.abspath(os.path.join(self.log_path, 'globaleaks.log'))
        self.accesslogfile = os.path.abspath(os.path.join(self.log_path, "access.log"))

        # If we see that there is a custom build of GLClient, use that one.
        custom_client_path = '/var/globaleaks/client'
        if os.path.exists(custom_client_path):
            self.client_path = custom_client_path

        self.appdata_file = os.path.join(self.client_path, 'data/appdata.json')
        self.questionnaires_path = os.path.join(self.client_path, 'data/questionnaires')
        self.questions_path = os.path.join(self.client_path, 'data/questions')
        self.field_attrs_file = os.path.join(self.client_path, 'data/field_attrs.json')

        set_db_uri(make_db_uri(self.db_file_path))

    def set_devel_mode(self):
        self.devel_mode = True

        self.key_bits = 1024

        self.acme_directory_url = 'https://acme-staging-v02.api.letsencrypt.org/directory'

        self.pid_path = os.path.join(self.src_path, 'workingdir')
        self.working_path = os.path.join(self.src_path, 'workingdir')

    def load_cmdline_options(self):
        self.nodaemon = self.cmdline_options.nodaemon

        if self.cmdline_options.disable_swap:
            self.disable_swap = True

        self.bind_address = self.cmdline_options.ip

        self.socks_host = self.cmdline_options.socks_host

        if not self.validate_port(self.cmdline_options.socks_port):
            sys.exit(1)

        self.socks_port = self.cmdline_options.socks_port

        if platform.system() != 'Windows':
            if (self.cmdline_options.user and self.cmdline_options.group is None) or \
               (self.cmdline_options.group and self.cmdline_options.user is None):
                self.print_msg("Error: missing user or group option")
                sys.exit(1)

            if self.cmdline_options.user and self.cmdline_options.group:
                import grp
                import pwd

                self.user = self.cmdline_options.user
                self.group = self.cmdline_options.group

                self.uid = pwd.getpwnam(self.cmdline_options.user).pw_uid
                self.gid = grp.getgrnam(self.cmdline_options.group).gr_gid

        if self.cmdline_options.devel_mode:
            self.set_devel_mode()

        self.orm_debug = self.cmdline_options.orm_debug

        if self.cmdline_options.working_path:
            self.working_path = self.cmdline_options.working_path

        if self.cmdline_options.client_path:
            self.client_path = os.path.abspath(os.path.join(self.src_path, self.cmdline_options.client_path))

        self.eval_paths()

        if self.nodaemon:
            self.print_msg("Going in background; log available at %s" % Settings.logfile)

        # special evaluation of client directory:
        indexfile = os.path.join(self.client_path, 'index.html')
        if os.path.isfile(indexfile):
            self.print_msg("Serving the client from directory: %s" % self.client_path)
        else:
            self.print_msg("Unable to find a directory to load the client from")
            sys.exit(1)

    def validate_port(self, inquiry_port):
        if inquiry_port <= 0 or inquiry_port > 65535:
            self.print_msg("Invalid port number ( > than 65535 can't work! )")
            return False

        return True

    def print_msg(self, *args):
        if not self.testing:
            print(*args)


# Settings is a singleton class exported once
Settings = SettingsClass()
