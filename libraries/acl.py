# Copyright (c) 2015 Sine Nomine Associates
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THE SOFTWARE IS PROVIDED 'AS IS' AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import sys
import os
import re
from robot.libraries.BuiltIn import BuiltIn

_FS = None # full path to the fs command
_RIGHTS = list("rlidwkaABCDEFGH")

def _normalize(rights):
    """Normalize a list of ACL right characters.

    Return the characters in canonical order.  A exception is
    thrown for illegal characters. Duplicate characters are silently
    removed.
    """
    # First, check for illegal chars.
    for r in rights:
        if not r in _RIGHTS:
            raise AssertionError("Illegal rights character: %s" % (r))
    # Create a set in the standard order.
    normalized = []
    for r in _RIGHTS:
        if r in rights:
            normalized.append(r)
    return normalized

def _split(rights):
    """ Returns a list string of right chars from a string.

    Unlike the fs commands, the leading char may be a '+'
    or '-' to indicate the type of rights.  Right alias names
    are expanded into right chars.

    Illegal chars will throw an exception.  Duplicate chars
    are silently removed.
    """
    sign = '+'            # default is positive rights
    rights = list(rights) # split into chars

    # An optional leading '+' or '-' indicates positive
    # or negative rights.
    if len(rights) >= 0 and rights[0] in ('+', '-'):
        sign = rights[0]
        rights = rights[1:]

    # Convert the aliases to the list of rights bits.
    w = "".join(rights)
    if w == "all":
        rights = _RIGHTS
    elif w == "none":
        rights = list()
    elif w == "read":
        rights = list("rl")
    elif w == "write":
        rights = list("rlidwk")

    return (sign, _normalize(rights))

class AccessControlList:
    """ACL rights checking."""

    @staticmethod
    def from_args(*args):
        """Create an ACL test object from a list of string arguments."""
        acl = AccessControlList()
        for arg in args:
            parts = arg.split()
            if len(parts) != 2:
                raise AssertionError("Invalid ACL format: '%s'" % arg)
            acl.add(parts[0], parts[1])
        return acl

    @staticmethod
    def from_path(path):
        """Read an ACL from AFS directory to create an ACL test object."""
        if not os.path.exists(path):
            raise AssertionError("Path does not exist: %s" % (path))
        if not os.path.isdir(path):
            raise AssertionError("Path is not a directory: %s" % (path))
        try:
            if _FS:
                fs = _FS
            else:
                fs = BuiltIn().get_variable_value("${FS}")
        except:
            raise AssertionError("FS variable is not set!")
        acl = AccessControlList()
        section = None
        cmd = "%s listacl %s" % (fs, path)
        pipe = os.popen(cmd)
        for line in pipe.readlines():
            if line.startswith("Access list for"):
                continue
            if line.startswith("Normal rights:"):
                section = "+"
                continue
            if line.startswith("Negative rights:"):
                section = "-"
                continue
            m = re.match(r'  (\S+) (\S+)', line)
            if m:
                name,rights = (m.group(1),m.group(2))
                if not section in ('+', '-'):
                    raise AssertionError("Failed to parse fs listacl; missing section label")
                acl.add(name, section + rights)
        rc = pipe.close()
        if rc:
            raise AssertionError("Failed to run %s: rc=%d" % (cmd,rc))
        return acl

    def __init__(self):
        """Create a new empty ACL test object."""
        self.acls = {}

    def __eq__(self, other):
        """Returns true if ACL test objects have the same entries."""
        if isinstance(other, self.__class__):
            return self.__str__() == self.__str__()
        else:
            return False

    def __ne__(self, other):
        """Returns true if ACL tests objects do not have the same entries."""
        return not self.__eq__(other)

    def __str__(self):
        """Returns a flat string listing all the entries in this ACL test object."""
        sep = ","
        items = []
        for name in sorted(self.acls.keys()):
            (pos,neg) = self.acls[name]
            if neg == "":
                items.append("%s+%s" % (name, pos))
            else:
                items.append("%s+%s-%s" % (name, pos, neg))
        return sep.join(items)

    def add(self, name, rights):
        """Add an entry."""
        if name not in self.acls:
            self.acls[name] = ('','')
        acl = self.acls[name] # current entry
        (sign,rights) = _split(rights)
        # Update the rights.
        if sign == '+':
            pos = "".join(_normalize(rights + list(acl[0])))
            neg = acl[1]
        elif sign == '-':
            pos = acl[0]
            neg = "".join(_normalize(rights + list(acl[1])))
        else:
            assert "Internal error"
        if pos == '' and neg == '':
            del self.acls[name]  # cleared
        else:
            self.acls[name] = (pos, neg)

    def contains(self, name, rights):
        """Returns true if an entry exists with a matching name and rights."""
        if name not in self.acls:
            return False
        acl = self.acls[name] # current entry
        (sign,rights) = _split(rights)
        rights = "%s%s" % (sign, "".join(rights))
        if sign == '+':
            current = "+%s" % acl[0]
        elif sign == '-':
            current = "-%s" % acl[1]
        else:
            assert "Internal error"
        if rights != current:
            return False
        return True


