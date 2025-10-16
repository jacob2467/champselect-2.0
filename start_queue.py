import connect
import lobby

c = connect.Connection()
lobby.start_queue(c)