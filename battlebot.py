# =============================================================
# || Python Battle Bot (Discord Bot for personal server)     ||
# =============================================================
# || AUTHOR: Harley Welsby, https://github.com/harleywelsby  ||
# =============================================================

#Discord API
import discord
from discord.ext import commands

#Functionality
import csv
import time
from random import randint

saveGap = 3600

#Extra .py files
import data      #Handles data storage & classes
import config    #Handles admin variables, plug-and-play boss fights, tunable features

#Bot command character
bot = commands.Bot(command_prefix='.')

#Essential data storage
ALL_MOVES = []
ACTIVE_FIGHTS = []
ACTIVE_TRAINING = set()

#Signs in the bot
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=config.activity)) #Set status message
    doFiles() #Load CSV data
    print('Ready and Logged in as {0.user}!'.format(bot))

# =============================================================
#                       Helper Functions
# =============================================================

#Get number of wins from object
def getWin(score):
    return int(score.wins)

#Load all CSVs into the game
def doFiles():
    
    #Initialize moves and players
    with open('moves.csv', 'r') as file:
        reader = csv.reader(file)

        i = int(1)

        for row in reader:
            #Get every second row
            if (i % 2) != 0:
                ALL_MOVES.append(data.Move(row[0],row[1],row[2],row[3]))
            i += 1

    with open('players.csv', 'r') as file:
        reader = csv.reader(file)

        count = int(1)

        for row in reader:
            if (count % 2) != 0:
                tempName = row[0]
                tempSet = row[1]
                tempWins = row[2]
                tempLoss = row[3]
                data.PLAYERDICT[str(tempName)] = data.Player(tempName, tempSet, tempWins, tempLoss)
            count += 1

    #Get all of the players moves into player objects
    for k in data.PLAYERDICT:

        p = data.PLAYERDICT[k]

        splitMoves = str(p.moveNames).split("|")
        tempMoves = []

        for name in splitMoves:
            if '' != name:
                if '\'}' not in name:
                    if '{\'' in name:
                        name = name.split("\'")[1]
                    level = name.split(" ")[0]
                    movename = name.split(" ")[1]
                    for m in ALL_MOVES:
                        if m.name.lower() in movename.lower():
                            tempMoves.append(data.Move(m.name, m.elem, m.hp, level))
                            break
        p.setMoves(tempMoves)

#Format move data (for .moves)
def getMoveInfo(move):
    
    toSend = ''
    
    toHit = move.getDamage()
    toSend += f'Dmg: {round(toHit,2)}\t Acc: '

    if move.getAccuracy() >= 0:
        toSend += '+'

    toSend += f'{move.getAccuracy()}\t {move.name}\t\t\t'
    
    #Status effects
    if str(move.name).lower() in config.concussListLOW or str(move.name).lower() in config.concussListHIGH or str(move.name).lower() in config.concussListMED:
        toSend += ' (% Concuss) '
    if str(move.name).lower() in config.windHIGH or str(move.name).lower() in config.windMED:
        toSend += ' (% Wind) '
    if str(move.name).lower() in config.blegVERYLOW:
        toSend += ' (% break own leg) '
    if str(move.name).lower() in config.barmHIGH:
        toSend += ' (% break arm) '
    if str(move.name).lower() == 'leg_kick':
        toSend += ' (% break leg) '
    toSend += '\n'
    
    return toSend

#Get a player's highest level move
def getHighestLevel(player):
    if str(player) in data.PLAYERDICT:
        p = data.PLAYERDICT[str(player)]
        highest = None
        for m in p.moves:
            if highest == None:
                highest = m
            elif highest.level < m.level:
                highest = m
        return highest
    else:
        return None

#Calculate all possible status effects in a move
async def doStatusEffects(player, opponent, m):

    #Chance to give person status effect
    playeruser = await bot.fetch_user(int(player.name))
    oppuser = await bot.fetch_user(int(opponent.name))
        
    sendeffect = ''
    giveEffect = randint(1,100)

    #Chance of concussing
    if ((giveEffect < config.HIGH_CHANCE and m.name.lower() in config.concussListHIGH) or
        (giveEffect < config.MED_CHANCE and m.name.lower() in config.concussListMED) or 
        (giveEffect < config.LOW_CHANCE and m.name.lower() in config.concussListLOW)):
        
        opponent.effect = 'concussion'
        sendeffect += f'{oppuser.mention} has been given a concussion!'                            
    
    #Chance of winding
    if ((m.name.lower() in config.windHIGH and giveEffect < config.HIGH_CHANCE) or
        (m.name.lower() in config.windMED and giveEffect < config.MED_CHANCE)):

        opponent.effect = 'winded'
        sendeffect += f'{oppuser.mention} has been winded!'
    
    #Chance of breaking arm
    elif m.name.lower() in config.barmHIGH and giveEffect < config.HIGH_CHANCE:
        
        opponent.effect = 'broken_arm'
        sendeffect += f'{oppuser.mention}\'s arm has snapped!'

    #Chance of breaking leg
    elif m.name.lower() == 'leg_kick' and giveEffect < config.HIGH_CHANCE:
        
        opponent.effect = 'broken_leg'
        sendeffect += f'{oppuser.mention}\'s leg has snapped!'
    
    #Chance of breaking own leg from a kick (Stacks with opponent effects)
    if m.name.lower() in config.blegVERYLOW and giveEffect < config.SELF_CHANCE:
        
        player.effect = 'broken_leg'
        sendeffect += f'{playeruser.mention} kicked too hard and their leg snapped!'

    #Chance of being hit with adrenaline
    if opponent.effect == None:
        
        rushroll = randint(1,100)
        rushroll -= float(m.getDamage()/2) #How much opponent hit by effects adrenaline rush chances
        
        if rushroll < config.RUSH_CHANCE:
            opponent.effect = 'rush'
            sendeffect += f'{oppuser.mention} has been hit with an adrenaline rush! Anything is possible!'
    
    return sendeffect

#Get the health bar string
def doHealthBar(fight, player):

    health = 0
    if str(player) == fight.player1:
        health = fight.p1health
    else:
        health = fight.p2health

    healthbar = ''
    i = 0
    while i < health:
        healthbar += '#'
        i += 10
    while i < 100:
        healthbar += '-'
        i += 10
    
    return healthbar

#Autosave call for playerdata
async def autosave():
    
    toSend = ''

    with open('players.csv', 'w') as file:
        saveWrite = csv.writer(file, delimiter=',')
        for k in data.PLAYERDICT:
            player = data.PLAYERDICT[k]

            output = ''

            for m in player.moves:
                output += (str(m.level) + ' ' + str(m.name) + '|')

            toSend += f'{player.name},{output},{player.wins},{player.losses}\n'
            saveWrite.writerow([player.name] + [output] + [player.wins] + [player.losses])

    user = await bot.fetch_user(int(config.saveUser)) 
    await user.send(f'__***AUTOSAVE BELOW***__\n{toSend}') #Send backup copy to logging account

