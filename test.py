import connect

c = connect.Connection()
result = c.api_get("/lol-lobby/v2/lobby")

json = result.json()

# local_summonerid = c.get_summoner_id()
#
# for player in json:
#     if player["summonerId"] == local_summonerid:
#         print(player["firstPositionPreference"])