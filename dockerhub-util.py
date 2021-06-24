#! /usr/bin/env python3

# -----------------------------------------------------------------------------
# dockerhub-util.py
# -----------------------------------------------------------------------------

import argparse
import json
import linecache
import logging
import os
import requests
import signal
import sys
import time
from datetime import date

__all__ = []
__version__ = "1.0.1"  # See https://www.python.org/dev/peps/pep-0396/
__date__ = '2021-02-22'
__updated__ = '2021-06-23'

SENZING_PRODUCT_ID = "5018"  # See https://github.com/Senzing/knowledge-base/blob/master/lists/senzing-product-ids.md
log_format = '%(asctime)s %(message)s'

# Working with bytes.

KILOBYTES = 1024
MEGABYTES = 1024 * KILOBYTES
GIGABYTES = 1024 * MEGABYTES

# The "configuration_locator" describes where configuration variables are in:
# 1) Command line options, 2) Environment variables, 3) Configuration files, 4) Default values

configuration_locator = {
    "debug": {
        "default": False,
        "env": "SENZING_DEBUG",
        "cli": "debug"
    },
    "dockerhub_api_endpoint_v1": {
        "default": "https://registry.hub.docker.com/v1",
        "env": "SENZING_DOCKERHUB_API_ENDPOINT_V1",
        "cli": "dockerhub-api-endpoint-v1"
    },
    "dockerhub_api_endpoint_v2": {
        "default": "https://hub.docker.com/v2",
        "env": "SENZING_DOCKERHUB_API_ENDPOINT_V2",
        "cli": "dockerhub-api-endpoint-v2"
    },
    "dockerhub_organization": {
        "default": "senzing",
        "env": "SENZING_DOCKERHUB_ORGANIZATION",
        "cli": "dockerhub-organization"
    },
    "dockerhub_password": {
        "default": None,
        "env": "SENZING_DOCKERHUB_PASSWORD",
        "cli": "dockerhub-password"
    },
    "dockerhub_username": {
        "default": None,
        "env": "SENZING_DOCKERHUB_USERNAME",
        "cli": "dockerhub-username"
    },
    "sleep_time_in_seconds": {
        "default": 0,
        "env": "SENZING_SLEEP_TIME_IN_SECONDS",
        "cli": "sleep-time-in-seconds"
    },
    "subcommand": {
        "default": None,
        "env": "SENZING_SUBCOMMAND",
    }
}

# Enumerate keys in 'configuration_locator' that should not be printed to the log.

keys_to_redact = [
    "dockerhub_password",
]

# Docker registries for knowledge-base/lists/versions-latest.sh

