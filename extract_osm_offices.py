#!/usr/bin/env python3
"""Pull government offices out of the OpenStreetMap planet, with contact
details, using the QLever SPARQL endpoint over osm-planet.

Why not Overpass: a global query for every town hall on Earth times out on
the public Overpass instances. QLever answers the same question over the
whole planet in seconds.

Why this script exists at all: the previous extract stopped at index 5
(lat, lon, name, website, operator, address). It never asked for a phone
or an email, so build_contacts_cells.py -- which reads r[7] and r[8] --
found nothing there, and the map showed a phone on 0.2% of offices. OSM
actually carries contact:phone on 18.5% of town halls and contact:email on
19.0%, and those prefixed forms are the COMMONER ones. Both forms are
read here.

Output schema, one row per office:
  0 lat  1 lon  2 name  3 website  4 operator  5 address
  6 phone  7 email  8 opening_hours  9 wikidata
Trailing empties are trimmed off each row to keep the files small.
"""
import json, sys, time, urllib.parse, urllib.request

EP = 'https://qlever.cs.uni-freiburg.de/api/osm-planet'

# Same selectors the earlier extract used, verified against QLever counts.
KINDS = {
    'townhall':    ('amenity', 'townhall'),
    'govoffice':   ('office', 'government'),
    'ministry':    ('government', 'ministry'),
    'police':      ('amenity', 'police'),
    'firestation': ('amenity', 'fire_station'),
    'prison':      ('amenity', 'prison'),
    'diplomatic':  ('office', 'diplomatic'),
}

Q = """
PREFIX osmkey: <https://www.openstreetmap.org/wiki/Key:>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
SELECT ?name (geof:centroid(?g) AS ?c) ?web ?cweb ?oper ?hno ?street ?city ?post
       ?full ?phone ?cphone ?email ?cemail ?hours ?wd WHERE {
  ?s osmkey:%(key)s "%(val)s" ; osmkey:name ?name ; geo:hasGeometry/geo:asWKT ?g .
  OPTIONAL { ?s osmkey:website ?web }
  OPTIONAL { ?s <https://www.openstreetmap.org/wiki/Key:contact:website> ?cweb }
  OPTIONAL { ?s osmkey:operator ?oper }
  OPTIONAL { ?s <https://www.openstreetmap.org/wiki/Key:addr:housenumber> ?hno }
  OPTIONAL { ?s <https://www.openstreetmap.org/wiki/Key:addr:street> ?street }
  OPTIONAL { ?s <https://www.openstreetmap.org/wiki/Key:addr:city> ?city }
  OPTIONAL { ?s <https://www.openstreetmap.org/wiki/Key:addr:postcode> ?post }
  OPTIONAL { ?s <https://www.openstreetmap.org/wiki/Key:addr:full> ?full }
  OPTIONAL { ?s osmkey:phone ?phone }
  OPTIONAL { ?s <https://www.openstreetmap.org/wiki/Key:contact:phone> ?cphone }
  OPTIONAL { ?s osmkey:email ?email }
  OPTIONAL { ?s <https://www.openstreetmap.org/wiki/Key:contact:email> ?cemail }
  OPTIONAL { ?s osmkey:opening_hours ?hours }
  OPTIONAL { ?s osmkey:wikidata ?wd }
}
ORDER BY ?s
LIMIT %(lim)d OFFSET %(off)d
"""

def ask(q, tries=4):
    for i in range(tries):
        try:
            u = EP + '?query=' + urllib.parse.quote(q)
            r = urllib.request.Request(u, headers={
                'Accept': 'text/tab-separated-values',
                'User-Agent': 'WelcomeToYourGalaxy-executive-map/1.0'})
            return urllib.request.urlopen(r, timeout=600).read().decode('utf-8', 'replace')
        except Exception as e:
            if i == tries - 1:
                raise
            sys.stderr.write('  retry %d after %s\n' % (i + 1, e))
            time.sleep(8 * (i + 1))

def unq(v):
    """TSV cells arrive as RDF terms: "text"@en, "text", <iri>, or empty."""
    v = v.strip()
    if not v:
        return ''
    if v.startswith('<') and v.endswith('>'):
        return v[1:-1]
    if v.startswith('"'):
        e = v.rfind('"')
        if e > 0:
            v = v[1:e]
    return v.replace('\\n', ' ').replace('\\t', ' ').replace('\\"', '"').strip()

def point(wkt):
    w = unq(wkt)
    if 'POINT(' not in w:
        return None
    try:
        lon, lat = w.split('POINT(', 1)[1].split(')', 1)[0].split()
        lat, lon = float(lat), float(lon)
    except Exception:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return round(lat, 5), round(lon, 5)

def addr(hno, street, city, post, full):
    if full:
        return full
    line = ' '.join(x for x in (hno, street) if x)
    tail = ' '.join(x for x in (post, city) if x)
    return ', '.join(x for x in (line, tail) if x)

PAGE = 120000

def pull(kind, key, val):
    rows, off = [], 0
    while True:
        txt = ask(Q % {'key': key, 'val': val, 'lim': PAGE, 'off': off})
        lines = txt.split('\n')
        if lines and lines[0].startswith('?'):
            lines = lines[1:]
        got = 0
        for ln in lines:
            if not ln.strip():
                continue
            f = ln.split('\t')
            if len(f) < 17:
                f += [''] * (17 - len(f))
            got += 1
            pt = point(f[1])
            if not pt:
                continue
            name = unq(f[0])
            if not name:
                continue
            rec = [pt[0], pt[1], name,
                   unq(f[2]) or unq(f[3]),                       # website
                   unq(f[4]),                                    # operator
                   addr(unq(f[5]), unq(f[6]), unq(f[7]), unq(f[8]), unq(f[9])),
                   unq(f[11]) or unq(f[10]),                     # phone, contact: first
                   unq(f[13]) or unq(f[12]),                     # email, contact: first
                   unq(f[14]),                                   # opening_hours
                   unq(f[15])]                                   # wikidata
            while len(rec) > 3 and rec[-1] == '':
                rec.pop()
            rows.append(rec)
        print('  %s: +%d (kept %d)' % (kind, got, len(rows)), flush=True)
        if got < PAGE:
            break
        off += PAGE
    return rows

if __name__ == '__main__':
    only = sys.argv[1:] or list(KINDS)
    for kind in only:
        key, val = KINDS[kind]
        rows = pull(kind, key, val)
        out = 'offices_%s.json' % kind
        json.dump(rows, open(out, 'w'), ensure_ascii=False, separators=(',', ':'))
        f = sum(1 for r in rows if len(r) > 7 and r[7])
        p = sum(1 for r in rows if len(r) > 6 and r[6])
        print('%s -> %s  rows %d  phone %d  email %d' % (kind, out, len(rows), p, f), flush=True)
