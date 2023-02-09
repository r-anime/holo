@echo off
cd ..\..

echo == "Do you want to first add the show to the database?
echo == If yes, you must put the valid config as "show.yaml" in the holo/ folder

choice
set ADD_SHOW=%ERRORLEVEL%

if %ADD_SHOW% EQU 1 goto add_show
if %ADD_SHOW% EQU 2 goto make_threads

:add_show
echo == Adding new show(s) from holo\show.yaml
py src\holo.py -m edit show.yaml
echo ==

:make_threads
set /p SHOW_NAME=Enter the show name (without quotes): 
set /p EPISODE_COUNT=Enter the number of episodes: 
set SUBREDDIT=bainos

choice /c 123 /m "What config file to use? [1] config.ini [2] config_secret.ini [3] enter a custom name "
set CONFIG_SELECT=%ERRORLEVEL%
if %CONFIG_SELECT% EQU 1 set CONFIG_FILE=config.ini
if %CONFIG_SELECT% EQU 2 set CONFIG_FILE=config_secret.ini
if %CONFIG_SELECT% EQU 3 set /p CONFIG_FILE=Enter the config file name: 

choice /m "Do you want to run in debug mode (do not make the threads)? "
set DEBUG_SELECT=%ERRORLEVEL%
if %DEBUG_SELECT% EQU 1 set DEBUG_FLAG=--debug
if %DEBUG_SELECT% EQU 2 set DEBUG_FLAG=

echo ==
echo Creating %EPISODE_COUNT% episodes for show %SHOW_NAME% on subreddit %SUBREDDIT%
pause

py src\holo.py %DEBUG_FLAG% -s %SUBREDDIT% -c %CONFIG_FILE% -m batch "%SHOW_NAME%" %EPISODE_COUNT%

pause
