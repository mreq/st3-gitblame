import sublime
import sublime_plugin
import os
import functools
import subprocess
from subprocess import check_output as shell


blame_cache = {}
template = '''
<span>
<style>
span {{
    background-color: brown;
}}
a {{
    text-decoration: none;
}}
</style>
<a href="close">
<strong>Git Blame:</strong> ({user})
Last updated: {date} {time} | [{sha}]
<close>X</close>&nbsp;
</a>
</span>
'''

# Sometimes this fails on other OS, just error silently
try:
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
except:
    si = None

class BlameCommand(sublime_plugin.TextCommand):

    def __init__(self, view):
        self.view = view
        self.phantom_set = sublime.PhantomSet(view, 'git-blame')

    @functools.lru_cache(128, False)
    def get_blame(self, line, path):
        try:
            return shell(["git", "blame", "--minimal", "-w",
                "-L {0},{0}".format(line), path],
                cwd=os.path.dirname(os.path.realpath(path)),
                startupinfo=si)
        except Exception as e:
            return

    def parse_blame(self, blame):
        sha, file_path, user, date, time, tz_offset, *_ = blame.decode('utf-8').split()

        # Was part of the inital commit so no updates
        if file_path[0] == '(':
            user, date, time, tz_offset = file_path, user, date, time
            file_path = None

        return(sha, user[1:], date, time)

    def on_phantom_close(self, href):
        self.view.erase_phantoms('git-blame')


    def run(self, edit):
        phantoms = []
        self.view.erase_phantoms('git-blame')

        for region in self.view.sel():
            line = self.view.line(region)
            (row, col) = self.view.rowcol(region.begin())
            full_path = self.view.file_name()
            result = self.get_blame(int(row)+1, full_path)
            if not result:
                # Unable to get blame
                return

            sha, user, date, time = self.parse_blame(result)
            body = template.format(sha=sha, user=user, date=date, time=time)

            phantom = sublime.Phantom(line, body, sublime.LAYOUT_BLOCK, self.on_phantom_close)
            phantoms.append(phantom)
        self.phantom_set.update(phantoms)
