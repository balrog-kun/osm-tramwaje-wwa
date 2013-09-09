#! /usr/bin/python2
# vim: fileencoding=utf-8 encoding=utf-8 et sw=4

# Copyright (C) 2009 Andrzej Zaborowski <balrogg@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


import os
import sys
import re

import xml.etree.cElementTree as ElementTree
import tidy

import locale, codecs
try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    encoding = locale.getlocale()[1]
    sys.stdout = codecs.getwriter(encoding)(sys.stdout, errors = "replace")
    sys.stderr = codecs.getwriter(encoding)(sys.stderr, errors = "replace")
except locale.Error:
    pass

tidyopts = dict(output_xml = 1, tidy_mark = 0,
        char_encoding = "utf8", input_encoding = "utf8",
        output_encoding = "utf8")

def recode(line):
    try:
        return line
    except:
        sys.stderr.write("warning: couldn't recode " + line + " in UTF-8!\n");
        return line

x_links = []
ns = "{http://www.w3.org/1999/xhtml}"
def parselement(el, pre):
    tag = el.tag
    if tag.startswith(ns):
        tag = tag[len(ns):]

    if tag == "a":
        x_links.append((el.attrib["href"], recode(el.text)))

    for sub in el:
        parselement(sub, pre)
def parselinks(doc):
    global x_links
    x_links = []
    tree = ElementTree.fromstring(str(doc))
    parselement(tree, 0)
    return x_links
def stopsparse(filename):
    f = open(filename, "r")
    p = -1
    n = -1
    e = -1
    ret = []
    for line in f:
        line = re.sub("<[^>]*>", "", unicode(line, "utf8")).rstrip()
        np = line.find("Przystanek ")
        nn = line.find("Nr ")
        if np > -1 and nn > -1:
            p = np
            n = nn
            e = n
            while line[e] != " " and e < len(line):
                e += 1
            while line[e] == " " and e < len(line):
                e += 1
            e -= 1
            continue
        if n == -1 or len(line) < e or line[p] == " ":
            continue
        ret.append(("", line[p:e]))
    f.close()
    return ret

outroot = ElementTree.Element("routes", {
    "route": "tram",
    "network": "local",
    "operator": u"Zarząd Transportu Miejskiego w Warszawie",
    "way": "railway=tram",
    "stop": "railway=tram_stop",
    "onlywholeway": "yes",
    "notightturns": "yes" })
outtree = ElementTree.ElementTree(outroot)

for arg in sys.argv[1:]:
    doc = tidy.parse(arg + "/TRASY.HTM", **tidyopts)
    links = [ x for x in parselinks(doc) if x[0].startswith("T") ]
    if len(links) != 2 and len(links) != 1:
        sys.stderr.write(arg + "/TRASY.HTM has " +
                str(len(links)) + " links!\n")
        sys.exit(-5)

    stops = []
    firststops = []
    firstp = 0
    lastp = 0
    for file, subroute in links:
        stoplinks = stopsparse(arg + "/" + file)
        newstops = []
        for subfile, stop in stoplinks:
            name = stop.replace(".", ". ").split()
            for i, word in enumerate(name):
                name[i] = word.capitalize(). \
                        replace("zoo", "ZOO").replace("bazylika", "Bazylika")
            newstops.append(" ".join(name))

        if not len(firststops):
            firststops = newstops

        """
        if len(stops) and stops[-1] != newstops[0]:
            sys.stderr.write(arg + "/" + file +
                    " first stop is not continuous\n")
            sys.exit(-5)
        """
        if len(stops) and stops[-1] == newstops[0]:
            newstops = newstops[1:]
            lastp = 1
        if len(stops) and stops[0] == newstops[-1]:
            newstops = newstops[:-1]
            firstp = 1
        stops += newstops

    route = ElementTree.SubElement(outroot, "route", {
        "ref": arg[9:],
        "name": "Linia " + arg[9:],
        "circular": "yes",
        "description": "Linia " + arg[9:] + ": " +
            firststops[0].strip(" 0123456789") + " - " +
            firststops[-1].strip(" 0123456789") })
    for stop in stops:
        if stop in firststops:
            if stop == firststops[0] and firstp:
                dir = "both"
            elif stop == firststops[-1] and lastp:
                dir = "both"
            else:
                dir = "forward"
        else:
            dir = "backward"
        routest = ElementTree.SubElement(route, "stop", { "direction": dir })
        routest.text = stop

outtree.write("routes.xml", "utf-8")
