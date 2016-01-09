![Holo, of course.](holo.png)

# Holo
New episode discussion bot for /r/anime.

## Requirements
* Python 3.4+ (targeting 3.5)
* requests
* feedparser
* PRAW

## Design notes
* Partitioned into multiple self-contained runnable modules
* Runs once and exits to play nice with schedulers
* Source sites (Crunchyroll, Funimation, Nyaa) are self-contained with a common interface

### Modules

Name|Run freq|Command
-|-|-
Find new episodes|high|python holo.py
Update shows|med|python holo.py -m showupdate
Find new show|low (or manual)|python holo.py -m showfind
