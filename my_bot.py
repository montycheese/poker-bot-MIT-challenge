__author__ = 'montanawong'

from random import uniform
from bots.bot import Bot
from .strategy import HeadsUpStrategy

# bug in engine, if both players tie, game gets OperatingError: Pot should be at zero

class MyBot(Bot):
    """
     My custom Bot implementation that extends BlackBird's base Bot class. The logic
     and strategy of this bot is inspired by my own studies of partially observable
     games in A.I., as well as current academic literature on the subject of rational
     poker agents. Sources are noted where used. This class may be extended to
     be used as a basis for other poker bots. They must use strategy objects to
     create decisions however.

    ====================  =====================================================
    Attribute             Description
    ====================  =====================================================

    DATA:
    name                  string; identifies your bot
    evaluator             Evaluator; an Evaluator object from the deuces module that allows
                          your bot to check the rank of it's hand with respect to the board
    aggression_factor     float or None; ratio of your bot's betting & raising to checking
    player_index          int; the position in the players array where your bot is indexed
    num_bets              int; the number of bets your bot has made in the current game
    num_checks            int; the number of checks your bot has made in the current game
    num_raises            int; the number of raises your bot has made in the current game

    FUNCTIONS:
    get_action()          send an action to the engine for the hand
    get_memory()          send a memory dictionary to the engine
    set_memory()          receive a memory dictionary from the engine
    set_pocket()          receive your cards from the engine
    ====================  ====================================================
    """

    def __init__(self, name=None):
        super().__init__(name)
        self.strategy = HeadsUpStrategy()
        self.aggression_factor = round(1 / uniform(0.5, 0.9))
        self.player_index = None
        self.num_bets = 0
        self.num_checks = 0
        self.num_raises = 0
        self.notes = None

    def get_memory(self):
        """
        @Override

        :return:
        """
        return self.notes

    def get_action(self, context):
        """
        @Override

        Gets an action determined by the bot's strategy and returns it to the game engine.

        :param context: (dict) A sub-classed python dictionary containing an exhaustive table of everything related
                         to the game, including but not limited to move history, pot size, and players.

        :return:
                action (LegalAction) returns the best determined action based on the bot's interpretation of the current
                        game state and strategy.
        """
        #print(context['players'])
        #print(self.pocket)

        action = self.strategy.determine_action(context, self)
        return action

    def set_pocket(self, card1, card2):
        """
        @Override

        :param card1:
        :param card2:
        :return:
        """
        self.pocket = [card1, card2]

    def set_memory(self, notes):
        """
        @Override

        :param notes:
        :return:
        """
        self.notes = notes