#
# Unit tests
#

def _test2_old():
    cases = [
        ("",     ("", "")),
        ("rl",   ("rl", "")),
        ("rl-l", ("rl", "l")),
        ("-w",   ("", "w"))
    ]
    for x,y in cases:
        u,v = AccessControlList.parse_rights(x)
        assert u == y[0] and v == y[1], "expected=(%s,%s), got=(%s,%s)" % (u,v,y[0],y[1])

def _test1():
    cases = [
        ("", ""),
        ("r", "r"),
        ("lr", "rl"),
        ("rlidwka", "rlidwka"),
        ("adiklrw", "rlidwka"),
        ("abcd",    None),
    ]
    for x,y in cases:
        try:
            z = "".join(_normalize(list(x)))
        except:
            assert y is None, "expected exception: x='%s'" % (x)
        if y:
            assert z == y, "expected='%s', got='%s'" % (y,z)

def _test2():
    cases = [
        "system:administrators rlidwka",
        "system:anyuser rl",
        "user1 rl",
        "user2 rl",
        "user2 rwl",
        "user2 -l",
        "user3 +rlidwk",
        "user4 none",
        "user5 read",
        "user6 write",
        "user7 -write",
    ]
    expected = {
        "system:administrators": ("rlidwka",""),
        "system:anyuser": ("rl",""),
        "user1": ("rl",""),
        "user2": ("rlw","l"),
        "user3": ("rlidwk",""),
        "user5": ("rl",""),
        "user6": ("rlidwkl",""),
        "user7": ("","rlidwk"),
    }
    a = AccessControlList()
    for case in cases:
        name,rights = case.split()
        a.add(name, rights)
    assert cmp(a.acls, expected)

def _test3():
    p = '/afs/robotest/test'
    t = [
        "system:administrators rlidwka",
        "system:anyuser rl",
        "user1 rl",
        "user2 rl",
        "user2 rwl",
        "user2 -l",
        "user3 +rlidwk",
        "user4 none",
    ]
    a1 = AccessControlList.from_path(p)
    a2 = AccessControlList.from_args(*t)
    #print "a1=", a1
    #print "a2=", a2
    assert not a1 is a2

def _test4():
    t = [
        "system:administrators rlidwka",
        "system:anyuser rl",
        "user1 rl",
        "user2 rl",
        "user2 rwl",
        "user2 -l",
        "user3 +rlidwk",
        "user4 none",
    ]
    a = AccessControlList.from_args(*t)
    assert a.contains("system:administrators", "rlidwka")
    assert a.contains("system:anyuser", "rl")
    assert a.contains("user1", "+rl")
    assert a.contains("user2", "rlw")
    assert a.contains("user2", "-l")
    assert a.contains("user3", "+rlidwk")
    assert not a.contains("user4", "none")

if __name__ == "__main__":
    _FS = "/usr/afs/bin/fs"
    _test1()
    _test2()
    _test3()
    _test4()

