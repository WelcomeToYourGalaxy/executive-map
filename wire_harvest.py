#!/usr/bin/env python3
"""
wire_harvest.py  --  Global Wire harvester for the EXECUTIVE-accountability map.

Fetches a rotating set of open RSS feeds, keeps only items relevant to the
EXECUTIVE branch (cabinets / agencies / decrees / oversight / procurement /
transparency ...), drops small single-incident noise, scores by significance,
de-duplicates, and merges into wire_archive.json (capped at 2000, newest first).

No API key, no account, no cost. Run locally or via GitHub Actions (see
.github/workflows/wire.yml). Requires: feedparser  (pip install feedparser)

    python3 wire_harvest.py            # harvest + merge into wire_archive.json
"""
import json, time, calendar, re, sys, os
try:
    import feedparser
except ImportError:
    sys.exit("Install feedparser first:  pip install feedparser")

ARCHIVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wire_archive.json")
CAP = 2000

FEEDS = [
    ("100Reporters", "https://100r.org/feed/"),
    ("Abzas Media", "https://abzas.org/en/rss.xml"),
    ("African Network of Centers for Investigative Reporting (ANCIR)", "https://investigate.africa/feed"),
    ("Agência Pública", "https://apublica.org/feed/"),
    ("Alqatiba", "https://alqatiba.com/feed/"),
    ("amaBhungane Centre for Investigative Journalism", "https://amabhungane.org/feed/"),
    ("Arab Reporters for Investigative Journalism (ARIJ)", "http://en.arij.net/feed"),
    ("Armando.info", "https://armando.info/feed/"),
    ("atlatszo.hu", "https://atlatszo.hu/feed/"),
    ("Balkan Investigative Reporting Network (BIRN)", "https://birn.eu.com/feed/"),
    ("Bellingcat", "https://www.bellingcat.com/feed"),
    ("Bihus.info", "https://bihus.info/feed"),
    ("Bivol.bg", "https://bivol.bg/feed"),
    ("Bolts", "https://boltsmag.org/feed"),
    ("BudgIT", "https://budgit.org/feed/"),
    ("Byline Times", "https://bylinetimes.com/feed/"),
    ("CAinfo (Centro de Archivo y Acceso a la Información Pública)", "http://cainfo.org.uy/feed"),
    ("Carter Center — Election Standards", "https://electionstandards.cartercenter.org/feed/"),
    ("Center for Investigative Journalism of Montenegro (CIN-CG)", "http://www.cin-cg.me/feed"),
    ("Center for Investigative Journalism of Serbia (CINS)", "https://www.cins.rs/web-stories/feed/"),
    ("Center for Investigative Reporting (CIN)", "https://cin.ba/feed/"),
    ("Center for Investigative Reporting (Reveal)", "https://revealnews.org/feed/"),
    ("Center for Investigative Reporting, Sri Lanka", "https://cir.lk/feed/"),
    ("Center for Public Integrity", "https://publicintegrity.org/feed/"),
    ("Centre for Investigative Journalism Malawi (CIJM)", "https://www.investigative-malawi.org/feed/"),
    ("Centro de Periodismo Investigativo — Puerto Rico", "https://periodismoinvestigativo.com/feed/"),
    ("Centro Latinoamericano de Investigación Periodística (CLIP)", "https://www.elclip.org/feed/"),
    ("Chronicles.Media", "https://chronicles.media/feed/"),
    ("CIPER — Centro de Investigación Periodística", "https://www.ciperchile.cl/feed/"),
    ("Civil Discourse (Joyce Vance)", "https://joycevance.substack.com/feed"),
    ("Coda Media", "https://www.codastory.com/feed/"),
    ("Confidencial", "https://confidencial.digital/feed"),
    ("Congressional Dish (Jennifer Briney)", "https://congressionaldish.com/feed"),
    ("Connectas", "https://www.connectas.org/feed/"),
    ("Context.ro", "https://context.ro/feed/"),
    ("CONVOCA", "https://convoca.pe/rss.xml"),
    ("CORRECTIV", "https://www.correctiv.org/feed"),
    ("Crimean Center for Investigative Journalism", "http://investigator.org.ua/feed"),
    ("CU Sens", "https://cusens.md/ro/feed/"),
    ("Cyprus Investigative Reporting Network (CIReN)", "http://www.ciren.cy/feed"),
    ("Czech Centre for Investigative Journalism", "https://www.investigace.cz/feed/"),
    ("Danwatch", "https://danwatch.dk/en/feed/"),
    ("Data Cameroon", "https://datacameroon.com/feed/"),
    ("DCReport", "https://www.dcreport.org/feed/"),
    ("Declassified UK", "https://www.declassifieduk.org/feed/"),
    ("Direkt36", "http://www.direkt36.hu/en/feed"),
    ("DISCLOSE", "https://disclose.ngo/feed/?lang=en"),
    ("Drop Site News", "https://www.dropsitenews.com/feed"),
    ("El Surtidor", "https://elsurti.com/feed"),
    ("Election Law Blog (Rick Hasen)", "https://electionlawblog.org/?feed=rss2"),
    ("emptywheel (Marcy Wheeler)", "https://emptywheel.net/feed/"),
    ("Environmental Investigative Forum", "https://eiforum.org/feed/"),
    ("Epicentro.TV", "https://epicentro.tv/rss/global.xml"),
    ("Fiquem Sabendo", "https://fiquemsabendo.com.br/rss/"),
    ("Follow the Money", "https://www.ftm.eu/feed"),
    ("Forbidden Stories", "https://forbiddenstories.org/feed/"),
    ("FrontStory / Fundacja Reporterów", "https://frontstory.pl/feed/"),
    ("Fundación Ciudadana Civio", "http://www.civio.es/feed.xml"),
    ("GIJN — Global Investigative Journalism Network", "https://gijn.org/rss"),
    ("Global Reporting Center", "https://globalreportingcentre.org/feed/"),
    ("HETQ — Investigative Journalists of Armenia", "https://hetq.am/en/rss"),
    ("ICIJ — International Consortium of Investigative Journalists", "https://www.icij.org/feed"),
    ("IDL-Reporteros", "https://www.idl-reporteros.pe/feed/"),
    ("inewsource", "https://inewsource.org/feed/"),
    ("Inhlase Centre for Investigative Journalism", "https://inhlase.com/feed/"),
    ("Inkyfada", "https://inkyfada.com/fr/feed/"),
    ("InSight Crime", "https://insightcrime.org/feed/"),
    ("Instituto Prensa y Sociedad (IPYS)", "http://www.ipys.org/rss.xml"),
    ("International Centre for Investigative Reporting (ICIR)", "https://www.icirnigeria.org/feed/"),
    ("Investico", "https://www.platform-investico.nl/feed"),
    ("Investigative Center of Jan Kuciak (ICJK)", "https://www.icjk.sk/rss"),
    ("Investigative Journalism Bureau", "https://ijb.utoronto.ca/feed/"),
    ("Investigative Journalism Center of Moldova", "https://anticoruptie.md/ro/feed"),
    ("Investigative Reporting Denmark", "https://www.ir-d.dk/feed/"),
    ("Investigative Reporting Lab Macedonia", "https://irl.mk/mk/feed/"),
    ("Investigative Reporting Workshop", "http://investigativereportingworkshop.org/feed"),
    ("IStories (Important Stories)", "https://istories.media/rss/all.xml"),
    ("iWatch Africa", "http://iwatchafrica.org/feed/"),
    ("JARING", "https://jaring.id/feed/"),
    ("Just Security", "https://www.justsecurity.org/feed/"),
    ("Kloop Media", "https://kloop.kg/feed/"),
    ("KRIK — Crime and Corruption Reporting Network", "https://www.krik.rs/feed/"),
    ("La Maison des Reporters", "https://lamaisondesreporters.sn/feed/"),
    ("Lighthouse Reports", "https://www.lighthousereports.com/feed/"),
    ("LUPA — Crime and Corruption Reporting Network", "https://lupa.co.me/feed/"),
    ("Mada Masr", "https://www.madamasr.com/en/feed"),
    ("Maka Angola", "https://www.makaangola.org/feed/"),
    ("Makanday", "https://makanday.org/feed/"),
    ("Maldita.es", "https://maldita.es/feed"),
    ("MapLight", "https://www.maplight.org/blog-feed.xml"),
    ("Mexicanos Contra la Corrupción y la Impunidad (MCCI)", "https://contralacorrupcion.mx/feed/"),
    ("Midwest Center for Investigative Reporting", "https://investigatemidwest.org/feed/"),
    ("Mikroskop Media", "https://mikroskopmedia.com/feed/"),
    ("Ministério Público – Amapá", "https://www.mpap.mp.br/rss"),
    ("Ministério Público – Ceará", "https://mpce.mp.br/feed/"),
    ("Ministério Público – Maranhão", "https://www.mpma.mp.br/feed"),
    ("Ministério Público – Paraíba", "https://www.mppb.mp.br/rss"),
    ("MNN Centre for Investigative Journalism", "https://lescij.org/feed/"),
    ("MPDFT (Ministério Público)", "https://www.mpdft.mp.br/portal/index.php?format=feed&type=rss"),
    ("MUSEBA Journalism Project", "https://www.themusebaproject.org/feed/"),
    ("Nashi Groshi (“Our Money”)", "https://nashigroshi.org/feed/"),
    ("Nikolaev Center for Investigative Reporting (NikCIR)", "https://nikcenter.org/feed/"),
    ("Notes on the Crises (Nathan Tankus)", "https://www.crisesnotes.com/rss/"),
    ("OCCRP — Organized Crime & Corruption Reporting Project", "https://www.occrp.org/en/feed"),
    ("openDemocracy", "https://www.opendemocracy.net/rss/"),
    ("Ortak", "https://ortak.org/feed/"),
    ("Oxpeckers", "https://oxpeckers.org/feed/"),
    ("Oštro", "https://ostro.si/feed/"),
    ("Periodismo de Barrio", "https://periodismodebarrio.org/feed/"),
    ("Philippine Center for Investigative Journalism (PCIJ)", "https://pcij.org/feed/"),
    ("Plaza Pública", "https://plazapublica.com.gt/feed/"),
    ("Pod črto", "https://podcrto.si/feed"),
    ("Popular Information (Judd Legum)", "https://popular.info/feed"),
    ("Prachatai", "https://prachatai.com/feed"),
    ("Proekt (The Project)", "https://www.proekt.media/feed/"),
    ("ProPublica", "https://www.propublica.org/feeds/propublica/main"),
    ("Public Herald", "https://publicherald.org/feed/"),
    ("Quinto Elemento Lab", "https://quintoelab.org/feed"),
    ("Rappler / Newsbreak", "https://www.rappler.com/feed/"),
    ("Re:Baltica — Baltic Centre for Investigative Journalism", "https://rebaltica.lv/feed/"),
    ("REFLEKT", "http://reflekt.ch/api/rss-feed"),
    ("REJI-RDC", "https://www.reji-rdc.org/feed/"),
    ("Reporters United", "https://www.reportersunited.gr/feed/"),
    ("Republik", "https://www.republik.ch/feed.xml"),
    ("Repórter Brasil", "https://reporterbrasil.org.br/feed/"),
    ("RISE Moldova", "https://www.rise.md/feed/"),
    ("RISE Project", "http://www.riseproject.ro/feed"),
    ("SCOOP-Macedonia", "http://scoop.mk/feed/"),
    ("Siena", "https://www.siena.lt/blog-feed.xml"),
    ("SIRAJ — Syrian Investigative Reporting for Accountability Journalism", "https://sirajsy.net/ar/feed"),
    ("Slidstvo.info", "https://www.slidstvo.info/feed/"),
    ("Sludge", "https://readsludge.com/rss/"),
    ("Solomon", "https://wearesolomon.com/feed/"),
    ("Studio Monitor", "https://monitori.ge/feed"),
    ("Tansa — Tokyo Investigative Newsroom", "https://en.tansajp.org/rss.xml"),
    ("Temirov Live", "https://www.youtube.com/feeds/videos.xml?channel_id=UCpZtteaL03_LrVORzSfxwZg"),
    ("Texas Observer", "https://www.texasobserver.org/feed/"),
    ("Texty.org.ua — Data Journalism Agency", "http://texty.org.ua/feed.xml"),
    ("The Bristol Cable", "https://thebristolcable.org/feed"),
    ("The Centre for Climate Reporting", "https://climate-reporting.org/feed/"),
    ("The Elephant", "https://www.theelephant.info/feed/"),
    ("The Ferret", "https://www.theferret.scot/latest/rss/"),
    ("The Investigative Desk", "https://investigativedesk.com/feed/"),
    ("The Lever", "https://www.levernews.com/rss/"),
    ("The Marshall Project", "https://www.themarshallproject.org/rss/recent"),
    ("The Public Source", "https://thepublicsource.org/feed"),
    ("The Reporter (Taiwan)", "https://www.twreporter.org/a/rss2.xml"),
    ("The War Horse", "https://thewarhorse.org/feed/"),
    ("Turkmen.News", "https://turkmen.news/feed/"),
    ("Type Investigations", "https://typeinvestigations.org/feed"),
    ("Viewfinder", "https://viewfinder.org.za/feed/"),
    ("Watershed Investigations", "https://watershedinvestigations.com/feed"),
    ("Wisconsin Watch", "https://wisconsinwatch.org/feed/"),
    ("Wole Soyinka Centre for Investigative Journalism", "https://wscij.org/feed/"),
    ("Ziarul de Gardă", "https://www.zdg.md/feed"),
    ("Átlátszó Erdély", "https://atlatszo.ro/feed/")
]

