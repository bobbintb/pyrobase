# -*- coding: utf-8 -*-
#
# Project Tasks
#
from __future__ import print_function, unicode_literals

import os
import time
import shutil
import subprocess
import webbrowser
try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

from invoke import task


PROJECT_NAME = 'pyrobase'
PYTEST_CMD = 'python -m pytest'
SPHINX_AUTOBUILD_PORT = int(os.environ.get('SPHINX_AUTOBUILD_PORT', '8340'))


@task
def test(ctx):
    """Run unit tests."""
    ctx.run(PYTEST_CMD)


@task
def cov(ctx):
    """Run unit tests & show coverage report"""
    coverage_index = Path("build/coverage/index.html")
    coverage_index.unlink()
    ctx.run(PYTEST_CMD)
    coverage_index.exists() and webbrowser.open(
        'file://{}'.format(os.path.abspath(coverage_index)))


def watchdog_pid(ctx):
    """Get watchdog PID via ``netstat``."""
    result = ctx.run('netstat -tulpn 2>/dev/null | grep 127.0.0.1:{:d}'
                     .format(SPHINX_AUTOBUILD_PORT), warn=True, pty=False)
    pid = result.stdout.strip()
    pid = pid.split()[-1] if pid else None
    pid = pid.split('/', 1)[0] if pid and pid != '-' else None

    return pid


@task(help={'open-tab': "Open docs in new browser tab after initial build"})
def docs(ctx, open_tab=False):
    """Start watchdog to build the Sphinx docs."""
    build_dir = 'docs/_build'
    index_html = build_dir + '/html/index.html'

    stop(ctx)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    ctx.run('command cd docs >/dev/null'
            ' && sphinx-apidoc -o apidoc -f -T ../src/' + PROJECT_NAME)

    print("\n*** Generating HTML doc ***\n")
    subprocess.check_call(
        'command cd docs >/dev/null'
        ' && . {pwd}/.venv/{prjname}/bin/activate'
        ' && nohup {pwd}/docs/Makefile SPHINXBUILD="sphinx-autobuild -p {port:d}'
        '          -i \'.*\' -i \'*.log\' -i \'*.png\' -i \'*.txt\'" html >autobuild.log 2>&1 &'
        .format(port=SPHINX_AUTOBUILD_PORT, pwd=os.getcwd(), prjname=PROJECT_NAME), shell=True)

    for i in range(25):
        time.sleep(2.5)
        pid = watchdog_pid(ctx)
        if pid:
            ctx.run("touch docs/index.rst")
            ctx.run('ps {}'.format(pid), pty=False)
            url = 'http://localhost:{port:d}/'.format(port=SPHINX_AUTOBUILD_PORT)
            if open_tab:
                webbrowser.open_new_tab(url)
            else:
                print("\n*** Open '{}' in your browser...".format(url))
            break


@task
def stop(ctx):
    "Stop Sphinx watchdog"
    print("\n*** Stopping watchdog ***\n")
    for i in range(4):
        pid = watchdog_pid(ctx)
        if not pid:
            break
        else:
            if not i:
                ctx.run('ps {}'.format(pid), pty=False)
            ctx.run('kill {}'.format(pid), pty=False)
            time.sleep(.5)
