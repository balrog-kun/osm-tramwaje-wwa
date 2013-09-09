#! /usr/bin/python3
# vim: fileencoding=utf-8 encoding=utf-8 et sw=4

# Copyright (C) 2010 Andrzej Zaborowski <balrogg@gmail.com>
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

import xml.etree.cElementTree as ElementTree

# need to be tweaked for every town
abbrev = {
    "osiedle": "os",
    "aleja": "al",
    "aleje": "al",
    "plac": "pl",
    "ulica": "ul",
    "armii Krajowej": "ak",
    "dworzec": "dw",
    "cmentarz": "cm",
    "księdza": "ks",
    "pętla": "",
    "rondo": "",
    "płd": "południe",
    "warszawskiego": "warszaws",
    "imigw": "i",
    "im": "i",
    "gw": "i",
}
def makeid(tags):
    if "name" not in tags:
        return []
    name = tags["name"].lower()
    for r in [ ",", ".", "\"", "-" ]:
        name = name.replace(r, " ")
    ret = {}
    for n in name.split():
        if n in abbrev:
            if abbrev[n] != "":
                ret[abbrev[n]] = 1
        else:
            ret[n] = 1
    return ret
def compareid(a, b):
    for s in a:
        if s not in b:
            return 0
    for s in b:
        if s not in a:
            return 0
    return 1

truths = [ "1", "true", "yes" ]

osm = ElementTree.parse("data.osm").getroot()
routes = ElementTree.parse("routes.xml").getroot()

osmstops = {}
osmways = {}
osmroutes = {}

attrs = {}
waypred = ""
stoppred = ""
routepred = ""
onlywholeway = 0
notightturns = 0
for attr in routes.attrib:
    if attr not in [ "way", "stop", "onlywholeway", "notightturns" ]:
        attrs[attr] = routes.attrib[attr]
    elif attr == "way":
        waypred = routes.attrib[attr]
    elif attr == "stop":
        stoppred = routes.attrib[attr]
    elif attr == "onlywholeway" and routes.attrib[attr] == "yes":
        onlywholeway = 1
    elif attr == "notightturns" and routes.attrib[attr] == "yes":
        notightturns = 1
    if attr == "route":
        routepred = attr + "=" + routes.attrib[attr]

for elem in osm:
    tags = {}
    tagpreds = {}
    for subelem in elem:
        if subelem.tag == "tag":
            tags[subelem.attrib["k"]] = subelem.attrib["v"]
            tagpreds[subelem.attrib["k"] + "=" + subelem.attrib["v"]] = 1

    if elem.tag == "node":
        if stoppred in tagpreds:
            osmstops[elem.attrib["id"]] = (elem, tags, makeid(tags))
    elif elem.tag == "way":
        if waypred in tagpreds:
            osmways[elem.attrib["id"]] = (elem, tags, {})
    elif elem.tag == "relation":
        if "type=route" in tagpreds and routepred in tagpreds and "ref" in tags:
            osmroutes[tags["ref"]] = (elem, tags)

adjnodes = {}
i = 0
for id in osmways:
    (elem, tags, adj) = osmways[id]
    first = (0, 0)
    for node in elem:
        if node.tag != "nd" or "ref" not in node.attrib:
            continue

        last = (node.attrib["ref"], i)
        if first[0] == 0:
            first = last

        if last[0] not in adjnodes:
            adjnodes[last[0]] = {}
        adjnodes[last[0]][(id, i)] = 0

        if "oneway" in tags and tags["oneway"] in truths:
            i += 1
        elif "oneway" in tags and tags["oneway"] == "-1":
            i -= 1

    if onlywholeway:
        adjnodes[first[0]][(id, first[1])] = 3
        adjnodes[last[0]][(id, last[1])] = 3

    if "oneway" in tags and tags["oneway"] in truths:
        adjnodes[first[0]][(id, first[1])] = 1
        adjnodes[last[0]][(id, last[1])] = 2
    elif "oneway" in tags and tags["oneway"] == "-1":
        adjnodes[first[0]][(id, first[1])] = 2
        adjnodes[last[0]][(id, last[1])] = 1

def istight(node, x, y):
    # TODO
    return 0

