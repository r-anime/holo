![Holo, of course.](holo.png)

# Holo
Anime episode discussion post bot for [/r/anime](https://reddit.com/r/anime/). Monitors online stream services for newly published episodes and submits a post for each to Reddit. Posting to Lemmy communities is also available.

Currently operates under the account [/u/AutoLovepon](https://www.reddit.com/user/AutoLovepon/). (Previously [/u/Holo_of_Yoitsu](https://www.reddit.com/user/Holo_of_Yoitsu/))

Season configurations (show names and associated service URLs for each anime season) can be found in `season_configs`. Each can be loaded using the `edit` module.

## Requirements
* Python 3.5+
* `requests`
* `feedparser`
* `beautifulsoup4`
* `praw`
* `praw-script-oauth`
* `pythorhead`
* `unidecode`
* `pyyaml`

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

## Quick setup for local development

1. Update config file with your desired useragent and reddit details. Make sure the subreddit you're posting to is a personal test subreddit. You can generate a Reddit OAuth key by [following the steps in the Getting Started section](https://github.com/reddit-archive/reddit/wiki/OAuth2#getting-started) of their GitHub wiki.

```
[connection]
useragent = useragent_to_use

[reddit]
subreddit = my_test_subreddit
username = test_reddit_account
password = test_reddit_account_password
oauth_key = reddit_oath_key
oauth_secret = reddit_oath_key_secret
```

2. Set up the database by running `python src/holo.py -m setup`
3. Load the desired season config files by running `python src/holo.py -m edit season_configs/[season]_[year].yaml`
4. Update the show information by running `python src/holo.py -m update`
5. Enable flairs on test subreddit
6. The bot is now ready to post threads with `python src/holo.py`
