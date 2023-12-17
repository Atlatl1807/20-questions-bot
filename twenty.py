import discord #from pycord
from discord import ui
from discord.ext import commands 
from discord.commands import Option

from collections import defaultdict

import os
from os.path import join, dirname
from dotenv import load_dotenv

import statistics
import json
from datetime import datetime
import random
import io
import aiohttp
import shlex
import subprocess

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="'", intents=intents)

bot.guildsActive = set()

class AskQuestion(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=60)
        self.channel = channel
        self.value = None

    @discord.ui.button(label="Yes", row=0, style=discord.ButtonStyle.primary)
    async def first_button_callback(self, button, interaction):
        self.value = "Yes"
        button.label += " ✅"
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Don't Know", row=0, style=discord.ButtonStyle.primary)
    async def second_button_callback(self, button, interaction):
        self.value = "Don't Know"
        button.label += " ✅"
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="No", row=0, style=discord.ButtonStyle.primary)
    async def second_button_callback(self, button, interaction):
        self.value = "No"
        button.label += " ✅"
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()

class IsCorrect(discord.ui.View):
    @discord.ui.button(label="Yes", row=0, style=discord.ButtonStyle.primary)
    async def first_button_callback(self, button, interaction):
        self.value = "Yes"
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="No", row=0, style=discord.ButtonStyle.primary)
    async def second_button_callback(self, button, interaction):
        self.value = "No"
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()

class NavigateDatabase(discord.ui.View):
    @discord.ui.button(label="⬅️", row=0, style=discord.ButtonStyle.primary)
    async def first_button_callback(self, button, interaction):
        self.value = "Left"
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="➡️", row=0, style=discord.ButtonStyle.primary)
    async def second_button_callback(self, button, interaction):
        self.value = "Right"
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="❌", row=0, style=discord.ButtonStyle.primary)
    async def third_button_callback(self, button, interaction):
        self.value = "Exit"
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.clear_items()
        self.stop()

    @discord.ui.button(label="➕", row=0, style=discord.ButtonStyle.primary)
    async def fourth_button_callback(self, button, interaction):
        self.value = "New"
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self, button, interaction):
        self.value = "Exit"
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.clear_items()
        self.stop()

@bot.event
async def on_ready():
    print("logged in")                      #prints message if bot is online
    try:
        await bot.sync_commands()
        print("synced commands")            #send message if commands are synced with the bot
    except Exception as e:
        print(e)                            #sends error message if commands are not being synced

@bot.command()
async def ping(ctx):
    await ctx.send("pong")
 
@bot.after_invoke
async def release(interaction: discord.Interaction):
    bot.guildsActive.remove(interaction.guild)


@bot.slash_command(name="test", description="checks if the slash command is working")   
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("working slash command")                    

