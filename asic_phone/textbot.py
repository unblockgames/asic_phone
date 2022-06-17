import discord
from texts import text
TOKEN = 'OTA4NzgzNDU3MzAyMzYwMTg0.GF25Xg.t9ksrSDzD0MoGrE8FgKZ_ZhI2-U086fwN-xLUI'

client = discord.Client()


@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))


@client.event
async def on_message(message):
    if message.channel.name == 'phone':
        if str(message.content).startswith("!message"):
            message_array = str(message.content).split(' ')
            print(message_array[1] + ': ' + " ".join(message_array[2:]))
            if len(message_array[1]) != 12:
                await message.channel.send("Number incorrectly formatted..")
                return
            text(message_array[1], " ".join(message_array[2:]))
            await message.channel.send("Message sent.")
            return


def runTextBot():
    client.run(TOKEN)
    return
