import configparser
from lcu_driver import Connector

config = configparser.ConfigParser()
config_dict = {}
config.read("config.ini")


def update_config_dict(section, dict):
    options = config.options(section)
    for option in options:
        dict[option] = config.get(section, option)


def update_config_dict(

searchx = int(add_dict("SearchBar")['searchx'])

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