dockerhub_repositories_for_latest = {
    'adminer': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_ADMINER'
    },
    'apt': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_APT'
    },
    'aptdownloader': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_APT_DOWNLOADER'
    },
    'db2': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_DB2',
        'version': '11.5.0.0a'
    },
    'db2-driver-installer': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_DB2_DRIVER_INSTALLER'
    },
    'entity-search-web-app': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_ENTITY_SEARCH_WEB_APP'
    },
    'g2command': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_G2COMMAND'
    },
    'g2configtool': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_G2CONFIGTOOL'
    },
    'g2loader': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_G2LOADER'
    },
    'init-container': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_INIT_CONTAINER'
    },
    'jupyter': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_JUPYTER'
    },
    'kafdrop': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_OBSIDIANDYNAMICS_KAFDROP',
        'version': '3.23.0'
    },
    'kafka': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_BITNAMI_KAFKA',
        'version': '2.4.0'
    },
    'mssql': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_MSSQL_SERVER',
        'version': '2019-GA-ubuntu-16.04'
    },
    'mssql-tools': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_MSSQL_TOOLS',
        'version': 'latest'
    },
    'mysql': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_MYSQL',
        'version': '5.7'
    },
    'mysql-init': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_MYSQL',
        'version': 'latest'
    },
    'phppgadmin': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_PHPPGADMIN'
    },
    'phpmyadmin': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_PHPMYADMIN',
        'version': '4.9'
    },
    'portainer': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_PORTAINER',
        'version': 'latest'
    },
    'postgres': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_POSTGRES',
        'version': '11.6'
    },
    'postgresql-client': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_POSTGRESQL_CLIENT'
    },
    'python-demo': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_PYTHON_DEMO'
    },
    'rabbitmq': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_RABBITMQ',
        'version': '3.8.2'
    },
    'redoer': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_REDOER'
    },
    'resolver': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_RESOLVER'
    },
    'senzing-api-server': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_SENZING_API_SERVER'
    },
    'senzing-base': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_SENZING_BASE'
    },
    'senzing-console': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_SENZING_CONSOLE'
    },
    'senzing-debug': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_SENZING_DEBUG'
    },
    'sqlite-web': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_SQLITE_WEB',
        'version': 'latest'
    },
    'sshd': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_SSHD'
    },
    'stream-loader': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_STREAM_LOADER'
    },
    'stream-logger': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_STREAM_LOGGER'
    },
    'stream-producer': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_STREAM_PRODUCER'
    },
    'swagger-ui': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_SWAGGERAPI_SWAGGER_UI',
        'version': 'v3.50.0'
    },
    'web-app-demo': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_WEB_APP_DEMO'
    },
    'xterm': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_XTERM'
    },
    'yum': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_YUM'
    },
    'yumdownloader': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_YUM_DOWNLOADER'
    },
    'zookeeper': {
        'environment_variable': 'SENZING_DOCKER_IMAGE_VERSION_BITNAMI_ZOOKEEPER',
        'version': '3.5.6'
    }
}
# -----------------------------------------------------------------------------
# Define argument parser
# -----------------------------------------------------------------------------


def get_parser():
    ''' Parse commandline arguments. '''

    subcommands = {
        'print-latest-versions': {
            "help": 'Print latest versions of Docker images.',
            "argument_aspects": ["common"],
            "arguments": {},
        },
        'sleep': {
            "help": 'Do nothing but sleep. For Docker testing.',
            "arguments": {
                "--sleep-time-in-seconds": {
                    "dest": "sleep_time_in_seconds",
                    "metavar": "SENZING_SLEEP_TIME_IN_SECONDS",
                    "help": "Sleep time in seconds. DEFAULT: 0 (infinite)"
                },
            },
        },
        'version': {
            "help": 'Print version of program.',
        },
        'docker-acceptance-test': {
            "help": 'For Docker acceptance testing.',
        },
    }

    # Define argument_aspects.

    argument_aspects = {
        "common": {
            "--debug": {
                "dest": "debug",
                "action": "store_true",
                "help": "Enable debugging. (SENZING_DEBUG) Default: False"
            },
            "--dockerhub-api-endpoint-v1": {
                "dest": "dockerhub_api_endpoint_v1",
                "metavar": "SENZING_DOCKERHUB_API_ENDPOINT_V1",
                "help": "Dockerhub API endpoint Version 1"
            },
            "--dockerhub-api-endpoint-v2": {
                "dest": "dockerhub_api_endpoint_v2",
                "metavar": "SENZING_DOCKERHUB_API_ENDPOINT_V2",
                "help": "Dockerhub API endpoint Version 2"
            },
        },
    }

    # Augment "subcommands" variable with arguments specified by aspects.

    for subcommand, subcommand_value in subcommands.items():
        if 'argument_aspects' in subcommand_value:
            for aspect in subcommand_value['argument_aspects']:
                if 'arguments' not in subcommands[subcommand]:
                    subcommands[subcommand]['arguments'] = {}
                arguments = argument_aspects.get(aspect, {})
                for argument, argument_value in arguments.items():
                    subcommands[subcommand]['arguments'][argument] = argument_value

    parser = argparse.ArgumentParser(description="Reports from DockerHub. For more information, see https://github.com/Senzing/dockerhub-util")
    subparsers = parser.add_subparsers(dest='subcommand', help='Subcommands (SENZING_SUBCOMMAND):')

    for subcommand_key, subcommand_values in subcommands.items():
        subcommand_help = subcommand_values.get('help', "")
        subcommand_arguments = subcommand_values.get('arguments', {})
        subparser = subparsers.add_parser(subcommand_key, help=subcommand_help)
        for argument_key, argument_values in subcommand_arguments.items():
            subparser.add_argument(argument_key, **argument_values)

    return parser

