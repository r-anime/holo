![Holo, of course.](holo.png)

# Holo
Anime episode discussion post bot for [/r/anime](https://reddit.com/r/anime/). Monitors online stream services for newly published episodes and submits a post for each to Reddit.

Currently operates under the account [/u/Holo_of_Yoitsu](https://www.reddit.com/user/Holo_of_Yoitsu/).

Season configurations (show names and associated service URLs for each anime season) can be found in `season_configs`. Each can be loaded using the `edit` module.

## Requirements
* Python 3.5+
* `requests`
* `feedparser`
* `beautifulsoup4`
* `praw`
* `praw-script-oauth`
* `unidecode`

## Design notes
* Partitioned into multiple self-contained runnable modules
* Runs once and exits to play nice with schedulers
* Source sites (Crunchyroll, Funimation, Nyaa) are self-contained with a common interface

### Modules

Name|Run freq|Command
:--|:-:|:--
Find new episodes|high|python holo.py -s [subreddit]
Update shows|med|python holo.py -m update
Find new show|low (or manual)|python holo.py -m find
Edit shows|manual|python holo.py -m edit [show-config]
Setup database|once|python holo.py -m setup