for id in adjnodes:
    for wayid, x in adjnodes[id]:
        if adjnodes[id][(wayid, x)] == 1 or (onlywholeway and
                adjnodes[id][(wayid, x)] == 0):
            continue
        for wayid2, y in adjnodes[id]:
            if adjnodes[id][(wayid2, y)] == 2 or (onlywholeway and
                    adjnodes[id][(wayid, x)] == 0):
                continue
            if wayid != wayid2 or x != y:
                if notightturns and istight(id, wayid, wayid2):
                    continue
                osmways[wayid][2][(wayid2, y)] = x

# TODO: avoid paths that pass through other stops, avoid making tight
# turns, especially turning back
def dijkstra(a, b):
    if a not in adjnodes or b not in adjnodes:
        return []
    stack = dict(adjnodes[a].keys())

    prev = dict(stack)
    pred = {}
    paths = []

    while stack:
        for id, x in adjnodes[b]:
            if id in stack and x >= stack[id]:
                paths.append((id, stack[id]))
        if paths:
            break

        newstack = {}
        for id in stack:
            for succ in osmways[id][2]:
                if osmways[id][2][succ] < stack[id]:
                    continue

                if "oneway" in osmways[succ[0]][1]:
                    succ = (succ[0], succ[1] + 1)
                if (succ[0] in newstack and newstack[succ[0]] <= succ[1]) or \
                        (succ[0] in prev and prev[succ[0]] <= succ[1]):
                    continue

                newstack[succ[0]] = succ[1]
                prev[succ[0]] = succ[1]
                pred[succ] = (id, stack[id])

        stack = newstack

    ret = []
    for end in paths:
        path = [ end[0] ]
        while end in pred:
            end = pred[end]
            path.append(end[0])

        path.reverse()
        ret.append(path)

    return ret

def isatend(node, way):
    max = 0
    i = -1
    for elem in osmways[way][0]:
        if elem.tag != "nd" or "ref" not in elem.attrib:
            continue

        max += 1

        if elem.attrib["ref"] == node:
            i = max

    return i == 1 or i == max

outroot = ElementTree.Element("osm", {
    "version": "0.6",
    "generator": sys.argv[0] })

def addrel(action, id, version, tags, roles, ways, nodes, rels):
    rel = ElementTree.SubElement(outroot, "relation", {
        "action": action,
        "id": id,
        "version": version })
    if action == "delete":
        rel.attrib["visible"] = "false"
    else:
        rel.attrib["visible"] = "true"

    for tag in tags:
        ElementTree.SubElement(rel, "tag", { "k": tag, "v": tags[tag] })

    for way in ways:
        ElementTree.SubElement(rel, "member", {
            "type": "way",
            "ref": way,
            "role": roles[way] })

    for node, d in nodes:
        ElementTree.SubElement(rel, "member", {
            "type": "node",
            "ref": node,
            "role": roles[node] })

    for mrel in rels:
        ElementTree.SubElement(rel, "member", {
            "type": "relation",
            "ref": mrel,
            "role": roles[mrel] })

missingstops = {}
noroute = {}
tosplit = {}
touched = {}

newid = -1

