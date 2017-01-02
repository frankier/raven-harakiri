# coding: utf-8
"""
Raven cli client for harakiri monitoring.
Based on raven test client code.

Original copyrights:
    :copyright: (c) 2012 by the Sentry Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import print_function
import fileinput
import logging
import re
import sys
from optparse import OptionParser
from raven import get_version, os, Client
from raven.utils import json
from six import StringIO
from raven.utils.stacks import get_lines_from_file


def store_json(option, opt_str, value, parser):
    try:
        value = json.loads(value)
    except ValueError:
        print("Invalid JSON was used for option %s.  Received: %s" % (opt_str, value))
        sys.exit(1)
    setattr(parser.values, option.dest, value)


def convert_traceback(uwsgi_traceback):
    """ Convert uwsgi traceback string with following pattern to raven protocol traceback
            thread_id = %s
            filename = %s
            lineno = %s
            function = %s
            line = %s

        More info: http://sentry.readthedocs.org/en/latest/developer/client/#building-the-json-packet
                   http://uwsgi-docs.readthedocs.org/en/latest/Tracebacker.html

        thread_id = MainThread
        filename = /home/belonika/.pythonz/pythons/CPython-2.6.8/lib/python2.6/socket.py
        lineno = 554
        function = create_connection
        line = sock.connect(sa)
    """
    variables = ('thread_id', 'filename', 'lineno', 'function', 'line')
    regexp = r' '.join(('%s = (?P<%s>.+?)' % (var, var) for var in variables))
    traceback = []
    for line in uwsgi_traceback.split('\n'):
        match = re.match(r'^%s$' % regexp, line)
        values = match.groupdict() if match else None
        if values:
            frame_result = {
                'abs_path': values['filename'],
                'context_line': values['line'],
                'filename': (values['filename']),
                'function': values['function'],
                'lineno': int(values['lineno']),

                'module': None,
                'post_context': [],
                'pre_context': [],
                'vars': {}
            }
            pre_context, context_line, post_context = get_lines_from_file(frame_result['abs_path'],
                                                                          frame_result['lineno'], 5)
            if context_line is not None:
                frame_result.update({
                    'pre_context': pre_context,
                    'post_context': post_context,
                })

            traceback.append(frame_result)

    return traceback


def extract_http(log):
    for line in log.split('\n'):
        match = re.match(
            r'^[^-]+- HARAKIRI \[core (?P<core>.+)\] (?P<remote_addr>.+) - '
            r'(?P<method>.+) (?P<url>.+) since (?P<begin_time>.+)$', line)
        if match:
            break
    if match:
        values = match.groupdict()
        return values['method'], values['url'], values['remote_addr']
    else:
        return None, None, None


def send_message(client, options, log):
    if not client.is_enabled():
        print('Error: Client reports as being disabled!')
        sys.exit(1)

    method, url, remote_addr = extract_http(log)

    data = {
        'logger': 'uwsgi.harakiri',
        'sentry.interfaces.Stacktrace': {
            'frames': convert_traceback(log)
        },
        'sentry.interfaces.Http': {
            'method': method,
            'url': url,
            'env': {
                'REMOTE_ADDR': remote_addr
            }
        }
    }

    ident = client.get_ident(client.captureMessage(
        message='uWSGI harakiri',
        data=data,
        level=logging.ERROR,
        stack=True,
        tags=options.get('tags', {}),
    ))

    if client.state.did_fail():
        return False

    return ident


def main():
    root = logging.getLogger('sentry.errors')
    root.setLevel(logging.DEBUG)
    root.addHandler(logging.StreamHandler())

    parser = OptionParser(version=get_version())
    parser.add_option("--tags", action="callback", callback=store_json, type="string", nargs=1, dest="tags")
    parser.add_option("--verbose", action="store_true")
    parser.add_option("--dsn")
    opts, args = parser.parse_args()

    dsn = opts.dsn or os.environ.get('SENTRY_DSN')
    if not dsn:
        print("Error: No configuration detected!")
        print("You must either pass a DSN to the command, or set the SENTRY_DSN environment variable.")
        sys.exit(1)

    if not opts.verbose:
        sys.stdout = StringIO()

    traceback = ''.join([line for line in fileinput.input(args)])

    client = Client(dsn, include_paths=['raven'], string_max_length=100000)
    send_message(client, opts.__dict__, traceback=traceback)


if __name__ == '__main__':
    main()