# -----------------------------------------------------------------------------
# Message handling
# -----------------------------------------------------------------------------

# 1xx Informational (i.e. logging.info())
# 3xx Warning (i.e. logging.warning())
# 5xx User configuration issues (either logging.warning() or logging.err() for Client errors)
# 7xx Internal error (i.e. logging.error for Server errors)
# 9xx Debugging (i.e. logging.debug())


MESSAGE_INFO = 100
MESSAGE_WARN = 300
MESSAGE_ERROR = 700
MESSAGE_DEBUG = 900

message_dictionary = {
    "100": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}I",
    "292": "Configuration change detected.  Old: {0} New: {1}",
    "293": "For information on warnings and errors, see https://github.com/Senzing/dockerhub-util",
    "294": "Version: {0}  Updated: {1}",
    "295": "Sleeping infinitely.",
    "296": "Sleeping {0} seconds.",
    "297": "Enter {0}",
    "298": "Exit {0}",
    "299": "{0}",
    "300": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}W",
    "499": "{0}",
    "500": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "696": "Bad SENZING_SUBCOMMAND: {0}.",
    "697": "No processing done.",
    "698": "Program terminated with error.",
    "699": "{0}",
    "700": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "899": "{0}",
    "900": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}D",
    "998": "Debugging enabled.",
    "999": "{0}",
}


def message(index, *args):
    index_string = str(index)
    template = message_dictionary.get(index_string, "No message for index {0}.".format(index_string))
    return template.format(*args)


def message_generic(generic_index, index, *args):
    index_string = str(index)
    return "{0} {1}".format(message(generic_index, index), message(index, *args))


def message_info(index, *args):
    return message_generic(MESSAGE_INFO, index, *args)


def message_warning(index, *args):
    return message_generic(MESSAGE_WARN, index, *args)


def message_error(index, *args):
    return message_generic(MESSAGE_ERROR, index, *args)


def message_debug(index, *args):
    return message_generic(MESSAGE_DEBUG, index, *args)


def get_exception():
    ''' Get details about an exception. '''
    exception_type, exception_object, traceback = sys.exc_info()
    frame = traceback.tb_frame
    line_number = traceback.tb_lineno
    filename = frame.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, line_number, frame.f_globals)
    return {
        "filename": filename,
        "line_number": line_number,
        "line": line.strip(),
        "exception": exception_object,
        "type": exception_type,
        "traceback": traceback,
    }

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


def get_configuration(args):
    ''' Order of precedence: CLI, OS environment variables, INI file, default. '''
    result = {}

    # Copy default values into configuration dictionary.

    for key, value in list(configuration_locator.items()):
        result[key] = value.get('default', None)

    # "Prime the pump" with command line args. This will be done again as the last step.

    for key, value in list(args.__dict__.items()):
        new_key = key.format(subcommand.replace('-', '_'))
        if value:
            result[new_key] = value

    # Copy OS environment variables into configuration dictionary.

    for key, value in list(configuration_locator.items()):
        os_env_var = value.get('env', None)
        if os_env_var:
            os_env_value = os.getenv(os_env_var, None)
            if os_env_value:
                result[key] = os_env_value

    # Copy 'args' into configuration dictionary.

    for key, value in list(args.__dict__.items()):
        new_key = key.format(subcommand.replace('-', '_'))
        if value:
            result[new_key] = value

    # Add program information.

    result['program_version'] = __version__
    result['program_updated'] = __updated__

    # Special case: subcommand from command-line

    if args.subcommand:
        result['subcommand'] = args.subcommand

    # Special case: Change boolean strings to booleans.

    booleans = [
        'debug',
    ]
    for boolean in booleans:
        boolean_value = result.get(boolean)
        if isinstance(boolean_value, str):
            boolean_value_lower_case = boolean_value.lower()
            if boolean_value_lower_case in ['true', '1', 't', 'y', 'yes']:
                result[boolean] = True
            else:
                result[boolean] = False

    # Special case: Change integer strings to integers.

    integers = [
        'sleep_time_in_seconds'
    ]
    for integer in integers:
        integer_string = result.get(integer)
        result[integer] = int(integer_string)

    return result