@bot.slash_command(name="start", description="starts a game")   
async def start(interaction: discord.Interaction):
    if interaction.guild in bot.guildsActive:
        await interaction.response.send_message("someone is already using bot in this server, you must wait until they finish")  
        return
    
    bot.guildsActive.add(interaction.guild)

    serverID = interaction.guild.id
    filepath = str(serverID) + ".json"
    if (os.path.exists(filepath)):
        with open(filepath, "r") as file:
            json_data = json.loads(file.read())
    else:
        await interaction.response.send_message("No database detected, try creating some objects!")  
        return   
    
    filteredQuestions = []
    # 0 = question name
    # 1 = frequency
    # 2 = average prob
    answeredQuestions = {}
    questionsNumber = 0

    objectsAndProb = []


    #objects that have been influenced by probability
    likelyObjects = {}
    uniqueQuestions = []
    allQuestions = []
    dataQuestions = []
    filteredQuestions = []
    for object in json_data['data']:
        for question in json_data['data'][object]['questions']:
            allQuestions.append(question)
    #remove duplicates
    uniqueQuestions = list(set(allQuestions))

    #first find the most best first question with both frequency and highest prob
    for question in uniqueQuestions:
        questionData = [question, 0, 0]
        probList = []
        for object in json_data['data']:
            if question in json_data['data'][object]['questions']:
                questionData[1] += 1
                if len(json_data['data'][object]['questions'][question].keys()) > 0:
                    probList.append(abs(json_data['data'][object]['questions'][question]['prob']))
        questionData[2] = statistics.mean(probList)
        dataQuestions.append(questionData)

    #sort by freuqnecy, then by probability change
    filteredQuestions = sorted(dataQuestions, key=lambda question: question[1], reverse=True)
    filteredQuestions = sorted(dataQuestions, key=lambda question: question[2], reverse=True)

    #now that its filtered we make it a normal list
    columns = list(zip(*filteredQuestions))
    filteredQuestions = list(columns[0])

    question = filteredQuestions[0]
    filteredQuestions.pop(0)

    view=AskQuestion(interaction.channel.id)
    embed = discord.Embed(
        title="Question",
        description="Thinking...",
        color=discord.Colour.blurple(),
    )
    
    message = await interaction.channel.send(embed=embed, view=view)

    await interaction.response.send_message("Questions:", delete_after=1)
    
    while questionsNumber < 20:

        view=AskQuestion(interaction.channel.id)
        embed = discord.Embed(
            title="Question",
            description=question,
            color=discord.Colour.blurple(),
        )
        await message.edit(embed=embed, view=view)
        view.enable_all_items()
        await view.wait()
        if view.value == "Yes":
            answeredQuestions[question] = 1
        elif view.value == "No":
            answeredQuestions[question] = -1
        else:
            answeredQuestions[question] = 0
        
        for object in json_data['data']:
            if question in json_data['data'][object]['questions']:
                #initialize key
                if not object in likelyObjects.keys():
                    likelyObjects[object] = 0
                #either increase or decrease probability. it's opposite if the answer was no
                likelyObjects[object] += (answeredQuestions[question] * json_data['data'][object]['questions'][question]['prob'])
        objectsAndProb = []
        for object in likelyObjects:
            objectProb = [object, likelyObjects[object]]
            objectsAndProb.append(objectProb)

        objectsByProb = sorted(objectsAndProb, key=lambda object: object[1], reverse=True)

        mostlikelyobject = objectsByProb[0][0]

        if (len(filteredQuestions) <= 0):
            break

        bestQuestions = []
        uniqueBestQuestions = []
        filteredBestQuestions = []
        usedQuestions = []
        #now base questions on the 5 most likely object
        rangelength = 4
        if (len(objectsByProb) < rangelength):
            rangelength = len(objectsByProb)
        for n in range(rangelength):
            for question in json_data['data'][objectsByProb[n][0]]['questions']:
                if question in filteredQuestions:
                    bestQuestions.append(question)

        #remove duplicates
        uniqueBestQuestions = list(set(bestQuestions))

        for question in uniqueBestQuestions:
            questionData = [question, 0, 0]
            probList = []
            for n in range(rangelength):
                if question in json_data['data'][objectsByProb[n][0]]['questions']:
                    questionData[1] += 1
                    if len(json_data['data'][object]['questions'][question].keys()) > 0:
                        probList.append(abs(json_data['data'][object]['questions'][question]['prob']))
            questionData[2] = statistics.mean(probList)
            filteredBestQuestions.append(questionData)

        #sort by frequency  
        filteredBestQuestions = sorted(filteredBestQuestions, key=lambda question: question[1], reverse=True)
        #sort by probability 
        filteredBestQuestions = sorted(filteredBestQuestions, key=lambda question: question[2], reverse=True)


        if len(filteredBestQuestions) <= 0:
            if len(filteredQuestions) <= 0:
                break 
            else:
                question = filteredQuestions[0]
        else:
            question = filteredBestQuestions[0][0]

        filteredQuestions.remove(question)
            
        questionsNumber += 1

    
    guessedobject = objectsByProb[0][0]
    guess = "Is your answer" + guessedobject + "?"

    view=IsCorrect()
    await interaction.followup.send(content=guess, view=view)
    await view.wait()
    if view.value == "Yes":
        await interaction.channel.send("Great!")
        for question in json_data['data'][guessedobject]['questions']:
            if question in answeredQuestions:
                if not 'times' in json_data['data'][guessedobject]['questions'][question].keys():
                    json_data['data'][guessedobject]['questions'][question]['times'] = {}
                    json_data['data'][guessedobject]['questions'][question]['times'] = 0
                hardtimes = json_data['data'][guessedobject]['questions'][question]['times'] + 1
                json_data['data'][guessedobject]['questions'][question]['times'] = hardtimes
                if not 'times' in json_data['data'][guessedobject]['questions'][question].keys():
                    json_data['data'][guessedobject]['questions'][question]['prob'] = {}
                    json_data['data'][guessedobject]['questions'][question]['prob'] = 0
                json_data['data'][guessedobject]['questions'][question]['prob'] += ((answeredQuestions[question] / hardtimes) * 0.5)
    elif view.value == "No":
        await interaction.channel.send("What was your answer?")
        def check(m):
            return m.channel == interaction.channel and m.author == interaction.user
        msg = await bot.wait_for('message', check=check)
        for object in ['data']:
            if object.lower() == msg.content.lower():
                for question in json_data['data'][object]['questions']:
                    if question in answeredQuestions:
                        if not 'times' in json_data['data'][object]['questions'][question].keys():
                            json_data['data'][object]['questions'][question]['times'] = {}
                            json_data['data'][object]['questions'][question]['times'] = 0
                        times = json_data['data'][object]['questions'][question]['times'] + 1
                        json_data['data'][object]['questions'][question]['times'] = times
                        if not 'times' in json_data['data'][object]['questions'][question].keys():
                            json_data['data'][object]['questions'][question]['prob'] = {}
                            json_data['data'][object]['questions'][question]['prob'] = 0
                        json_data['data'][object]['questions'][question]['prob'] = json_data['data'][object]['questions'][question]['prob'] + float((answeredQuestions[question] / times) * 0.5)
                break
        #object not in data, add it
        newobject = msg.content
        for question in answeredQuestions:
            json_data['data'][newobject] = {}
            json_data['data'][newobject]['questions'] = {}
            json_data['data'][newobject]['questions'][question] = {}
            json_data['data'][newobject]['questions'][question]['times'] = 1
            json_data['data'][newobject]['questions'][question]['prob'] = [(answeredQuestions[question] * 0.5)]

    with open(filepath, "w+") as file:
        json.dump(json_data, file)
    print("Data stored successfully!")

