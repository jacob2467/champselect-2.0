import configparser
from lcu_driver import Connector

config = conf

client = Connector()

@client.ready
async def lcu_ready(connection):
    summoner = await connection.request("get", "/lol-summoner/v1/current-summoner")
    print(await summoner.json())


@client.ws.register("/lol-matchmaking/v1/ready-check", event_types=("UPDATE",))
async def accept_match(connection, event):
    if event.data["playerResponse"] == "None":
        await connection.request("post", "/lol-matchmaking/v1/ready-check/accept")
        print("Match has been accepted!")


client.start()