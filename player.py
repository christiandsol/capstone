class Player:
    def __init__(self, number: int, name: str, isMafia: bool = False, isDoctor: bool = False, isAlive: bool = True):
        self.number = number
        self.name = name
        self.isMafia = isMafia
        self.isDoctor = isDoctor
        self.isAlive = isAlive