@bot.slash_command(name="database", description="scan the database and add questions")   
async def database(interaction: discord.Interaction):
    if interaction.guild in bot.guildsActive:
        await interaction.response.send_message("someone is already using bot in this server, you must wait until they finish")  
        return
    
    bot.guildsActive.add(interaction.guild)

    serverID = interaction.guild.id
    filepath = str(serverID) + ".json"
    if (os.path.exists(filepath)):
        with open(filepath, "r") as file:
            json_data = json.loads(file.read())
    else:
        await interaction.response.send_message("No database detected, try creating some objects!")  
        return
        
    allObjects = []
    iterator = 0
    for object in json_data['data']:
        allObjects.append(object)
    maxiterator = len(allObjects) - 1

    await interaction.response.send_message("Navigate the database:", delete_after=1)

    while(True):
        embed = discord.Embed(
            title="Database",
            description=allObjects[iterator],
            color=discord.Colour.blurple(),
        )
        questioniterator = 1
        for question in json_data['data'][allObjects[iterator]]['questions']:
            text = question
            if 'prob' in json_data['data'][allObjects[iterator]]['questions'][question].keys():
                text += " **Probability: " + str(json_data['data'][allObjects[iterator]]['questions'][question]['prob']) + "**"
            embed.add_field(name="Question " + str(questioniterator), value=text)
            questioniterator += 1
        embed.set_footer(text=str(iterator + 1) + "/" + str(maxiterator + 1))
        view=NavigateDatabase()
        if not 'message' in locals():
            message = await interaction.channel.send(content="Navigate the database:", embed=embed, view=view)
        else:
            await message.edit(embed=embed, view=view)
        await view.wait()
        if view.value == "Left":
            if iterator <= 0:
                iterator = maxiterator
            else:
                iterator -= 1
        elif view.value == "Right":
            if iterator >= maxiterator:
                iterator = 0
            else:
                iterator += 1
        elif view.value == "Exit":
            break
        elif view.value == "New":
            await interaction.channel.send("What question would you like to add? (Can have answer of either yes or no)")
            def check(m):
                return m.channel == interaction.channel and m.author == interaction.user
            msg = await bot.wait_for('message', check=check)
            newquestion = msg.content
            for question in json_data['data'][object]['questions']:
                if question.lower() == newquestion.lower():
                    await interaction.channel.send("That question is already there.")
                    break
            await interaction.channel.send("Is the answer yes or no?")
            def check(m):
                return m.channel == interaction.channel and m.author == interaction.user
            msg = await bot.wait_for('message', check=check)
            if "yes" in msg.content.lower():
                newprob = 0.5
            elif "no" in msg.content.lower():
                newprob = -0.5
            else:
                newprob = 0
            if not 'questions' in json_data['data'][object].keys():
                json_data['data'][object] = {}
            if not len(json_data['data'][object]['questions'].keys()) > 0:
                json_data['data'][object]['questions'] = {}
            json_data['data'][object]['questions'][newquestion] = {}
            json_data['data'][object]['questions'][newquestion]['prob'] = newprob
            

    with open(filepath, "w+") as file:
        json.dump(json_data, file)
    print("Data stored successfully!")
                    
