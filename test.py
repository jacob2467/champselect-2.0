import connect

c = connect.Connection()

c.populate_champ_table()

c.update_primary_role()

print(c.user_role)