def validate_configuration(config):
    ''' Check aggregate configuration from commandline options, environment variables, config files, and defaults. '''

    user_warning_messages = []
    user_error_messages = []

    # Perform subcommand specific checking.

    subcommand = config.get('subcommand')

    if subcommand in ['comments']:

        if not config.get('github_access_token'):
            user_error_messages.append(message_error(701))

    # Log warning messages.

    for user_warning_message in user_warning_messages:
        logging.warning(user_warning_message)

    # Log error messages.

    for user_error_message in user_error_messages:
        logging.error(user_error_message)

    # Log where to go for help.

    if len(user_warning_messages) > 0 or len(user_error_messages) > 0:
        logging.info(message_info(293))

    # If there are error messages, exit.

    if len(user_error_messages) > 0:
        exit_error(697)


def redact_configuration(config):
    ''' Return a shallow copy of config with certain keys removed. '''
    result = config.copy()
    for key in keys_to_redact:
        try:
            result.pop(key)
        except:
            pass
    return result

# -----------------------------------------------------------------------------
# Class DockerHubClient
# Inspired by https://github.com/amalfra/docker-hub/blob/master/src/libs/docker_hub_client.py
# -----------------------------------------------------------------------------


class DockerHubClient:
    """ Wrapper to communicate with docker hub API """

    def __init__(self, config):
        self.auth_token = config.get('auth_token')
        self.dockerhub_api_endpoint_v1 = config.get('dockerhub_api_endpoint_v1')
        self.dockerhub_api_endpoint_v2 = config.get('dockerhub_api_endpoint_v2')
        self.valid_methods = ['GET', 'POST']

    def do_request(self, url, method='GET', data={}):
        result = {}
        if method not in self.valid_methods:
            raise ValueError('Invalid HTTP request method')
        headers = {'Content-type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = 'JWT ' + self.auth_token
        request_method = getattr(requests, method.lower())
        if len(data) > 0:
            data = json.dumps(data, indent=2, sort_keys=True)
            response = request_method(url, data, headers=headers)
        else:
            response = request_method(url, headers=headers)
        if response.status_code == 200:
            result = json.loads(response.content.decode())
        return result

    def get_repositories(self, organization):
        url = '{0}/repositories/{1}/'.format(self.dockerhub_api_endpoint_v2, organization)
        return self.do_request(url)

    def get_repository_tags(self, organization, repository_name):
        url = '{0}/repositories/{1}/{2}/tags'.format(self.dockerhub_api_endpoint_v1, organization, repository_name)
        return self.do_request(url)

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------


def bootstrap_signal_handler(signal, frame):
    sys.exit(0)


def create_signal_handler_function(args):
    ''' Tricky code.  Uses currying technique. Create a function for signal handling.
        that knows about "args".
    '''

    def result_function(signal_number, frame):
        logging.info(message_info(298, args))
        sys.exit(0)

    return result_function


def entry_template(config):
    ''' Format of entry message. '''
    debug = config.get("debug", False)
    config['start_time'] = time.time()
    if debug:
        final_config = config
    else:
        final_config = redact_configuration(config)
    config_json = json.dumps(final_config, sort_keys=True)
    return message_info(297, config_json)


def exit_template(config):
    ''' Format of exit message. '''
    debug = config.get("debug", False)
    stop_time = time.time()
    config['stop_time'] = stop_time
    config['elapsed_time'] = stop_time - config.get('start_time', stop_time)
    if debug:
        final_config = config
    else:
        final_config = redact_configuration(config)
    config_json = json.dumps(final_config, sort_keys=True)
    return message_info(298, config_json)


def exit_error(index, *args):
    ''' Log error message and exit program. '''
    logging.error(message_error(index, *args))
    logging.error(message_error(698))
    sys.exit(1)


def exit_silently():
    ''' Exit program. '''
    sys.exit(0)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def find_latest_version(version_list):
    # TODO: Perhaps improve with https://pypi.org/project/semver/

    redact_list = [
        'latest',
        'experimental'
    ]

    for redact in redact_list:
        if redact in version_list:
            version_list.remove(redact)
    return max(version_list)


def get_latest_versions(config, dockerhub_repositories):

    result = []
    organization_default = config.get('dockerhub_organization')
    dockerhub_client = DockerHubClient(config)

    for key, value in dockerhub_repositories.items():
        organization = value.get('organization', organization_default)
        latest_version = value.get('version')
        if not latest_version:
            response = dockerhub_client.get_repository_tags(organization, key)
            version_tags = [x.get('name') for x in response]
            latest_version = find_latest_version(version_tags)
        result.append("export {0}={1}".format(value.get('environment_variable'), latest_version))

    result.sort()
    return result

# -----------------------------------------------------------------------------
# do_* functions
#   Common function signature: do_XXX(args)
# -----------------------------------------------------------------------------


def do_docker_acceptance_test(args):
    ''' For use with Docker acceptance testing. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)

    # Prolog.

    logging.info(entry_template(config))

    # Epilog.

    logging.info(exit_template(config))


def do_print_latest_versions(args):
    ''' Do a task. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)

    # Prolog.

    logging.info(entry_template(config))

    # Do work.

    response = get_latest_versions(config, dockerhub_repositories_for_latest)

    print("#!/usr/bin/env bash")
    print("")
    print("# Generated on {0} by https://github.com/Senzing/dockerhub-util dockerhub-util.py version: {1} update: {2}".format(date.today(), config.get('program_version'), config.get('program_updated')))
    print("")

    for line in response:
        print(line)

    # Epilog.

    logging.info(exit_template(config))