#Get and add player health to an embed
async def doBossfightPlayers(bfight, toSend):
    
    #Get and output players
    user1 = None
    user2 = None
    user3 = None
    
    if bfight.p1 != None:
        user1 = await bot.fetch_user(int(bfight.p1))
        toSend.add_field(name = f"{user1.name}", value = f"{bfight.p1hp}hp", inline = True) 
    if bfight.p2 != None:
        user2 = await bot.fetch_user(int(bfight.p2))
        toSend.add_field(name = f"{user2.name}", value = f"{bfight.p2hp}hp", inline = True) 
    if bfight.p3 != None:
        user3 = await bot.fetch_user(int(bfight.p3))
        toSend.add_field(name = f"{user3.name}", value = f"{bfight.p3hp}hp", inline = True) 
    
    return toSend

#Play bossfight turn as the computer player
async def doBossTurn(bfight, currentBoss):

    #Select a random move
    toPlay = currentBoss.moves[(randint(0,len(currentBoss.moves)-1))]

    #Calculate damage to inflict
    toHit = float((float(toPlay.hp)*float(toPlay.level/(data.modifier))))

    #Calculate type multipliers TODO: Boss-specified modifiers
    if bfight.lastMove != None:
        if bfight.lastMove.lower() == 'punch':
            toHit = float(toHit) * float(0.5)
        elif bfight.lastMove.lower() == 'grapple':
            toHit = float(toHit) * float(1.0)
        elif bfight.lastMove.lower() == 'kick':
            toHit = float(toHit) * float(1.5)

    #Get random user to hit
    whom = None
    
    #Must hit player 1
    if bfight.p2 == None and bfight.p3 == None:
        bfight.p1hp -= toHit
        whom = await bot.fetch_user(int(bfight.p1))
    
    #Must hit player 2
    elif bfight.p1 == None and bfight.p3 == None:
        bfight.p2hp -= toHit
        whom = await bot.fetch_user(int(bfight.p2))

    #Must hit player 3
    elif bfight.p1 == None and bfight.p2 == None:
        bfight.p3hp -= toHit
        whom = await bot.fetch_user(int(bfight.p3))

    #Must hit player 2 or 3
    elif bfight.p1 == None and (bfight.p2 != None and bfight.p3 != None):
        whoHit = randint(2,3)
        if whoHit == 2:
            bfight.p2hp -= toHit
            whom = await bot.fetch_user(int(bfight.p2))
        elif whoHit == 3:
            bfight.p3hp -= toHit
            whom = await bot.fetch_user(int(bfight.p3))

    #Must hit player 1 or 2
    elif bfight.p3 == None and bfight.p1 != None and bfight.p2 != None:
        whoHit = randint(1,2)
        if whoHit == 1:
            bfight.p1hp -= toHit
            whom = await bot.fetch_user(int(bfight.p1))
        elif whoHit == 2:
            bfight.p2hp -= toHit
            whom = await bot.fetch_user(int(bfight.p2))

    #Must hit player 1 or 3
    elif bfight.p2 == None and bfight.p1 != None and bfight.p3 != None:
        whoHit = randint(1,2)
        if whoHit == 1:
            bfight.p1hp -= toHit
            whom = await bot.fetch_user(int(bfight.p1))
        elif whoHit == 2:
            bfight.p3hp -= toHit
            whom = await bot.fetch_user(int(bfight.p3))

    #Can hit anyone
    else:
        whoHit = randint(1,3)
        if whoHit == 1:
            bfight.p1hp -= toHit
            whom = await bot.fetch_user(int(bfight.p1))
        elif whoHit == 2:
            bfight.p2hp -= toHit
            whom = await bot.fetch_user(int(bfight.p2))
        elif whoHit == 3:
            bfight.p3hp -= toHit
            whom = await bot.fetch_user(int(bfight.p3))

    #Initialize the display
    toSend = discord.Embed(title = f"{bfight.boss.name}: {bfight.boss.hp}hp", color = 0xFF0000)
    toSend.add_field(name = "POW!", value = f'{currentBoss.name} hit {whom.mention} with a {toPlay.name} for {toHit}hp!\n\n', inline = False)
        
    #Check for critical hit
    critChance = randint(1,100)
    if critChance < config.BOSS_CRIT_CHANCE:
        
        #Pick a status effect
        effects = ['broken_arm', 'broken_leg', 'concussion', 'winded'] 
        effectToPick = randint(0,len(effects)-1)

        #Get the player and apply effect
        p = data.PLAYERDICT[str(whom.id)]
        p.effect = effects[effectToPick]
        
        #Send critical hit message
        if effectToPick < 3:
            toSend.add_field(name = "CRITICAL HIT!", value = f'{whom.mention} has been given a {effects[effectToPick]}\n', inline = False)
        else:
            toSend.add_field(name = "CRITICAL HIT!", value = f'{whom.mention} has been {effects[effectToPick]}\n', inline = False)

    #Get the player hp
    finalEmbed = await doBossfightPlayers(bfight, toSend)
    
    #Get next turn
    if bfight.p1 != None:
        bfight.turn = str(bfight.p1)
        user = await bot.fetch_user(int(bfight.p1))
        finalEmbed.add_field(name = f"Turn:", value = f"It is now {user.mention}\'s turn!", inline = False) 
    
    elif bfight.p2 != None:
        bfight.turn = str(bfight.p2)
        user = await bot.fetch_user(int(bfight.p2))
        finalEmbed.add_field(name = f"Turn:", value = f"It is now {user.mention}\'s turn!", inline = False) 
    
    else:
        bfight.turn = str(bfight.p3)
        user = await bot.fetch_user(int(bfight.p3))
        finalEmbed.add_field(name = f"Turn:", value = f"It is now {user.mention}\'s turn!", inline = False) 
    
    bfight.lastMove = 'boss'
    return finalEmbed

# =============================================================
#                         ADMIN Commands
# =============================================================

#Save sections of data
@bot.command(pass_context=True)
async def save(ctx, arg, password = None):

    if 'moves' in arg.lower() and adminPass in password:
        with open('moves.csv', 'w') as file:
            saveWrite = csv.writer(file, delimiter=',', quotechar='\"', quoting=csv.QUOTE_MINIMAL)
            for move in ALL_MOVES:
                saveWrite.writerow([move.name] + [move.elem] + [move.hp] + [move.level])
        await ctx.send("Done! Move data has been saved")
    
    if 'players' in arg.lower() and adminPass in password:

        toSend = ''

        with open('players.csv', 'w') as file:
            saveWrite = csv.writer(file, delimiter=',')
            for k in data.PLAYERDICT:
                player = data.PLAYERDICT[k]

                output = ''

                for m in player.moves:
                    output += (str(m.level) + ' ' + str(m.name) + '|')

                toSend += f'{player.name},{output},{player.wins},{player.losses}\n'
                saveWrite.writerow([player.name] + [output] + [player.wins] + [player.losses])
        await ctx.send("Done! Player data has been saved")

        user = await bot.fetch_user(int(config.adminID))
        await user.send(toSend) #Send backup copy to admin account ID

