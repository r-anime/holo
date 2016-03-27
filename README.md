![Holo, of course.](holo.png)

# Holo
New episode discussion bot for /r/anime.

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
