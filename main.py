import configparser
from lcu_driver import Connector

config = configparser.ConfigParser()
config.read("config.ini")


def cfg_to_dict():
    dict = {}
    options = config.options(section)
    for option in options:
        dict[option] = config.get(option)

    return dict


def update_config_dict():
    return


config_dict = cfg_to_dict()

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