#Check various data for debugging
@bot.command(pass_context=True)
async def check(ctx, thing, password):
    if password == adminPass:
        if 'training' in thing.lower():
            toSend = ''
            for t in ACTIVE_TRAINING:
                user = await bot.fetch_user(int(t.player))
                toSend += f'{user} ({t.player}) -> {t.move}, {t.level}, Time: {float(time.time()-t.time)/60}\n'       
            await ctx.send(toSend)   

#Force-finish all training
@bot.command(pass_context=True)
async def fintrain(ctx, password):    
    if password == adminPass:
        for t in ACTIVE_TRAINING:
            if str(t.player) in data.PLAYERDICT:
                   
                    p = data.PLAYERDICT[str(t.player)]
                    found = False
                    
                    #Increment move level if player already has move
                    for m in p.moves:
                        if m.name.lower() == t.move.lower():
                            m.level += 1
                            found = True
                            break
                    
                    #Otherwise add the move
                    if found == False:
                        for am in ALL_MOVES:
                            if am.name.lower() == t.move.lower():
                                p.moves.append(data.Move(am.name, am.elem, am.hp, am.level))
                                break
                    
                    p.setTraining(False)
        await ctx.send('All training has been completed!')
        ACTIVE_TRAINING.clear()

#Adjust player move level
@bot.command(pass_context=True)
async def adjust(ctx, player, move, level, password):
    if password == adminPass:
        if str(player) in data.PLAYERDICT:
            p = data.PLAYERDICT[str(player)]
            for m in p.moves:
                if m.name.lower() == move.lower():
                    m.level = int(level)
                    user = await bot.fetch_user(str(player))
                    await ctx.send(f'Adjusted {user.name}\'s {m.name} to level {m.level}')
                    break
    else:
        await ctx.send('Incorrect password!')

# =============================================================
#                     Fights and Bossfights
# =============================================================

#Handles starting PvP fights
@bot.command(pass_context=True, aliases=['f'])
async def fight(ctx, arg, player=None, password=None):

    if 'accept' in arg.lower():
        
        for f in ACTIVE_FIGHTS:
            if f.player2 == str(ctx.author.id):
                
                f.stage = 'game' #Set game to active

                user1 = await bot.fetch_user(f.player1)
                user2 = await bot.fetch_user(f.player2)
                
                await ctx.send(f'{ctx.message.author.mention} has accepted {user1.mention}\'s fight! Booting combat sequence...')

                #Display combat screen
                toSend = discord.Embed(title = f"{user1.name} vs {user2.name}", color = 0xFF000)
                toSend.add_field(name = f"{user1.name}", value = "(##########) 100hp", inline = True)
                toSend.add_field(name = f"{user2.name}", value = "(##########) 100hp", inline = True)
                toSend.add_field(name = "Turn:", value = f"It is now {user2.name}\'s turn!", inline = False)
                await ctx.send(embed=toSend)
                
                break

    elif 'cancel' in arg.lower():
        
        #Admin fight cancel, in case of bug
        if password != None and player != None:
            if password == adminPass:
                toRemove = None
                for f in ACTIVE_FIGHTS:
                    if (str(player) in f.player1 or str(player) in f.player2):
                        toRemove = f
                        await ctx.send(f'OK {ctx.author.mention}, I\'ve cancelled {player}\'s fight!')
                        break
            ACTIVE_FIGHTS.remove(toRemove)
        
        #Regular fight cancel by participant
        else:
            toRemove = None
            for f in ACTIVE_FIGHTS:
                if (str(ctx.author.id) in f.player1 or str(ctx.author.id) in f.player2):
                    if f.stage == 'lobby' or f.stage == None: 
                        toRemove = f
                        await ctx.send(f'OK {ctx.author.mention}, I\'ve cancelled your fight!')
                        break
                    elif f.stage == 'game':
                        await ctx.send(f'You can\'t cancel a fight in progress {ctx.author.mention}!')
                        break
            ACTIVE_FIGHTS.remove(toRemove)
        
    else:
        
        cancelFight = False

        #Ensure player can't get stuck in a fight with themselves
        if str(ctx.author.id) == str(ctx.message.mentions[0].id):
            await ctx.send(f'{ctx.author.mention}, you cannot challenge yourself to a fight!')

        elif str(ctx.author.id) not in data.PLAYERDICT:
            await ctx.send(f'{ctx.author.mention}, you need to *\'.signup\'* first!')

        elif str(ctx.message.mentions[0].id) in data.PLAYERDICT:

            player = data.PLAYERDICT[str(ctx.message.mentions[0].id)]

            #Make sure players can't be in multiple fights at once
            for f in ACTIVE_FIGHTS:
                
                #Check if opponent is in a fight
                if player.name in f.player1 or player.name in f.player2:
                    await ctx.send(f'Sorry {ctx.author.mention}, that person is already in a fight!')
                    cancelFight = True
                    break
                
                #Check if challenger is in a fight
                elif str(ctx.author.id) in f.player1 or str(ctx.author.id) in f.player2:
                    await ctx.send(f'You\'re already in a fight {ctx.author.mention}!')
                    cancelFight = True
                    break

            if cancelFight == False:
                #Initialize new fight
                ACTIVE_FIGHTS.append(data.Fight(str(ctx.author.id), player.name, int(100), int(100), False))
                await ctx.send(f'{ctx.author.mention} has challenged {ctx.message.mentions[0].mention}! Waiting for them to accept...')

        #Couldn't find player with that name
        else:
            await ctx.send(f'Sorry {ctx.author.mention}, I don\'t know a \"{arg}\"')

