import connect as c

class ChampselectAction:

    def __init__(self, connection: c.Connection, mode: str, actionid: int | None, champid: int):
        self._connection: c.Connection = connection
        self._old_mode: str = mode
        self._mode: str = mode
        self.actionid: int = actionid
        self.champid: int = champid

    def __enter__(self):
        self._mode = "hover"
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._mode = self._old_mode

    def banning(self):
        return self._mode == "ban"

    def picking(self):
        return self._mode == "pick"

    def hovering(self):
        return self._mode == "hover"

    def skipping(self):
        return self._mode == "skip"

    def update_champid(self) -> bool:
        """ Update this object's champid, and return a bool indicating whether or not it was different from before. """
        if self.skipping():
            return False

        old_id: int = self.champid

        if self.banning():
            self.champid = self._connection.get_champid(self._connection.ban_intent)

        else: # we are picking or hovering
            self.champid = self._connection.get_champid(self._connection.pick_intent)

        return self.champid != old_id

    def get_mode(self):
        return self._mode