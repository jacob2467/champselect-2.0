import connect

c = connect.Connection()

c.populate_champ_table()
c.update_champselect()
runes = c.get_recommended_runepage()

print(runes)

# local_summonerid = c.get_summoner_id()
#
# for player in json:
#     if player["summonerId"] == local_summonerid:
#         print(player["firstPositionPreference"])