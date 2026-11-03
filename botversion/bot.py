import os
import discord
from dotenv import load_dotenv, find_dotenv
from discord.ext import commands
from groq import Groq
import asyncio
import time

#Intents are a feature of Discord that tells the gateway exactly which events to send your bot (taken from https://www.pythondiscord.com/pages/tags/intents/)
intent = discord.Intents.default()
intent.message_content = True

#dm_msg stores messages from ?askdm 
#dm_userlist stores the user's Discord ID
#localmemory is used to store the specific messages needed for specific DMs
dm_msg = []
dm_userlist = []

#msglist list is used to store ?ask messages
channellist = []
msglist = []

#limit to how many messages are able to be stored across all functions, change this value to your liking
msgstorelimit = 100

envpath = find_dotenv()
load_dotenv(envpath)

bot_token = os.environ.get("bot_token")

ai = Groq(api_key=os.environ.get("GROQ_API_KEY"))
client = commands.Bot(command_prefix="?", intents=intent)

#stores chats from askdm()
def storechats(msglst,idlst,message,ID):      
        print(len(msglst))
        if len(msglst) < msgstorelimit:
                print("should append")
                msglst.append(message)
                idlst.append(ID)
        else:
                print("---POPPING---")
                msglst.pop(0)
                idlst.pop(0)
                msglst.append(message)
                idlst.append(ID)

#retrieves messages required for a specific DM, this is so conversations from other DMs are not passed into different DMs
def specificmem(msglst,idlst,ID):
        localmemory = []
        for i in range(len(idlst)):
                if idlst[i] == ID:
                        print("SHOULD APPEND")
                        localmemory.append(msglst[i])
                        print(f"localmem {localmemory}")
                        print(f"round {i+1} complete")
        return localmemory

#function to get and store ai's response
async def airequest(qst,memory):
        response = ai.chat.completions.create(
        messages=[{"role":"user","content":qst}]+memory,
        model="openai/gpt-oss-120b",
        max_completion_tokens=2048,
        temperature=0.2,
        top_p=1,
        stream=False,
        reasoning_effort="medium"
        )
        global globresponse 
        globresponse = response.choices[0].message.content

#discord command ?ask defined as function ask()
#sends user's input and returns ai response to send in discord. Calls storechats() for memory
@client.command()
async def ask(ctx, *, question: str):
        if ctx.channel.type is discord.ChannelType.private:
                await discord.DMChannel.send(ctx.author,"Cannot use **?ask** command in DMs. Use **?askdm** command instead.")
        else:
                try:    
                        # serverid = ctx.guild.id
                        channelid = ctx.channel.id
                        #^ If server specific memory instead of channelspecific memory is desired, uncomment serverid and replace all instances of channelid with serverid

                        await ctx.message.delete()
                        placeholder = await ctx.send(f"Thinking... ")
                        secstart = time.time()

                        storechats(msglist,channellist,{"role": "user", "content": question},channelid)
                        localmem = specificmem(msglist,channellist,channelid)

                        await airequest(question,localmem)
                        respondvar = f"<@{ctx.author.id}>\n"+globresponse
                        respondvarnew = ""
                        length = print("LENGTH: "+str(len(respondvar)))
                        count = 0
                        if len(respondvar) > 2000:
                                while count != 1999-28:
                                        respondvarnew = respondvarnew + respondvar[count]   
                                        count = count+1
                                cut = True
                                respondvarnew = respondvarnew + "\n(Response cut at 2000 chars)"
                        else:
                                respondvarnew = respondvar

                        print("User asked:", question)

                        await ctx.send(respondvarnew)
                        secend = time.time()
                        await placeholder.edit(content=f"Thinking... (Thought for {secend-secstart:.1f}s)")
                        await asyncio.sleep(0.3)
                        await placeholder.delete()
                        print("Done request.")
                        

                        storechats(msglist,channellist,{"role": "assistant", "content": globresponse},channelid)
                        print(msglist)      
                        print("Stored messages: "+str(len(msglist)))

                except:
                        await placeholder.delete()
                        print("Error processing request.")
                        errorctx = await ctx.send("There was an error processing your request.")
                        await asyncio.sleep(3)
                        await errorctx.delete()




#defines discord command ?askdm as askdm()
#sends user's input and returns ai response to send in DMs to the user. Calls storechats() for memory
@client.command()
async def askdm(ctx, *, question: str):
        user = ctx.author
        userid = ctx.author.id
        placeholder = await discord.DMChannel.send(user,"Thinking...")
        secstart = time.time()
        
        print(f"--USER {user}--")
        storechats(dm_msg,dm_userlist,{"role": "user", "content": question},userid)

        print(dm_msg)

        localmemory = specificmem(dm_msg,dm_userlist,userid)

        await airequest(question,localmemory) 
        newresponse = ""

        if len(globresponse) > 2000:
                        respondvarstore = ""
                        respondvarnew = ""
                        limit = 2000
                        count = 0
                        twok_plus = True

                        while count != len(globresponse)-1:
                                respondvarnew = respondvarnew + globresponse[count]
                                count = count + 1
                                if count == limit:
                                        print(f"2k: {len(respondvarnew)}")
                                        await discord.DMChannel.send(user,respondvarnew)
                                        respondvarnew = ""
                                        limit = limit + 2000
                                
                        if count/2000 != count//2000:
                                await discord.DMChannel.send(user,respondvarnew) 
        else:
                await discord.DMChannel.send(user,globresponse)         

        storechats(dm_msg,dm_userlist,{"role": "assistant", "content": globresponse},userid)

        print(dm_msg)
        secend = time.time()
        await placeholder.edit(content=f"(Thought for {secend-secstart:.1f}s)")


@client.command()
async def ping(ctx):
        pingstart = time.time()
        pongmsg = await ctx.send("Pong!")
        pingend = time.time()
        await pongmsg.edit(content=f"Pong! ({(pingend-pingstart)*1000:.0f}ms)")

client.run(bot_token)
