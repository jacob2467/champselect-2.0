import connect

c = connect.Connection()

c.populate_champ_table()
c.update_champselect()
runes = c.get_recommended_runepage()

print(runes)