#Play an attack move during a fight
@bot.command(pass_context=True, aliases=['a'])
async def attack(ctx, move):

    #Checks
    currentFight = None
    fightNotAccepted = False
    user1 = None
    user2 = None
    sendeffect = ''
    
    #Get the active fight
    for f in ACTIVE_FIGHTS:
        if str(ctx.author.id) in str(f.player1) or str(ctx.author.id) in str(f.player2):
            currentFight = f
            if f.stage == 'lobby' or f.stage == None:
                fightNotAccepted = True
            break

    #Do reasons fight shouldn't happen
    if currentFight == None:
        await ctx.send(f'You\'re not in an active fight {ctx.author.mention}!')
    
    elif fightNotAccepted == True:
        await ctx.send(f'You need to accept the fight first {ctx.author.mention}!')

    #Do move
    else:
        
        #Get discord users
        user1 = await bot.fetch_user(currentFight.player1)
        user2 = await bot.fetch_user(currentFight.player2)

        #Make sure it is this player's turn before continuing
        if (str(ctx.author.id) in str(f.player1) and currentFight.turn == False) or (str(ctx.author.id) in str(f.player2) and currentFight.turn == True):
            await ctx.send(f'It\'s not your turn {ctx.author.mention}')
        
        else:
            
            #Get opponent
            opp = None
            if str(ctx.author.id) == str(currentFight.player1):
                opp = currentFight.player2
            else:
                opp = currentFight.player1

            #Get player
            if str(ctx.author.id) in data.PLAYERDICT:
                p = data.PLAYERDICT[str(ctx.author.id)]

                for m in p.moves:
                    if m.name.lower() == move.lower():

                        #Calculate damage to inflict
                        toHit = m.getDamage()

                        #Calculate type multipliers
                        if currentFight.lastMove != None:
                            if m.elem.lower() == 'kick':
                                if currentFight.lastMove.lower() == 'punch':
                                    toHit = float(toHit) * float(1.5)
                                elif currentFight.lastMove.lower() == 'grapple':
                                    toHit = float(toHit) * float(0.5)
                            elif m.elem.lower() == 'punch':
                                if currentFight.lastMove.lower() == 'grapple':
                                    toHit = float(toHit) * float(1.5)
                                elif currentFight.lastMove.lower() == 'kick':
                                    toHit = float(toHit) * float(0.5)
                            elif m.elem.lower() == 'grapple':
                                if currentFight.lastMove.lower() == 'kick':
                                    toHit = float(toHit) * float(1.5)
                                elif currentFight.lastMove.lower() == 'punch':
                                    toHit = float(toHit) * float(0.5)
                        
                        #Roll chance to miss
                        miss = randint(0,100)
                        miss += int(m.getAccuracy()) #Factor in move accuracy

                        #Process status effects
                        if p.getEffect() != None:
                            Euser = await bot.fetch_user(int(p.name))
                            
                            #Concussion: minus 5-30 accuracy
                            if p.effect.lower() == 'concussion': 
                                debuff = randint(5,30)
                                miss -= debuff
                                sendeffect += f'{Euser.mention} has a concussion! their accuracy is -{debuff}!\n'
                            
                            #Winded: 60-80% damage
                            elif p.effect.lower() == 'winded': 
                                debuff = randint(55,80)
                                toHit = toHit*float(debuff/100)
                                sendeffect += f'{Euser.mention} is winded! they will only do {debuff}% damage!\n'
                            
                            #Broken arm: Punches do 50% damage
                            elif p.effect.lower() == 'broken_arm': 
                                if m.elem.lower() == 'punch':
                                    
                                    #Remove any punch buff
                                    if currentFight.lastMove != None: 
                                        if currentFight.lastMove == 'grapple':
                                            toHit = (float(toHit)/1.5)
                                    
                                    toHit = float(toHit)*float(0.5)
                                    sendeffect += f'{Euser.mention} has a broken arm! their punch will do 50% damage!\n'
                                else:
                                    sendeffect += f'{Euser.mention} has a broken arm! good thing they aren\'t using it.\n'
                            
                            #Broken leg: Kicks do 50% damage
                            elif p.effect.lower() == 'broken_leg': 
                                if m.elem.lower() == 'kick':
                                    
                                    #Remove any kick buff
                                    if currentFight.lastMove != None: 
                                        if currentFight.lastMove == 'punch':
                                            toHit = (float(toHit)/1.5)
                                    
                                    toHit = float(toHit)*float(0.5)
                                    sendeffect += f'{Euser.mention} has a broken leg! their kick will do 50% damage!\n'
                                else:
                                    sendeffect += f'{Euser.mention} has a broken leg! good thing they aren\'t using it.\n'
                            
                            #Adrenaline: Random -20-20 Acc debuff, Random -20-20 Dmg buff
                            elif p.effect.lower() == 'rush': 
                                
                                #Calculate damage modifier
                                dmg = randint(-20,20)
                                toHit += float(dmg)
                                if toHit < 0: #Stop negative damage
                                    toHit = 0
                                
                                #Calculate accuracy modifier
                                acc = randint(-20,20)
                                miss += acc
                                
                                #Get display
                                sendeffect += f'{ctx.author.mention} is amped up on adrenaline! they will inflict '
                                
                                #Damage
                                if dmg >= 0:
                                    sendeffect += '+'
                                sendeffect += f'{dmg} damage at '

                                #Accuracy
                                if acc >= 0:
                                    sendeffect += '+'
                                sendeffect += f'{acc} accuracy!\n'

                            #await ctx.send(sendeffect)
                            p.setEffect(None)

                        if miss > config.missChance:

                            #If last move was this move, it will do 70% dmg
                            if p.last == m.name: 
                                toHit = float(toHit)*float(0.7)
                            p.last = m.name

                            #Calculate "Wide not tall" bonus
                            highest = getHighestLevel(p.name)
                            if len(p.moves)*2 > highest.level:
                                toHit = float(toHit)*float(1.2)
                            
                            #Level difference bonus
                            oppHigh = getHighestLevel(opp)
                            if int(oppHigh.level) > (int(highest.level)+config.LEVEL_DIFF):
                                diff = int(oppHigh.level) - (int(highest.level)+config.LEVEL_DIFF)
                                toHit += (float(toHit)*float(diff/10)/data.modifier)

                            #Status effect processing 
                            sendeffect += await doStatusEffects(p, data.PLAYERDICT[str(opp)], m)

                            #Attack correct player with the move
                            if currentFight.player1 == p.name:
                                currentFight.p2health -= float(toHit) 
                            else:
                                currentFight.p1health -= float(toHit) 

                        #Get opponent user
                        oppuser = await bot.fetch_user(int(opp))

                        #Get health bars
                        p1healthbar = doHealthBar(currentFight, currentFight.player1)
                        p2healthbar = doHealthBar(currentFight, currentFight.player2)

                        #Draw the board
                        toSend = discord.Embed(title = f"{user1.name} vs {user2.name}", color = 0xFF0000)

                        #Draw the move
                        if miss > config.missChance:
                            toSend.add_field(name = "POW!", value = f'{ctx.author.name} hit {oppuser.name} with a {m.name} ({m.elem}) for {round(toHit,2)}hp!\n\n', inline = False)
                        else:
                            toSend.add_field(name = "WOOSH!", value = f'{ctx.author.name} missed their {m.name} ({m.elem})! No damage has been taken!\n\n', inline = False)

                        #Send effect, if any
                        if sendeffect != '':
                            toSend.add_field(name = "Effects:", value = sendeffect, inline = False)

                        #Draw the next move
                        toSend.add_field(name = "Turn:", value = f"It is now {oppuser.mention}\'s turn!", inline = False)
                        
                        #Draw health bars
                        toSend.add_field(name = f"{user1.name}", value = f"({p1healthbar}) {round(currentFight.p1health)}hp", inline = True)
                        toSend.add_field(name = f"{user2.name}", value = f"({p2healthbar}) {round(currentFight.p2health)}hp", inline = True)

                        #Output
                        await ctx.send(embed=toSend)

                        #Set turn & lastmove
                        currentFight.lastMove = m.elem
                        currentFight.turn = not currentFight.turn
                        
                        break

            #Check if either player has been defeated
            if currentFight.p1health <= 0:
                await ctx.send(f'KO! {user2.mention} destroyed {user1.mention}!')    
                data.PLAYERDICT[str(f.player2)].wins += 1     
                data.PLAYERDICT[str(f.player1)].losses += 1     
            elif currentFight.p2health <= 0:
                data.PLAYERDICT[str(f.player1)].wins += 1     
                data.PLAYERDICT[str(f.player2)].losses += 1    
                await ctx.send(f'KO! {user1.mention} destroyed {user2.mention}!')
    
    #If game has ended, delete the fight instance
    toRemove = None
    for f in ACTIVE_FIGHTS:
        if (str(ctx.author.id) in f.player1 or str(ctx.author.id) in f.player2) and (f.p1health <= 0 or f.p2health <=0):
            toRemove = f
            data.PLAYERDICT[str(f.player1)].effect = None
            data.PLAYERDICT[str(f.player2)].effect = None
            break
    if toRemove != None:
        ACTIVE_FIGHTS.remove(toRemove)      