@bot.slash_command(name="add_object", description="add a new object")   
async def add_object(interaction: discord.Interaction):
    if interaction.guild in bot.guildsActive:
        await interaction.response.send_message("someone is already using bot in this server, you must wait until they finish")  
        return
    
    bot.guildsActive.add(interaction.guild)
    serverID = interaction.guild.id
    filepath = str(serverID) + ".json"
    newdatabase = False
    if (os.path.exists(filepath)):
        with open(filepath, "r") as file:
            json_data = json.loads(file.read())
    else:
        newdatabase = True
        json_data = {} 
    
    await interaction.response.send_message("What object would you like to add?")
    def check(m):
        return m.channel == interaction.channel and m.author == interaction.user
    msg = await bot.wait_for('message', check=check)
    newobject = msg.content
    #might not exist for this command since it allows empty database
    if not newdatabase:
        for object in json_data['data']:
            if object.lower() == newobject.lower():
                await interaction.channel.send("That object is already there.")
                break
    await interaction.channel.send("What question would you like to add? (Can have answer of either yes or no)")
    def check(m):
        return m.channel == interaction.channel and m.author == interaction.user
    msg = await bot.wait_for('message', check=check)
    newquestion = msg.content
    await interaction.channel.send("Is the answer yes or no?")
    def check(m):
        return m.channel == interaction.channel and m.author == interaction.user
    msg = await bot.wait_for('message', check=check)
    if "yes" in msg.content.lower():
        newprob = 0.5
    elif "no" in msg.content.lower():
        newprob = -0.5
    if not 'questions' in json_data['data'][newobject].keys():
        json_data['data'][newobject] = {}
    if not len(json_data['data'][newobject]['questions'].keys()) > 0:
        json_data['data'][newobject]['questions'] = {}
    json_data['data'][newobject]['questions'][newquestion] = {}
    json_data['data'][newobject]['questions'][newquestion]['prob'] = newprob
    
    with open(filepath, "w+") as file:
        json.dump(json_data, file)
    print("Data stored successfully!")

@bot.slash_command(name="awesome", description="can")   
async def awesome(interaction: discord.Interaction):
    await interaction.response.send_message("think")    

bot.run(TOKEN)   #replace TOKEN with your bots token if you are not working with a seperate file to protect the token put the token in quotation marks.
