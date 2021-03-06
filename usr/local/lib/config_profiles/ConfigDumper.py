#!/usr/bin/python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version. 

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from py_base.Job import Job

import re
from subprocess import Popen, STDOUT, PIPE
import sys


class ConfigDumper(Job):

    def __init__(self, out=None, system=None):
        Job.__init__(self, out, system)
        self.argumentPseudonyms['d'] = DconfDumperAdapter
        self.argumentPseudonyms['dconf'] = DconfDumperAdapter
        self.argumentPseudonyms['g'] = GconfDumperAdapter
        self.argumentPseudonyms['gconf'] = GconfDumperAdapter
        self.argumentPseudonyms['x'] = XfceDumperAdapter
        self.argumentPseudonyms['xfce'] = XfceDumperAdapter
        self.arguments[DconfDumperAdapter] = False
        self.arguments[GconfDumperAdapter] = False
        self.arguments[XfceDumperAdapter] = False

    def doRunSteps(self):
        for adapterType in [DconfDumperAdapter,
                            GconfDumperAdapter,
                            XfceDumperAdapter]:
            if self.arguments[adapterType]:
                self.out.put('')
                self.out.indent('### %s ###' % adapterType.__doc__)
                adapterType(self.out, self.system).printPath('/')
                self.out.unIndent()

class DconfDumperAdapter:
    'Dconf'

    out = None
    system = None

    def __init__(self, out, system):
        self.out = out
        self.system = system

    def printPath(self, path):
        assert(self.isDirectory(path)) # can only run 'list' for paths, not k/v pairs
        children = self.system.runCommand(['dconf', 'list', path]).rstrip().split('\n')
        for child in children:
            if self.isDirectory(path + child):
                self.printPath(path + child)
            else:
                self.printDconfNode(path + child)

    def printDconfNode(self, path):
        assert(not self.isDirectory(path)) # only print k/v pairs, not directories
        value = self.system.runCommand(['dconf', 'read', path]).rstrip()
        self.out.put('dconf write %s %s' % (self.escape(path), self.escape(value)))

    def isDirectory(self, path):
        if re.match('.*\/$', path):
            return True
        return False

    def escape(self, string):
        string = '"%s"' % string.replace('"', '\\"')
        return string

class GconfDumperAdapter:
    'Gconf'
    pass

class XfceDumperAdapter:
    'XfceConfig'
    pass

if __name__ == "__main__":
    ConfigDumper().run()

