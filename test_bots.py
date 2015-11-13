__author__ = 'montanawong'
from .my_bot import MyBot
from .strategy import AlwaysCall, AlwaysBet


class TestBot1(MyBot):
    """
    This bot always checks/calls no matter what
    """
    def __init__(self, name):
        super().__init__(self)
        self.strategy = AlwaysCall()
        self.name = name

    def get_action(self, context):
        action = self.strategy.determine_action(context, self)
        return action

    def set_pocket(self, card1, card2):
        super().set_pocket(card1, card2)

class TestBot2(MyBot):
    """
    This bot always bets/calls no matter what
    """
    def __init__(self, name):
        super().__init__()
        self.strategy = AlwaysBet()
        self.name = name

    def get_action(self, context):
        action = self.strategy.determine_action(context, self)
        return action

    def set_pocket(self, card1, card2):
        super().set_pocket(card1, card2)