def do_sleep(args):
    ''' Sleep.  Used for debugging. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)

    # Prolog.

    logging.info(entry_template(config))

    # Pull values from configuration.

    sleep_time_in_seconds = config.get('sleep_time_in_seconds')

    # Sleep

    if sleep_time_in_seconds > 0:
        logging.info(message_info(296, sleep_time_in_seconds))
        time.sleep(sleep_time_in_seconds)

    else:
        sleep_time_in_seconds = 3600
        while True:
            logging.info(message_info(295))
            time.sleep(sleep_time_in_seconds)

    # Epilog.

    logging.info(exit_template(config))


def do_version(args):
    ''' Log version information. '''

    logging.info(message_info(294, __version__, __updated__))

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


if __name__ == "__main__":

    # Configure logging. See https://docs.python.org/2/library/logging.html#levels

    log_level_map = {
        "notset": logging.NOTSET,
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "fatal": logging.FATAL,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }

    log_level_parameter = os.getenv("SENZING_LOG_LEVEL", "info").lower()
    log_level = log_level_map.get(log_level_parameter, logging.INFO)
    logging.basicConfig(format=log_format, level=log_level)
    logging.debug(message_debug(998))

    # Trap signals temporarily until args are parsed.

    signal.signal(signal.SIGTERM, bootstrap_signal_handler)
    signal.signal(signal.SIGINT, bootstrap_signal_handler)

    # Parse the command line arguments.

    subcommand = os.getenv("SENZING_SUBCOMMAND", None)
    parser = get_parser()
    if len(sys.argv) > 1:
        args = parser.parse_args()
        subcommand = args.subcommand
    elif subcommand:
        args = argparse.Namespace(subcommand=subcommand)
    else:
        parser.print_help()
        if len(os.getenv("SENZING_DOCKER_LAUNCHED", "")):
            subcommand = "sleep"
            args = argparse.Namespace(subcommand=subcommand)
            do_sleep(args)
        exit_silently()

    # Catch interrupts. Tricky code: Uses currying.

    signal_handler = create_signal_handler_function(args)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Transform subcommand from CLI parameter to function name string.

    subcommand_function_name = "do_{0}".format(subcommand.replace('-', '_'))

    # Test to see if function exists in the code.

    if subcommand_function_name not in globals():
        logging.warning(message_warning(696, subcommand))
        parser.print_help()
        exit_silently()

    # Tricky code for calling function based on string.

    globals()[subcommand_function_name](args)