#Initialize and join boss fights
@bot.command(pass_context=True, aliases=['bf'])
async def bossfight(ctx, arg = None, plob = None):
    
    #Start boss fight lobby
    if arg == None:
        
        if data.ACTIVE_BOSSFIGHT == None:
            
            inMatch = False

            #Can't be in both fight and bossfight
            for f in ACTIVE_FIGHTS:
                if str(ctx.author.id) == str(f.player1) or str(ctx.author.id) == str(f.player2):
                    inMatch = True
                    await ctx.send(f'{ctx.author.mention} you\'re already in a PvP fight!')
                    break
            
            #Start the fight lobby
            if inMatch == False:
                data.ACTIVE_BOSSFIGHT = (data.Bossfight(config.BOSSES[randint(0,len(config.BOSSES)-1)], str(ctx.author.id), str(ctx.author.id)))
                await ctx.send(f'{ctx.author.mention} has started a boss fight! Type \'.bossfight join {ctx.author.mention}\' to join the lobby.')
        
        #Can only have 1 boss fight
        else:
            await ctx.send(f'There is already an active bossfight {ctx.author.mention}!')

    #Cancel a fight (In case of game-breaking bugs, idle players)
    elif arg.lower() == 'drop':
        if plob == adminPass:
            data.ACTIVE_BOSSFIGHT = None
            await ctx.send(f'{ctx.author.mention}, I\'ve dropped the active boss fight!')

    #Join an active boss fight lobby
    elif 'join' in arg.lower():
        
        #Incorrect syntax
        if plob == None:
            await ctx.send(f'{ctx.author.mention}, you need to say who\'s lobby you\'re joining! \'.bossfight join [@person]\'')
        
        else:
            
            #Get the lobby leader
            lobby = None
            if str(ctx.message.mentions[0].id) in data.PLAYERDICT:
                lobby = data.PLAYERDICT[str(ctx.message.mentions[0].id)]
            else:
                await ctx.send(f'{ctx.author.mention}, that person isn\'t in a lobby!')
            
            #Join
            if lobby != None:
                leader = await bot.fetch_user(int(lobby.name))
                
                f = data.ACTIVE_BOSSFIGHT

                if str(f.p1) == str(lobby.name):
                    
                    #Join as player 2
                    if f.p2 == None:
                        f.p2 = str(ctx.author.id)
                        await ctx.send(f'{ctx.author.mention} has joined {leader.mention}\'s boss fight lobby!')
                        f.lobby.append(ctx.author.id)
                    
                    #Join as player 3
                    elif f.p3 == None:
                        f.p3 = str(ctx.author.id)
                        await ctx.send(f'{ctx.author.mention} has joined {leader.mention}\'s boss fight lobby!')
                        f.lobby.append(ctx.author.id)
                    
                    #Unable to join
                    else:
                        await ctx.send(f'This lobby is full {ctx.author.mention}!')
    
    #Start a boss fight from the lobby
    elif 'start' in arg.lower():
        
        #Get the boss fight lobby
        f = data.ACTIVE_BOSSFIGHT
        if f == None:
            await ctx.send(f'{ctx.author.mention}, there\'s no active boss fight right now!')

        #Check and start
        elif str(ctx.author.id) in str(f.p1) and (f.stage == None or f.stage == 'lobby'):
            
            f.stage = 'game' 
            
            #Initialize embed
            toSend = discord.Embed(title = f"{f.boss.name}: {f.boss.hp}hp", color = 0xFF0000)

            #Get players
            user1 = await bot.fetch_user(int(f.p1))
            user2 = None
            user3 = None
            
            #Turn
            toSend.add_field(name = f"Turn:", value = f"It is now {user1.mention}\'s turn!", inline = False)

            #Embed p1
            toSend.add_field(name = f"{user1.name}", value = f"{round(f.p1hp)}hp", inline = True)

            #Rest of players
            if f.p2 != None:
                user2 = await bot.fetch_user(int(f.p2))
                toSend.add_field(name = f"{user2.name}", value = f"{round(f.p2hp)}hp", inline = True)
            if f.p3 != None:
                user3 = await bot.fetch_user(int(f.p3))
                toSend.add_field(name = f"{user3.name}", value = f"{round(f.p3hp)}hp", inline = True)

            #Send the board
            await ctx.send(embed=toSend)

