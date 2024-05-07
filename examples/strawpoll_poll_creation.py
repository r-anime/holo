# Example of automated poll submission to strawpoll.ai
# Last tested on 2023/10/07

import re
import requests

URL = "https://strawpoll.ai/poll-maker/"
DATA = (
    '{{"address":"","token":"{token}","type":"0",'
    '"questions":[{{"plurality":{{"isVoterOpts":false,"maxOpts":"10"}},'
    '"approval":{{"type":"0","value":"1","lower":"1","upper":"1"}},'
    '"range":{{"min":"1","max":"10"}},"integer":{{"min":"1","max":"10"}},'
    '"rational":{{"min":"1.0","max":"10.0"}},"type":"0",'
    '"title":"test question","opts":["answer 1","answer 2","answer 3"]}}],'
    '"settings":{{"reddit":{{"link":"0","comment":"200","days":"3"}},'
    '"limits":"3","isCaptcha":false,"isDeadline":false,"isHideResults":false,"deadline":null}}}}'
)

g = requests.get(URL, timeout=60)
match = re.search(r"<input type=\"hidden\" id=\"pm-token\" value=\"(\w+)\">", g.text)
assert match
token = match.group(1)
data = DATA.format(token=token)
cookies = {"PHPSESSID": g.headers["set-cookie"].split(";")[0].split("=")[1]}
p = requests.post(URL, data={"data": f"{data}"}, cookies=cookies, timeout=60)

print(p.history)
# History should be a list with a 302 response
print(p.url)
# Response URL should be https://strawpoll.ai/poll/vote/{poll_id}