for route in routes:
    if route.tag != "route":
        continue

    tags = { "type": "route" }
    circular = 0
    for attr in attrs:
        tags[attr] = attrs[attr]
    for attr in route.attrib:
        if attr == "circular" and route.attrib["circular"] in truths:
            circular = 1
        else:
            tags[attr] = route.attrib[attr]

    if "ref" not in tags:
        continue
    touched[tags["ref"]] = 1

    stopids = []
    done = 1
    for stop in route:
        if stop.tag != "stop":
            continue

        id = makeid({ "name": stop.text })
        direction = "both"
        if "direction" in stop.attrib:
            direction = stop.attrib["direction"]

        matches = 0
        matchid = 0
        for osmid in osmstops:
            if compareid(id, osmstops[osmid][2]):
                matchid = osmid
                matches += 1
        if matches != 1:
            missingstops[stop.text] = matches
            done = 0

        stopids.append((matchid, direction))

    if not done:
        continue

    prev = (0, "foo")
    ways = []
    for id, direction in stopids:
        if prev[1] == "foo":
            if circular:
                prev = stopids[-1]
            else:
                prev = (id, direction)
                continue

        dir = direction
        if prev[1] != "both":
            dir = prev[1]

        paths = dijkstra(prev[0], id)
        if len(paths) != 1:
            done = 0
            noroute[(prev[0], id)] = len(paths)
            break
        segment = paths[0]
        #print (segment, "for", osmstops[id][1]["name"])####

        if ways and ways[-1][0] != segment[0] and (
                not isatend(prev[0], ways[-1][0]) or
                not isatend(prev[0], segment[0])):
            done = 0
            if not isatend(prev[0], ways[-1][0]):
                tosplit[(prev[0], ways[-1][0])] = 1
            if not isatend(prev[0], segment[0]):
                tosplit[(prev[0], segment[0])] = 1
            break

        if ways and ways[-1][0] == segment[0]:
            if isatend(prev[0], segment[0]):
                done = 0
                noroute[(prev[0], id)] = 0
                break

            if ways[-1][1] == "both":
                ways[-1][1] = dir
            segment = segment[1:]

        for way in segment:
            ways.append((way, dir))

        prev = (id, direction)

    if not done:
        continue

    if circular:
        if ways[0][0] == ways[-1][0]:
            ways = ways[:-1]

            if isatend(prev[0], ways[0][0]):
                noroute[(prev[0], stopids[0][0])] = 0
                continue
        elif not isatend(prev[0], ways[0][0]) or \
                not isatend(prev[0], ways[-1][0]):
            if not isatend(prev[0], ways[0][0]):
                tosplit[(prev[0], ways[0][0])] = 1
            if not isatend(prev[0], ways[-1][0]):
                tosplit[(prev[0], ways[-1][0])] = 1
            continue

    deways = []
    role = {}
    for way in ways:
        if way[0] in role:
            if role[way[0]] == "forward" and way[1] == "backward":
                role[way[0]] = ""
            elif role[way[0]] == "backward" and way[1] == "forward":
                role[way[0]] = ""
            else:
                sys.stderr.write(("Way %s is more than once with the same " +
                        "role in route %s!\n") % (way[0], tags["ref"]))
        else:
            deways.append(way[0])
            if way[1] == "both":
                role[way[0]] = ""
            else:
                role[way[0]] = way[1]
    for id, direction in stopids:
        if direction == "both":
            role[id] = ""
        else:
            role[id] = direction + ":stop"

    id = 0
    if tags["ref"] in osmroutes:
        same = 1

        for tag in tags:
            if tags not in osmroutes[tags["ref"]][1]:
                same = 0

        origstops = []
        origways = []
        origrels = []
        origrole = {} # Assuming unique IDs across n/w/r.. yes, I know
        for elem in osmroutes[tags["ref"]][0]:
            if elem.tag != "member" or "type" not in elem.attrib or \
                    "ref" not in elem.attrib:
                continue

            origrole[elem.attrib["ref"]] = elem.attrib["role"]

            if elem.attrib["type"] == "node":
                origstops.append(elem.attrib["ref"])
            elif elem.attrib["type"] == "way":
                origways.append(elem.attrib["ref"])
            elif elem.attrib["type"] == "relation":
                origrels.append(elem.attrib["ref"])

        if len(stopids) != len(origstops):
            same = 0
        else:
            for i, stop in enumerate(stopids):
                if origstops[i] != stop[0]:
                    same = 0
                    break

        if len(deways) != len(origways):
            same = 0
        elif same:
            for i, way in enumerate(deways):
                if origways[i] != way:
                    same = 0
                    break

        if same:
            continue

        for tag in osmroutes[tags["ref"]][1]:
            tags[tag] = osmroutes[tags["ref"]][1][tag]

        addrel("modify", osmroutes[tags["ref"]][0].attrib["id"],
                osmroutes[tags["ref"]][0].attrib["version"],
                tags, role, deways, stopids, origrels)
    else:
        addrel("create", str(newid), "1", tags, role, deways, stopids, [])
        newid -= 1

for ref in osmroutes:
    if ref not in touched:
        addrel("delete", osmroutes[ref][0].attrib["id"],
                osmroutes[ref][0].attrib["version"], {}, {}, [], [], [])

ElementTree.ElementTree(outroot).write("routes.osm", "utf-8")

for id in missingstops:
    sys.stderr.write("%i matches for stop %s!\n" % (missingstops[id], id))

for a, b in noroute:
    sys.stderr.write("%i routes from %s to %s!\n" % (noroute[(a, b)], a, b))

for node, way in tosplit:
    sys.stderr.write("Way %s needs to be split at node %s!\n" % (way, node))
