# Sites

One folder per source. The rest of the program discovers them through the `SITES` list in
`src/sites/__init__.py`: nothing else has to be edited to add a site.

```
src/sites/
├── __init__.py        SITES = [...]  and  site_for_url(url)
├── base.py            the Site dataclass: what a site has to provide
├── _utils.py          small helpers shared by the sites (dedupe)
└── <site>/
    ├── __init__.py    SITE = Site(...)  (name, domain, order, functions, season URL pattern)
    ├── search.py      search(queries, headers)             -> [{"title", "url", "support", "site"}]
    ├── seasons.py     expand(url, headers)                 -> [{"name": "Saison N", "url": ...}]
    ├── episodes.py    fetch_episodes(base_url, headers, wanted_episodes)
    │                                                       -> {"Player (LANG)": [url_ep1, url_ep2, None, ...]}
    └── metadata.py    anime_name(base_url), alt_titles(base_url, headers), season_info(base_url)
```

## How a URL travels

```
search()   -> result["url"]            (the URL of one anime; you build it, you may put an id in it)
expand()   -> [{"name", "url"}, ...]   (one URL per season)
fetch_episodes(season_url, ...)        (the players' links, one list per player and language)
```

Only the URL goes from one step to the next, so anything a later step needs (an id, a title) has to be
in the URL you build.

## Adding a site

1. Copy a site folder close to yours (`french_manga/` for an HTML + small JSON API site, `franime/` for a JSON API).
2. Fill in `search.py`, `seasons.py`, `episodes.py`, `metadata.py`.
3. Describe it in `__init__.py` (`SITE = Site(...)`). `season_url_pattern` must match a **season** URL and
   nothing else: `main.py` uses it to know whether to ask for the season.
4. Add `<site>.SITE` to `SITES` in `src/sites/__init__.py`.
5. A new video host: add its domains to `SourceDomains` in `src/var.py` and an extractor in
   `src/utils/extract/`, then the dispatch in `src/utils/fetch/fetch_video_source.py`.

## Return format of `fetch_episodes`

* one key per player and language: `"Vidzy (VF)"`, `"Vidzy (VOSTFR)"`, `"Sibnet 2 (VOSTFR)"`;
* each value is a list of links, one slot per episode of the **whole season**: slot `i` is episode `i + 1`,
  `None` when that player has no link for that episode;
* return `None` when nothing was found.