#Take a player turn in a bossfight
@bot.command(pass_context=True) 
async def b(ctx, move):

    bfight = None
    fstarted = True

    #Check if fight exists / has started
    if data.ACTIVE_BOSSFIGHT != None:  
        f = data.ACTIVE_BOSSFIGHT
        if str(ctx.author.id) in str(f.p1) or str(ctx.author.id) in str(f.p2) or str(ctx.author.id) in str(f.p3):
            bfight = f
            if f.stage == 'lobby' or f.stage == None:
                fstarted = False
    
    #Fight doesn't exist / player isn't in fight
    if bfight == None:
        await ctx.send(f'You\'re not in an active fight {ctx.author.mention}!')
        return
    
    #Fight hasn't started
    elif fstarted == False:
        await ctx.send(f'The boss fight hasn\'t started {ctx.author.mention}!')
        return
    
    #Take turn
    else:
        
        currentBoss = bfight.boss 
        
        #Make sure it is this player's turn before continuing
        if str(ctx.author.id) != str(bfight.turn):
            await ctx.send(f'It\'s not your turn {ctx.author.mention}')
        
        #On player's turn:
        else:
           
            sendeffect = ''

            #Get the player
            if str(ctx.author.id) in data.PLAYERDICT:
                p = data.PLAYERDICT[str(ctx.author.id)]
                
                #Get the move
                for m in p.moves:
                    if m.name.lower() == move.lower():

                        toHit = m.getDamage()

                        #Calculate type multipliers
                        if bfight.lastMove != None:
                            
                            if m.elem.lower() == 'kick':
                                if bfight.lastMove.lower() == 'punch':
                                    toHit = float(toHit) * float(1.5)
                                elif bfight.lastMove.lower() == 'grapple':
                                    toHit = float(toHit) * float(0.5)
                                elif bfight.lastMove.lower() == 'boss':
                                    toHit = float(toHit) * float(config.bossMoveModifier)
                            
                            elif m.elem.lower() == 'punch':
                                if bfight.lastMove.lower() == 'grapple':
                                    toHit = float(toHit) * float(1.5)
                                elif bfight.lastMove.lower() == 'kick':
                                    toHit = float(toHit) * float(0.5)
                                elif bfight.lastMove.lower() == 'boss':
                                    toHit = float(toHit) * float(config.bossMoveModifier)
                           
                            elif m.elem.lower() == 'grapple':
                                if bfight.lastMove.lower() == 'kick':
                                    toHit = float(toHit) * float(1.5)
                                elif bfight.lastMove.lower() == 'punch':
                                    toHit = float(toHit) * float(0.5)
                                elif bfight.lastMove.lower() == 'boss':
                                    toHit = float(toHit) * float(config.bossMoveModifier)
                        
                        #Roll chance to miss
                        miss = randint(0,100)
                        miss += int(m.getAccuracy()) #Factor in move accuracy

                        #Process status effects
                        if p.getEffect() != None:
                            Euser = await bot.fetch_user(int(p.name))
                            
                            #Concussion: minus 5-30 accuracy
                            if p.effect.lower() == 'concussion': 
                                debuff = randint(5,30)
                                miss -= debuff
                                sendeffect += f'{Euser.mention} has a concussion! their accuracy is -{debuff}!\n'
                            
                            #Winded: 60-80% damage
                            elif p.effect.lower() == 'winded': 
                                debuff = randint(55,80)
                                toHit = toHit*float(debuff/100)
                                sendeffect += f'{Euser.mention} is winded! they will only do {debuff}% damage!\n'
                            
                            #Broken arm: Punches do 50% damage
                            elif p.effect.lower() == 'broken_arm': 
                                if m.elem.lower() == 'punch':
                                    
                                    #Remove any punch buff
                                    if bfight.lastMove != None: 
                                        if bfight.lastMove == 'grapple':
                                            toHit = (float(toHit)/1.5)
                                    
                                    toHit = float(toHit)*float(0.5)
                                    sendeffect += f'{Euser.mention} has a broken arm! their punch will do 50% damage!\n'
                                else:
                                    sendeffect += f'{Euser.mention} has a broken arm! good thing they aren\'t using it.\n'
                            
                            #Broken leg: Kicks do 50% damage
                            elif p.effect.lower() == 'broken_leg': 
                                if m.elem.lower() == 'kick':
                                    
                                    #Remove any kick buff
                                    if bfight.lastMove != None: 
                                        if bfight.lastMove == 'punch':
                                            toHit = (float(toHit)/1.5)
                                    
                                    toHit = float(toHit)*float(0.5)
                                    sendeffect += f'{Euser.mention} has a broken leg! their kick will do 50% damage!\n'
                                else:
                                    sendeffect += f'{Euser.mention} has a broken leg! good thing they aren\'t using it.\n'
                            
                            #Adrenaline: Random -20-20 Acc debuff, Random -20-20 Dmg buff
                            elif p.effect.lower() == 'rush': 
                                
                                #Calculate damage modifier
                                dmg = randint(-20,20)
                                toHit += float(dmg)
                                if toHit < 0: #Stop negative damage
                                    toHit = 0
                                
                                #Calculate accuracy modifier
                                acc = randint(-20,20)
                                miss += acc
                                
                                #Get display
                                sendeffect += f'{ctx.author.mention} is amped up on adrenaline! they will inflict '
                                
                                #Damage
                                if dmg >= 0:
                                    sendeffect += '+'
                                sendeffect += f'{dmg} damage at '

                                #Accuracy
                                if acc >= 0:
                                    sendeffect += '+'
                                sendeffect += f'{acc} accuracy!\n'
                            
                            p.setEffect(None)

                        #If last move was this move, it will do 70% dmg
                        if p.last == m.name: 
                            toHit = float(toHit)*float(0.7)
                        p.last = m.name

                        #Initialize embed
                        toSend = discord.Embed(title = f"{f.boss.name}: {f.boss.hp}hp", color = 0xFF0000)

                        #Damage boss + get output
                        if miss > config.missChance:
                            currentBoss.hp -= toHit
                            toSend = discord.Embed(title = f"{f.boss.name}: {f.boss.hp}hp", color = 0xFF0000) #Reset title with new hp
                            toSend.add_field(name = f"POW!", value = f'{ctx.author.mention} hit {currentBoss.name} with a {m.name} for {toHit}hp!\n\n', inline = False)
                        else:
                            toSend.add_field(name = f"WOOSH!", value = f'{ctx.author.mention} missed their {m.name}!\n\n', inline = False)

                        #Calculate next turn
                        if str(ctx.author.id) == bfight.p1 and bfight.p2 != None:
                            bfight.turn = bfight.p2
                            next = await bot.fetch_user(int(bfight.p2))
                            toSend.add_field(name = f"Turn:", value = f"It is now {next.mention}\'s turn!", inline = False) 
                        
                        elif str(ctx.author.id) == bfight.p1 and bfight.p2 == None:
                            bfight.turn = 'BOSS_TURN'
                            toSend.add_field(name = f"Turn:", value = f"It is now {currentBoss.name}\'s turn!", inline = False) 
                        
                        elif str(ctx.author.id) == bfight.p2 and bfight.p3 != None:
                            bfight.turn = bfight.p3
                            next = await bot.fetch_user(int(bfight.p3))
                            toSend.add_field(name = f"Turn:", value = f"It is now {next.mention}\'s turn!", inline = False) 
                        
                        elif str(ctx.author.id) == bfight.p2 and bfight.p3 == None:
                            bfight.turn = 'BOSS_TURN'
                            toSend.add_field(name = f"Turn:", value = f"It is now {currentBoss.name}\'s turn!", inline = False) 
                        
                        elif str(ctx.author.id) == bfight.p3:
                            bfight.turn = 'BOSS_TURN'
                            toSend.add_field(name = f"Turn:", value = f"It is now {currentBoss.name}\'s turn!", inline = False) 

                        #Get the player hp
                        toSend = await doBossfightPlayers(bfight, toSend)

                        #Send embed
                        await ctx.send(embed=toSend)
                        
                        #Set last move
                        bfight.lastMove = m.elem

                        #Do boss turn
                        if bfight.turn == 'BOSS_TURN':

                            if currentBoss.hp <= 0:
                                break #Continue to win condition check

                            time.sleep(3)
                            finalEmbed = await doBossTurn(bfight, currentBoss)
                            
                            #Send the display
                            await ctx.send(embed=finalEmbed)
    
    #Player 1 check
    if bfight.p1hp <= 0:
        
        victim = await bot.fetch_user(int(bfight.p1))
        await ctx.send(f'{victim.mention} has been knocked out!\n')
        
        #If it would have been player 1's turn, get the next turn
        if str(bfight.turn) == str(bfight.p1):
            
            if bfight.p2 != None:
                bfight.turn = str(bfight.p2)
                user = await bot.fetch_user(int(bfight.p2))
                await ctx.send(f'It is now {user.mention}\'s turn!')
            
            elif bfight.p3 != None:
                bfight.turn = str(bfight.p3)
                user = await bot.fetch_user(int(bfight.p3))
                await ctx.send(f'It is now {user.mention}\'s turn!')
        
        #Reset player values
        bfight.p1 = None
        bfight.p1hp = 100

    #Player 2 check
    if bfight.p2hp <= 0:
        
        victim = await bot.fetch_user(int(bfight.p2))
        await ctx.send(f'{victim.mention} has been knocked out!\n')
        
        if str(bfight.turn) == str(bfight.p2):
            
            if bfight.p3 != None:
                bfight.turn = str(bfight.p3)
                user = await bot.fetch_user(int(bfight.p3))
                await ctx.send(f'It is now {user.mention}\'s turn!')
        
        #Reset player values
        bfight.p2 = None
        bfight.p2hp = 100

    #Player 3 check
    if bfight.p3hp <= 0:
        
        victim = await bot.fetch_user(int(bfight.p3))
        await ctx.send(f'{victim.mention} has been knocked out!\n')
        
        #Reset player values
        bfight.p3 = None
        bfight.p3hp = 100

    #Get fight info
    currentBoss = bfight.boss
    f = data.ACTIVE_BOSSFIGHT
    
    #Game over, loss
    if f.p2 == None and f.p3 == None and f.p1 == None:
        data.ACTIVE_BOSSFIGHT = None
        currentBoss.hp = currentBoss.maxhp
        await ctx.send(f'Game over, {f.boss.name} has won!\n')
    
    #Game over, win
    elif currentBoss.hp <= 0:
        
        #Win message
        await ctx.send(f'{currentBoss.name} has been knocked out! You have won!\n')
        
        #Reward message
        toSend = '\n===================================\n'
        toSend += f'If you didn\'t before have {currentBoss.reward.name}, you have now gained it.\n'
        toSend += f'{currentBoss.reward.name} is a mysterious move that is difficult to master...\n'
        toSend += f'If you have learned {currentBoss.reward.name}, you have gained a level...\n\n'
        
        #Check each player for boss reward move
        for i in f.lobby:
            
            #Get player
            if str(i) in data.PLAYERDICT:
                p = data.PLAYERDICT[str(i)]
                user = await bot.fetch_user(int(p.name))
                
                found = False
                
                #Check for move
                for m in p.moves:
                    #If player has the move, increment level
                    if m.name.lower() == currentBoss.reward.name.lower():
                        m.level = int(m.level) + 1
                        toSend += f'{user.mention}\'s {m.name} has reached level {m.level}!\n'
                        found = True
                        break
                
                #Otherwise, add the move to the player
                if found == False:
                    p.moves.append(data.Move(currentBoss.reward.name, currentBoss.reward.elem, currentBoss.reward.hp, int(5)))
                    toSend += f'{user.mention} has learned {currentBoss.reward.name}!\n'
        
        #Reset and send
        data.ACTIVE_BOSSFIGHT = None
        currentBoss.hp = currentBoss.maxhp
        await ctx.send(toSend)

