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

# This one needs to be before 'import gconf' to avoid static import errors
from gi.repository import Gio

import gconf
from os import listdir
from os.path import dirname, exists, isdir, isfile
from py_base.Job import Job


class CustomLogin(Job):
    '''
    Runs custom login scripts to allow icons, UI, settings to be set differently for different
    OS's under the same user account.
    '''

    def __init__(self, **kwargs):
        Job.__init__(self, **kwargs)
        self.requireUserConfig('loginScriptFolder', str, "Where do you want to keep your stored profiles?")
        self.config['installedOsProfilesFolder'] = '/usr/local/share/installed-profiles'
        self.config['lastLoggedInOsHash'] = ''

    def doRunSteps(self):
        fullPath = self.getFullPathFromArg(self.config['loginScriptFolder'])
        self.runLoginScripts(fullPath)

    def runLoginScripts(self, scriptDir):
        installedProfiles = self.getInstalledProfiles()
        for profile in installedProfiles:
            self.out.indent('Running login scripts in %s/%s...' % (scriptDir, profile))
            self.runScript('%s/%s/login.pre' % (scriptDir, profile))
            self.applyDconf('%s/%s/dconf' % (scriptDir, profile))
            self.applyGconf('%s/%s/gconf' % (scriptDir, profile))
            self.copyDotfiles('%s/%s/dotfiles' % (scriptDir, profile))
            self.runScript('%s/%s/login' % (scriptDir, profile))

            # do we need to run os-cleanup scripts?
            thisOsHash = self.getOsHash()
            if thisOsHash != self.config['lastLoggedInOsHash']:
                self.out.put("hash didn't match the last-run hash (%s)." % self.config['lastLoggedInOsHash'], self.out.LOG_LEVEL_DEBUG)
                self.runScript('%s/%s/profile-change' % (scriptDir, profile))
                self.config['lastLoggedInOsHash'] = thisOsHash
            self.out.unIndent()

    def applyDconf(self, filename):
        allSchemas = sorted(Gio.Settings.list_schemas())
        settings = self.readJsonFromFile(filename)
        if settings:
            self.out.put("Applying settings from %s" % filename)
            for path in sorted(settings.keys()):
                schema, separator, key = path.rpartition('.')
                if schema not in allSchemas:
                    self.out.put('GSettings schema not found: %s (trying to set: %s)' % (schema, key))
                    continue
                gsettings = Gio.Settings.new(schema)
                setters = {bool: gsettings.set_boolean,
                           int: gsettings.set_int,
                           float: gsettings.set_double,
                           str: gsettings.set_string,
                           unicode: gsettings.set_string,
                           list: gsettings.set_strv,
                           }
                dataType = type(settings[path])
                setterFunction = setters[dataType]
                setterFunction(key, settings[path])  # i.e. gsettings.set_int('key', 123)
        else:
            self.out.put("No settings found at %s" % filename)

    def applyGconf(self, filename):
        client = gconf.client_get_default()
        setters = {bool: client.set_bool,
                   int: client.set_int,
                   float: client.set_float,
                   str: client.set_string,
                   unicode: client.set_string,
                   list: client.set_list,
                   }
        settings = self.readJsonFromFile(filename)
        if settings:
            self.out.put("Applying settings from %s" % filename)
            for key in sorted(settings.keys()):
                dataType = type(settings[key])
                setterFunction = setters[dataType]
                try:
                    setterFunction(key, settings[key])  # i.e. gsettings.set_int('key', 123)
                except:
                    # no DBUS daemon running?
                    pass
        else:
            self.out.put("No settings found at %s" % filename)

    def copyDotfiles(self, scriptDir):
        try:
            dotfiles = sorted(listdir(scriptDir))
        except:
            # scriptDir doesn't exist
            return
        userHome = self.getUserHomeDir()
        for filename in dotfiles:
            sourceFullpath = '%s/%s' % (scriptDir, filename)
            targetFullpath = '%s/.%s' % (userHome, filename)  # dotfree > dotty
            self.copyRecursive(sourceFullpath, targetFullpath)

    def copyRecursive(self, src, dest):
        if isdir(src):
            # find all missing or 'leaf' folders and copy only those.
            if exists(dest):
                # folder exists on both sides already. Go one level down.
                for child in listdir(src):
                    self.copyRecursive('%s/%s' % (src, child),
                                       '%s/%s' % (dest, child))
            else:
                # copying from existing src to non-existing dest
                self.system.copytree(src, dest)
        elif isfile(src):
            # automatically overwrites, so we don't need any more logic
            self.system.copy(src, dest)
        else:
            self.out.put("ERROR: don't know how to copy %s to %s" % (src, dest),
                         self.out.LOG_LEVEL_ERROR)

    def runScript(self, script):
        if exists(script):
            self.out.indent('Running script: %s' % script)
            self.system.runCommand([script], self.getUserHomeDir())
            self.out.unIndent()

    def getOsHash(self):
        installedProfiles = self.getInstalledProfiles()
        osHash = '|'.join(sorted(installedProfiles))
        self.out.put('hashed current OS profile to hash key: %s' % osHash, self.out.LOG_LEVEL_DEBUG)
        return osHash

    def getInstalledProfiles(self):
        try:
            fileList = listdir(self.config['installedOsProfilesFolder'])
        except:
            # probably in debug environment - directory doesn't exist
            fileList = []
        return sorted(fileList)

if __name__ == '__main__':
    from py_base.Job import runMockJob
    def fakeProfiles():
        # MUST return sorted to match real behavior
        return ['base', 'workstation']
    CustomLogin.getInstalledProfiles = fakeProfiles
    runMockJob(CustomLogin,
               config={'loginScriptFolder': '/home/luke/Reference/Config/profiles'})

