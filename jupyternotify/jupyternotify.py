# see https://ipython.org/ipython-doc/3/config/custommagics.html
# for more details on the implementation here
import json
import os
import time
import uuid

from IPython.core.getipython import get_ipython
from IPython.core.magic import (Magics, cell_magic, line_cell_magic,
                                line_magic, magics_class)
from IPython.core.magic_arguments import (argument, magic_arguments,
                                          parse_argstring)
from IPython.display import Javascript, display
from pkg_resources import resource_filename

from jupyternotify import telegram_notify


@magics_class
class JupyterNotifyMagics(Magics):
    # pointer to *_run_cell events
    _events = None, None
    # start time of cell execution
    run_start_time = None
    # uuid for autonotify
    notification_uuid = None

    def __init__(self, shell, require_interaction=False):
        super(JupyterNotifyMagics, self).__init__(shell)
        self.options = {
            "requireInteraction": require_interaction,
            "icon": "/static/base/images/favicon.ico",
        }
        self.telegram_api_key = os.environ['TELEGRAM_API_KEY']
        self.telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']

    @magic_arguments()
    @argument(
        "-m",
        "--message",
        default="Cell execution has finished!",
        help="Custom notification message"
    )
    @argument(
        "-o",
        "--output", action='store_true',
        help="Use last output as message"
    )
    @line_cell_magic
    def notify(self, line, cell=None):
        # custom message
        args = parse_argstring(self.notify, line)
        message = args.message.lstrip("\'\"").rstrip("\'\"")

        # Run cell if its cell magic
        if cell is not None:
            execution_start = time.time()
            output = get_ipython().run_cell(cell)
            execution_time = time.time() - execution_start

            if output.error_before_exec or output.error_in_exec:
                message = f'Cell Execution failed: {output.error_before_exec or output.error_in_exec}'

            # prevent autonotify from firing with notify cell magic
            self.__class__.notification_uuid = None

        # display our browser notification using javascript
        self.display_notification(message)


    def display_notification(self, message: str):
        telegram_notify.notify(message, self.telegram_api_key, self.telegram_chat_id)


    @magic_arguments()
    @argument(
        "-a", "--after", default=None,
        help="Send notification if cell execution is longer than x seconds"
    )
    @argument(
        "-m",
        "--message",
        default="Cell Execution Has Finished!",
        help="Custom notification message"
    )
    @argument(
        "-o",
        "--output", action='store_true',
        help="Use last output as message"
    )
    @line_magic
    def autonotify(self, line):
        # Record options
        args = parse_argstring(self.autonotify, line)
        self.options["body"] = args.message.lstrip("\'\"").rstrip("\'\"")
        self.options['autonotify_after'] = args.after
        self.options['autonotify_output'] = args.output

        ## Register events
        ip = get_ipython()

        # Remove events if they're already registered
        # This is necessary because jupyter makes a new instance everytime
        pre, post = self.__class__._events
        if pre and pre in ip.events.callbacks['pre_run_cell']:
            ip.events.callbacks['pre_run_cell'].remove(pre)
        if post and post in ip.events.callbacks['post_run_cell']:
            ip.events.callbacks['post_run_cell'].remove(post)

        # Register new events
        ip.events.register('pre_run_cell', self.pre_run_cell)
        ip.events.register('post_run_cell', self.post_run_cell)
        self.__class__._events = self.pre_run_cell, self.post_run_cell

    def pre_run_cell(self):
        # Initialize autonotify
        if self.options.get('autonotify_after'):
            self.run_start_time = time.time()
        self.__class__.notification_uuid = uuid.uuid4()

    def post_run_cell(self):
        # TODO detect if the cell execution failed
        options = dict(self.options)
        # Set last output as notification message
        if self.options.get('autonotify_output'):
            last_output = get_ipython().user_global_ns['_']
            # Don't use output if it's None or empty (but still allow False, 0, etc.)
            try:
                if last_output is not None and len(str(last_output)):
                    options['body'] = str(last_output)
            except ValueError:
                pass # can't convert to string. Use default message

        # allow notify to stop autonotify
        if not self.__class__.notification_uuid:
            return
        # Check autonotify options and perform checks
        elif self.check_after():
            pass
        # maybe add other triggers here too
        # example/idea: autonotify if browser window not in focus
        else:
            return
        self.display_notification(message='Cell Execution Has Finished!')


    def check_after(self):
        # Check if the time elapsed is over the specified time.
        now, start = time.time(), self.run_start_time
        threshold = float(self.options.get('autonotify_after', -1))
        return threshold >= 0 and start and (now - start) >= threshold
