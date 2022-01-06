# NOTE: This project has been deprecated due to Discord.py's discontinuation, and has been replaced with a Discord.js version that can be found here: https://github.com/harleywelsby/Battlebot.js

# BattleBot

This is a Discord bot that allows users to train in various "moves" and level them to fight in pokemon-style battles against other members of the server.

The program takes a CSV file of all moves that can be learned and a CSV of all players who have interacted with the game, and allows users to add moves to their set and level them up in order to fight eachother in a text-based combat system.

Please note that currently BattleBot is hosted from a private repository due to the need of a private bot token to run as a discord account. This repository will be updated alongside the private repository although it may at times be 1 or 2 commits behind.

## Currently working commands include: ##

### Training and Info: ###
- /moves mine - Displays the sender's moveset and move levels.
- /moves all - Displays every available move (Will later be adapted to show correct levels for moves the user already has).
- /moves (player) - Displays another player's moveset.
- /train (move) - Levels up a move after an amount of time has passed

### Utility & Admin: ###
- /save moves - Saves the table of moves to the 'moves.csv' file.
- /save players - Saves player data to 'players.csv'.
- /check training - Checks all moves-in-training for debugging
- /helpme - Shows all commands
- /wiki - Explains move types and modifiers
- /scoreboard - Displays player's wins and losses ordered by most wins

### Fight System: ###
- /fight cancel - Cancels an initialized fight.
- /fight (@person) - Challenges a user to a pokemon-style fight between two people, until someone hits 0hp.
- /fight accept - Accept the fight challenge from the above command to start.
- /attack (move) - Plays a move as the sender's turn during a fight sequence.

### Boss Fights: ###
- /bossfight - Start a boss fight lobby
- /bossfight join (@person) - Join a player's boss fight lobby
- /bossfight start - Start the boss fight
- /b (move) - Plays a move against the boss

### Other notable features: ###
- RNG Chances to miss attacks, scaling with move level. (Currently set to base 20% miss chance + level modifier).
- Move damage multiplier depends on last move played, eg: Last move was a punch, new move is a kick, the kick will do 1.5x damage.
- Status effects caused by certain moves which affect a player's next move.
- config.py with plug-and-play variables for custom boss fights, fight modifiers, status effect chances etc.
- Bossfights can be started with anywhere between 1 and 3 players, with adjusting lobby size if players get knocked out