# --- executive-relevance filter: an item must hit one of these ---
EXEC_TERMS = ['executive','cabinet','minister','ministry','prime minister','president',
 'presidential','head of state','head of government','chancellor','decree','executive order',
 'ordinance','directive','regulation','regulator','agency','government agency','civil service',
 'appointment','appointed','nominat','reshuffle','procurement','state contract','audit','auditor',
 'anti-corruption','corruption','ombudsman','integrity commission','freedom of information',
 'right to information','transparency','disclosure','lobby','lobbying','beneficial ownership',
 'conflict of interest','asset declaration','emergency powers','administration','gazette',
 'official journal','watchdog','oversight','governor','public official','graft','embezzle',
 'state capture','abuse of power','autocra','strongman','coup','impeach']

STOP = ["football","soccer","celebrity","royal wedding","recipe","horoscope","box office",
 "fashion","obituary","weather forecast","sports","webinar","register now","register here",
 "join us","save the date","rsvp","upcoming event","panel discussion","podcast episode",
 "watch live","giveaway","sponsored"]

BIG = ["reform","overhaul","sweeping","landmark","historic","nationwide","decree","executive order",
 "regulation","agency","minister","cabinet","president","audit","procurement","inquiry","probe",
 "investigation","ruling","commission","government","federal","billion","crackdown","anti-corruption",
 "emergency powers","reshuffle","watchdog","ombudsman","impeach"]
