@echo off
cd ..\..

echo === Running initial setup

echo == Installing dependencies
py -m pip install -r requirements.txt
echo == Dependencies installed


echo == Running database setup
py src\holo.py -m setup
echo == Database setup complete

pause
