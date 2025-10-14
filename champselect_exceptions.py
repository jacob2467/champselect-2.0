# No need for custom exception behavior - just want helpful exception names

class ClientConnectionError(Exception):
    pass

class ChampionError(Exception):
    pass