SMALL = ["councillor","local council","mayor of","resign","quit","stepped down","arrested",
 "charged with","jailed","apolog","expenses claim","affair","wedding","tweeted","gaffe","insult",
 "feud","hospital"," dies","obituary","health scare","by-election","personal"]

def _txt(it):
    return ((it.get("title") or "") + " " + (re.sub("<[^>]+>","",it.get("summary") or ""))).strip()

def _has_exec(s):
    s = " " + s.lower() + " "
    return any(w in s for w in EXEC_TERMS)

def _sig(s):
    s = " " + s.lower() + " "; sc = 0
    for w in BIG:
        if w in s: sc += 2
    for w in SMALL:
        if w in s: sc -= 3
    for w in EXEC_TERMS:
        if w in s: sc += 1
    return sc

def _date(it):
    for k in ("published_parsed","updated_parsed"):
        t = it.get(k)
        if t:
            try: return int(calendar.timegm(t) * 1000)
            except Exception: pass
    return int(time.time() * 1000)

def load_archive():
    try:
        with open(ARCHIVE, encoding="utf-8") as f:
            a = json.load(f)
            return a if isinstance(a, list) else []
    except Exception:
        return []

def main():
    archive = load_archive()
    seen = {x.get("link") for x in archive}
    added = 0
    for name, url in FEEDS:
        try:
            d = feedparser.parse(url)
        except Exception as e:
            print("  ! %-24s %s" % (name, e)); continue
        n_feed = 0
        for it in d.entries:
            link = it.get("link")
            if not link or link in seen:
                continue
            txt = _txt(it)
            low = " " + txt.lower() + " "
            if any(w in low for w in STOP):
                continue
            if not _has_exec(txt):
                continue
            sig = _sig(txt)
            if sig < 1:                       # drop weak / single-keyword noise
                continue
            archive.append({
                "name": name,
                "title": (it.get("title") or "").strip(),
                "link": link,
                "date": _date(it),
                "sig": sig,
            })
            seen.add(link); added += 1; n_feed += 1
        if n_feed:
            print("  + %-26s %d" % (name, n_feed))
    archive.sort(key=lambda x: x.get("date", 0), reverse=True)
    archive = archive[:CAP]
    with open(ARCHIVE, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, separators=(",", ":"))
    print("\nHarvest complete: +%d new, %d total in wire_archive.json" % (added, len(archive)))

if __name__ == "__main__":
    main()
