class Player:
    def __init__(self, id: int, name: str, isMafia: bool = False, isDoctor: bool = False, isAlive: bool = True):
        self.id = id
        self.name = name
        self.isMafia = isMafia
        self.isDoctor = isDoctor
        self.isAlive = isAlive