# =============================================================
#                    Move Training and Other
# =============================================================

#Train new moves or level up existing ones
@bot.command(pass_context=True, aliases=['t'])
async def train(ctx, move):

    if str(ctx.author.id) in data.PLAYERDICT:
        
        player = data.PLAYERDICT[str(ctx.author.id)]
        moveFound = False
        
        if player.getTraining() == False:

            if move.upper() in config.BOSS_MOVES:
                await ctx.send(f'This move can\'t be trained that easily {ctx.author.mention}!')
            
            else:
                for m in player.moves: 
                    
                    #If player has the move, increase level and @ them
                    if m.name.lower() == move.lower():
                        
                        moveFound = True
                        
                        #Stop if move is already the level cap
                        if m.level >= config.LEVELCAP:
                            await ctx.send(f'You\'re already the max level for this move {ctx.author.mention}!')
                        
                        else:
                            player.setTraining(True)
                            ACTIVE_TRAINING.add(data.Training(str(ctx.author.id), m.name, int(m.level)+1, time.time()))
                            timeleft = config.trainTime
                            i = 5
                            while i < int(m.level)+1:
                                timeleft += config.trainTime
                                i += 5
                            await ctx.send(f'Training {m.name} to level {m.level+1}... This may take a while... ({int(timeleft)/60} minutes)')
                        
                        break
                
                #If player is training a new move, get the move from the list and increase it to level 1
                if moveFound == False:
                    for m in ALL_MOVES:
                        if m.name.lower() == move.lower():
                            player.setTraining(True)
                            ACTIVE_TRAINING.add(data.Training(str(ctx.author.id), m.name, m.level, time.time()))
                            await ctx.send(f'Training {m.name} to level {m.level}... This may take a while... ({int(config.trainTime)/60} minutes)')

        #Player is already training, tell them how long is left                 
        else:
            for t in ACTIVE_TRAINING:
                if str(t.player) == str(ctx.author.id):
                    timeleft = config.trainTime
                    i = 5
                    while i < int(t.level):
                        timeleft += config.trainTime
                        i += 5
                    await ctx.send(f'You\'re already training {t.move}! {ctx.author.mention}, Come back in {int((timeleft-(time.time()-t.time))/60)} minutes!')
                    break

#Add as a new user to the BattleBot files           
@bot.command(pass_context=True)
async def signup(ctx):

    if str(ctx.author.id) in data.PLAYERDICT:
        await ctx.send(f'You\'ve already signed up {ctx.author.mention}!')

    else:
        
        with open('players.csv', 'a') as file:
            playerWrite = csv.writer(file, delimiter=',')
            starting = ('3 Hook|3 Front_Kick|3 Belly_Flop|')
            playerWrite.writerow([ctx.author.id] + [starting])    

        data.PLAYERDICT[str(ctx.author.id)] = data.Player(str(ctx.author.id), set(), 0, 0)

        if str(ctx.author.id) in data.PLAYERDICT:
            p = data.PLAYERDICT[str(ctx.author.id)]
            p.moves = [data.Move('Hook', 'Punch', 5, 3), data.Move('Front_Kick', 'Kick', 5, 3), data.Move('Belly_Flop', 'Grapple', 10, 3)]

        await ctx.send(f'Welcome to BattleBot, {ctx.author.mention}!\nYou\'ll start with some basic moves, on the house.\nType \".helpme\" for any more info, and good luck!')

