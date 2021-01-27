# Spafbi's Python 3.x module and CLI for Miscreated RCON
I am not a (good) programmer, but I do try to learn more as I can. I hacked this together from multiple sources and a lot of trial and error. I hope you find it useful. Feel free to submit optimizations and bug fixes.
## Module usage example
### Python code
Note: For this example, the `misrcon.py` file was placed in the same directory as this code snippet.
```python
from misrcon import MiscreatedRCON

# This dictionary contains the required RCON connection information
rcon_config = {'host': '127.0.0.1',
               'port': 64094,
               'password': 'secret'}

# Create the RCON object using our config dictionary
this_rcon = MiscreatedRCON(**rcon_config)

# Send a command and assign the resulting dictionary to the 'result' variable
rcon_result = this_rcon.send_command(command='status')

# Print any returned errors
print('error: {0}'.format(rcon_result['error']))
# Print the boolean value for the success of the command
print('success: {0}'.format(rcon_result['success']))
# Print the returned value of the command as received from RCON
print('result: {0}'.format(rcon_result['returned']))
```
### Resulting text from the above code example
```
error: None
success: True
result: -----------------------------------------
Server Status:
name: My Super Cool Miscreated Server
ip: knight001
version: 1.0.1.1012
level: Multiplayer/islands
gamerules: Miscreated
time: 08:08
players: 2/36
round time remaining: 0:00
uptime: 06:08:27
next restart in: 05:49:46
weather: RainbowHalf
weatherpattern: 14
 -----------------------------------------
Connection Status:
steam: '76561112345678901'  name: 'Survivor'  entID:'719767' id: '10'  ip: '10.115.43.2:64090'  ping: '53'  state: '3'  profile: '0'
steam: '76561112345678902'  name: 'Joe'  entID:'653567' id: '12'  ip: '172.16.0.199:64090'  ping: '93'  state: '3'  profile: '0'
```
## Command-line (CLI) usage
### Executing against a locally running self-hosted Miscreated server
```bash
python3 misrcon.py -p secret -c "sv_chat This is a test... ignore me"
```
### Executing against a locally running self-hosted Miscreated server running on a non-default port (example: `-sv_port 54321`)
```bash
python3 misrcon.py --game-port 54321 -p secret -c "sv_chat This is a test... ignore me"
```
### Executing against a remote (ip address: `172.16.65.235`) Miscreated server with RCON listening on `64099`
```bash
python3 misrcon.py -s 172.16.65.235 --rcon-port 64099 -p secret -c "sv_chat This is a test... ignore me"
```
### Returned result from RCON for the above listed CLI usage examples
```
** Server: This is a test... ignore me **
```
