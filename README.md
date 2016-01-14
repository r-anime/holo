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
:--|:-:|:--
Find new episodes|high|python holo.py -s anime
Update shows|med|python holo.py -m showupdate
Find new show|low (or manual)|python holo.py -m showfind

### `config.ini` template

```ini
[data]
database = database.sqlite

[connection]
useragent = script:Holo, /r/anime episode discussion wolf:v0.1

[reddit]
subreddit = 
username = 
password = 
oauth_key = 
oauth_secret = 

[post]
title = [Spoilers] {show_name} - Episode {episode} discussion
body = 
	*{show_name}*, episode {episode}: {episode_name}
	
	{spoiler}
	
	---
	
	**Streams**
	
	{streams}
	
	**Show information**
	
	{links}

format_spoiler = **Reminder: Do not discuss plot points not yet seen in the show.**
format_stream = * [{service_name}]({stream_link})
format_link = * [{site_name}]({link})
```
