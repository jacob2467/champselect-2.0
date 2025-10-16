import connect
import lobby

c = connect.Connection()

c.populate_champ_table()

lobby.create_lobby(c, "draft")