#Send a list of commands
@bot.command(pass_context=True)
async def helpme(ctx):
    toSend = '===================================\n'
    toSend += 'BattleBot Commands:\n'
    toSend += '===================================\n'
    toSend += '\n_**MISC:**_\n'
    toSend += '.helpme - Show this list\n'
    toSend += '.wiki - Explain the move modifiers'
    toSend += '.signup - Get started with BattleBot!\n'
    toSend += '\n_**MOVE TRAINING:**_\n'
    toSend += '.train [move] - Level up a move, or get a new one\n'
    toSend += '.moves all - See all the moves that exist\n'
    toSend += '.moves mine - See all of your moves\n'
    toSend += '.moves [person] - See someone\'s moveset\n'
    toSend += '\n_**COMBAT:**_\n'
    toSend += '.f [person] - Challenge someone to a fight!\n'
    toSend += '.f accept - Accept someone\'s challenge to fight\n'
    toSend += '.f cancel - Cancel a fight you\'ve started\n'
    toSend += '.a [move] - Play a selected move during a fight\n'
    await ctx.send(toSend)

#See your available moves 
@bot.command(pass_context=True, aliases=['m'])
async def moves(ctx, who):
    
    #Send user's moves list
    if 'mine' in who.lower():
        
        toSend = ''

        if str(ctx.author.id) in data.PLAYERDICT:
            
            player = data.PLAYERDICT[str(ctx.author.id)]
            
            for m in player.moves:
                
                toHit = m.getDamage()

                #Name padding
                padding = 25-len(m.name)
                padstr = ''
                while padding > 0:
                    padstr += ' '
                    padding -= 1

                #Level display    
                displaylevel = str(m.level)
                if int(displaylevel) < 10:
                    displaylevel = f'0{m.level}'

                #Main string
                toSend += f'L:{displaylevel}\t Dmg: {round(toHit,2)}\t Acc: '
                if m.getAccuracy() >= 0: #Include + if positive
                    toSend += '+'
                toSend += f'{m.getAccuracy()}\t {m.name}{padstr} \t\t\t'
                
                #Status effects
                if str(m.name).lower() in config.concussListLOW or str(m.name).lower() in config.concussListHIGH or str(m.name).lower() in config.concussListMED:
                    toSend += ' (% Concuss) '
                if str(m.name).lower() in config.windHIGH or str(m.name).lower() in config.windMED:
                    toSend += ' (% Wind) '
                if str(m.name).lower() in config.blegVERYLOW:
                    toSend += ' (% Break own leg) '
                if str(m.name).lower() in config.barmHIGH:
                    toSend += ' (% Break arm) '
                if str(m.name).lower() == 'leg_kick':
                    toSend += ' (% Break opponent\'s leg) '

                #Add newline
                toSend += '\n'

        await ctx.send(f'==================================\nHey {ctx.message.author.mention}, Here\'s a list of your moves! \n===================================\n{toSend}')

    #Send every move that exists
    elif 'all' in who.lower():
        
        toSend = ''
        movetypes = []
        
        #Get every move type
        for m in ALL_MOVES:
            if m.elem not in movetypes and m.elem != 'BOSS':
                movetypes.append(m.elem)

        #Print section for each move type
        for t in movetypes:
            toSend += '===================================\n'
            toSend += f'{str(t).upper()}:\n'
            toSend += '===================================\n'
        
            #Display all move information
            for move in ALL_MOVES:
                if move.elem.lower() == str(t).lower():
                    toSend += getMoveInfo(move)

        await ctx.send(f'===================================\nHey {ctx.message.author.mention}, Here\'s a list of all available moves! \n===================================\n{toSend}')

    elif len(ctx.message.mentions) > 0:
        if str(ctx.message.mentions[0].id) in data.PLAYERDICT:
            
            player = data.PLAYERDICT[str(ctx.author.id)]

            toSend = ''
            
            for m in player.moves:
                    toSend += (f'{m.name}\n')
            user1 = await bot.fetch_user(player.name)

            await ctx.send(f'===================================\nHey {ctx.message.author.mention}, Here\'s a list of {user1.name}\'s moves! \n===================================\n{toSend}')

#See the scoreboard
@bot.command(pass_context=True)
async def scoreboard(ctx):
    
    #Get the scores of each player into the scoreboard
    data.SCOREBOARD.clear()
    for p in data.PLAYERDICT:
        current = data.PLAYERDICT[p]
        data.SCOREBOARD.append(data.Score(current.name, current.wins, current.losses))
    data.SCOREBOARD.sort(key=getWin, reverse=True)
    
    toSend = ''
    
    for s in data.SCOREBOARD:
        user = await bot.fetch_user(int(s.player))
        
        kd = float(0)
        if int(s.losses) > 0:
            kd = float(int(s.wins) / int(s.losses))
        else:
            kd = float(int(s.wins))

        toSend += f'{s.wins} wins | {s.losses} losses | ({round(kd, 1)} K/D)\t\t{user.name}\n'
    
    await ctx.send(f'Battlebot Scoreboard:\n===========================\n{toSend}\n')

# =============================================================
#                     Message processing
# =============================================================

#When a message is sent, do training checks
@bot.event 
async def on_message(message):

    if message.author == bot.user:
        return

    #Remove any old training
    toRemove = set()
    for t in ACTIVE_TRAINING:
        if str(t.player) in data.PLAYERDICT:
            if data.PLAYERDICT[str(t.player)].getTraining() == False:
                toRemove.add(t)
    for r in toRemove:
        ACTIVE_TRAINING.remove(r)

    #Check and handle moves in training that need to finish
    for t in ACTIVE_TRAINING:
        if t.done == False:
            
            fullTime = int(config.trainTime)

            #Get how long the move should take
            if str(t.player) in data.PLAYERDICT:
                p = data.PLAYERDICT[str(t.player)]
                for m in p.moves:
                    if m.name.lower() == t.move.lower():
                        i = 5
                        while i < int(t.level):
                            fullTime += config.trainTime
                            i += 5
                        break

            if (time.time() - t.time) > fullTime:
                
                if str(t.player) in data.PLAYERDICT:
                   
                    p = data.PLAYERDICT[str(t.player)]
                    found = False
                    
                    #Increment move level if player already has move
                    for m in p.moves:
                        if m.name.lower() == t.move.lower():
                            m.level += 1
                            found = True
                            break
                    
                    #Otherwise add the move
                    if found == False:
                        for am in ALL_MOVES:
                            if am.name.lower() == t.move.lower():
                                p.moves.append(data.Move(am.name, am.elem, am.hp, am.level))
                                break
                    
                    p.setTraining(False)

                #Send user level up message
                user1 = await bot.fetch_user(t.player)
                await message.channel.send(f'Congrats {user1.mention}, your {t.move} has reached level {t.level}!')
                t.done == True

    #Autosave
    if time.time()-config.lastSave >= saveGap:
        await autosave()
        await message.channel.send('Autosave completed!')
        config.lastSave = time.time()

    #Process all commands, required to have both on_message and @bot.command methods
    await bot.process_commands(message)

#Run the bot, calls a private token
bot.run(config.botToken)