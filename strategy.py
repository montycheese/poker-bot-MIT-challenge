__author__ = 'montanawong'

from deuces3x.deuces.card import Card
from deuces3x.deuces.deck import Deck
from api import LegalFold, LegalRaise, LegalCall, LegalBet, LegalCheck
from deuces3x.deuces.evaluator import Evaluator
from random import uniform, random, shuffle
from .utils.prediction import generate_possible_hands as gen_hands, \
                                generate_possible_boards as gen_boards, \
                                EPSILON, \
                                create_action, \
                                simulate_games
from math import sqrt

FULL_DECK = set(Deck().GetFullDeck())

class PokerStrategy(object):
    """
    Base class for a Poker game bot strategy engine. This may be extended to handle multiple styles of Texas Hold em'.

    ====================  =====================================================
    Attribute             Description
    ====================  =====================================================

    DATA:
    name                  string; identifies your strategy
    evaluator             Evaluator; an Evaluator object from the deuces module that allows
                          your strategy to check the strength of the bot's hand.

    FUNCTIONS:
    determine_action()                 determine which action the bot should take given the situation
    calculate_aggression()             calculate the aggression level of a bot
    calculate_pre_flop_hand_strength() calculate the strength of the bot's hand pre-flop
    check_stack_size()                 checks and returns the size of a bot's stack in the current game
    check_opponents_last_move()        checks and returns the opponent's last move
    check_amount_in_pot()              checks and returns the amount of chips the bot current has in the pot.
    create_action()                    creates a LegalAction object or one of its subclasses, given action data
    ====================  ====================================================
    """
    def __init__(self, name=None):
        self.name = name
        self.evaluator = Evaluator()

    def determine_action(self, context, bot):
        """
        abstract
        :param context: (dict) A python dictionary containing an exhaustive table of everything related to the game,
                        including but not limited to move history, pot size, and players.
        :param bot: (MyBot) A MyBot object of the agent in the current HeadsUp poker game.

        :return:    action (LegalAction) returns the best determined action based on the bot's interpretation of the current
                    game state and strategy.
        """
        pass

    def calculate_aggression(self, num_bets, num_raises, num_checks):
        """
        Calculates aggression as a ratio of all bets & raises to checks

        :param num_bets: (int) number of bets made in a game
        :param num_raises: (int) number of raises made in a game
        :param num_checks: (int) number of checks made in a game

        :return:
                aggression: (float) a ratio representing our bots current aggression level
        """
        aggression = None
        try:
            aggression = num_bets + num_raises / num_checks
        except ZeroDivisionError:
            aggression = num_bets + num_raises / (num_checks + EPSILON)
        return aggression

    def calculate_pre_flop_hand_strength(self, pocket):
        """
        Calculates the hand strength before the flop. I normalized the score before outputting to force
        a ratio between 0 and 1. This allowed me to use it more easily in rule generation.
        The algorithm is inspired by the "Bill Chen method."
        See link for details, Bill Chen is a world renown Poker player/mathematician.
        http://www.simplyholdem.com/chen.html

        :param pocket: (list) a list of 2  Card objects that depict the bot's current hand

        :return:
                score (float) an irrational number between 0 and 1 that indiciates the strength of a pre-flop
                hand/pocket. This is used to determine actions leading up to the flop reveal.
        """

        curr_pocket = list(map(Card.new, pocket))
        score = 0

        high_rank = max(Card.get_rank_int(curr_pocket[0]), Card.get_rank_int(curr_pocket[1]))
        low_rank = min(Card.get_rank_int(curr_pocket[0]), Card.get_rank_int(curr_pocket[1]))

        #skew = lambda x: (x + 2) / 2.0

        #convert deuces lib hand rankings to Bill Chen's scale
        def skew(rank):
            if rank > 8:
                if rank == 12:
                    rank = 10
                elif rank == 11:
                    rank = 8
                elif rank == 10:
                    rank = 7
                elif rank == 9:
                    rank = 6
                else:
                    raise Exception('Invalid rank as input')
            else:
                rank = (rank + 2) / 2.0
            return rank

        skewed_high_rank = skew(high_rank)
        skewed_low_rank = skew(low_rank)

        if skewed_high_rank == skewed_low_rank:
            score += (max(skewed_high_rank * 2, 5))
        else:
            score += skewed_high_rank
            diff = (high_rank - low_rank)
            if diff == 1:
                score += 1
            elif diff < 3:
                score -= (diff-1)
            elif diff == 3:
                score -= (diff+1)
            else: #diff >= 4
                score -= 5

        #if the suit is same
        if Card.get_suit_int(curr_pocket[0]) == Card.get_suit_int(curr_pocket[1]):
            score += 2

        #normalize score to give percentage
        # 20 is the highest score possible, achieved with Pocket Aces
        score /= 20.0
        return score

    def check_stack_size(self, context, bot, our_stack):
        """
        Returns the size of the stack for a particular player in the game.

        :param context: (dict) A python dictionary containing an exhaustive table of everything related to the game,
                        including but not limited to move history, pot size, and players.
        :param bot: (MyBot) A MyBot object of the agent in the current HeadsUp poker game.
        :param our_stack: (boolean) A boolean value that indicates whether we are querying the size of
                        the bot's stack, or the opponent's stack.

        :return:
                (int) The size of the queried player's stack.
        """

        # if we have queried our player's stack size before, it will be stored in the
        # index attribute
        if bot.player_index and our_stack:
            return context['players'][bot.player_index]['stack']

        players = context['players']
        for i, player_data in enumerate(players):
            #return our stack
            if our_stack:
                if player_data['name'] == bot.name:
                    player_index = i
                    return player_data['stack']
            #return their stack
            else:
                if player_data['name'] != bot.name:
                    return player_data['stack']

    def check_opponents_last_move(self, context, bot):
        """
        Finds and returns the last move the opponent made this round.

        :param context: (dict) A python dictionary containing an exhaustive table of everything related to the game,
                        including but not limited to move history, pot size, and players.
        :param bot: (MyBot) A MyBot object of the agent in the current HeadsUp poker game.

        :return:
                (string) A string representing the last move made. E.g. ("CHECK", "BET", "CALL")

        :exception:
                (Exception) Throws a general exception if the opponent is not found in the history.
        """

        try:
            #go through history starting with most recent action
            for action_info in reversed(context['history']):
                if action_info['actor'] != bot.name and action_info['actor'] is not None:
                    return action_info['type']
        except Exception:
            return None

    def check_amount_in_pot(self, context, bot):
        """
        Queries the amount of chips in the current pot that belong to our player.

        :param context:(dict) A python dictionary containing an exhaustive table of everything related to the game,
                        including but not limited to move history, pot size, and players.
        :param bot: (MyBot) A MyBot object of the agent in the current HeadsUp poker game.

        :return:
                amount (int) the amount of chips in the pot that belonged to the player before the round started.
        """
        amount = 0
        for action_info in reversed(context['history']):
            if action_info['actor'] != bot.name:
                continue
            if action_info['type'] == 'POST':
                amount += action_info['amount']
                break
            elif action_info['type'] == 'CALL' or action_info['type'] == 'BET'or action_info['type'] == 'RAISE':
                amount += action_info['amount']
        return amount

    @staticmethod
    def create_action(action_info, bot):
        action = None

        if action_info['action'] == 'check':
            action = LegalCheck()
            bot.num_checks += 1
        elif action_info['action'] == 'call':
            action = LegalCall()
            action['amount'] = action_info['amount']
        elif action_info['action'] == 'bet':
            action = LegalBet(
                action_info['min'],
                action_info['max'])
            action['amount'] = action_info['amount']
            bot.num_bets += 1
        elif action_info['action'] == 'raise':
            action = LegalRaise(
                min_amount=action_info['min'],
                max_amount=action_info['max'])
            action['amount'] = action_info['amount']
            bot.num_raises += 1
        else:
            return LegalFold()

        return action


class HeadsUpStrategy(PokerStrategy):
    """
    Sub-class of PokerStrategy that focuses on determining actions for a bot playing
    Heads Up Texas hold 'em.

     ====================  =====================================================
    Attribute             Description
    ====================  =====================================================

    DATA:
    name                  string; identifies your strategy's name
    evaluator             Evaluator; an Evaluator object from the deuces module that allows
                          your strategy to check the strength of the bot's hand/pocket
    FUNCTIONS:
    calculate_hand_strength()            calculates the strength of a bot's hand/pocket at a given point in the game.
    calculate_effective_hand_strength()  improves the above calculation by leveraging negative/positive potential
    calculate_hand_potential()           calculates the positive and negative potential of a hand/pocket
    calculate_risk()                     calculates the risk of a certain move
    do_bet()                             determines whether or not a bet is the best course of action given the situation
    do_call()                            determines whether or not a call is the best course of action given the situation
    do_raise()                           determines whether or not a raise is the best course of action given the situation
    determine_action()                   determine which action the bot should take given the situation
    determine_pre_flop_action()          determine which action the bot should take pre-flop given the situation.
    simulate_games()                     simulates n iterations of a poker game pre-flop to calculate win/lose ratio of a hand
    ====================  ====================================================
    """

    def __init__(self, name=None):
        super().__init__(name)
        self.evaluator = Evaluator()
        self.do = dict()

    def determine_action(self, context, bot):
        #print(context)
        #print(context['players'])
        #print(self.pocket)

        self.do.clear()
        fold = True
        first_move = False
        opponents_last_move = None
        hand_strength = None
        stack_size = self.check_stack_size(context, bot, True)
        opponents_stack_size = self.check_stack_size(context, bot, False)

        # set whether or not we are making the first move
        if context['history'][-1]['type'] == 'DEAL':
            first_move = True
        elif context['history'][-1]['type'] == 'POST' and len(context['board']) == 0:
            first_move = True
        else:
            # if we aren't going first, determine the move is preceding this one
            opponents_last_move = self.check_opponents_last_move(context, bot)
            if opponents_last_move is None:
                raise Exception('Error reading history')

        # handle pre-flop action in another method
        if len(context['board']) == 0:
            return self.determine_preflop_action(context, bot.pocket, first_move, opponents_last_move, stack_size, opponents_stack_size)

        # calculate hand strength by simulating possible boards & opponent hands
        if len(context['board']) < 5:
            potential = self.calculate_hand_potential(context['board'], bot.pocket)
            hand_strength = self.calculate_effective_hand_strength(
                self.calculate_hand_strength(context['board'], bot.pocket),
                potential[0],
                potential[1])
        elif len(context['board']) == 5:
            hand_strength = self.calculate_hand_strength(context['board'], bot.pocket)
        else:
            raise Exception('Invalid board length')

        # check if we're all in
        if stack_size == 0:
            self.do['action'] = 'check'
            return create_action(bot)

        # if we are making the first move of the round
        if first_move:
            # percepts -> bet?
            # given percepts from the world, determine whether or not we should bet
            bet = self.do_bet(context, bot, stack_size, opponents_stack_size, hand_strength)
            if bet is not None:
                #bet info is stored in "do" dict
                pass
            else:
                self.do['action'] = 'check'
            fold = False
        # if we are going second this turn
        else:
            # if we are following a bet
            if opponents_last_move == 'BET':
                amount_to_call = context['legal_actions']['CALL']['amount']
                # if we are pressured to go all in
                if amount_to_call >= stack_size:
                    # percepts -> call?
                    # given percepts from the world, determine if we should call the bet
                    call = self.do_call(context, stack_size, opponents_stack_size, hand_strength)
                    if call:
                        fold = False
                    # fold otherwise
                # if our hand is strong or the move has low risk, evaluate possibility of raise/call
                elif random() <= hand_strength or random() / 2 <= (1 - self.calculate_risk(context, amount_to_call, stack_size)):
                    # percepts -> raise?
                    _raise = self.do_raise(context, bot, stack_size, opponents_stack_size, hand_strength)
                    if _raise is not None:
                        fold = False
                    # if raising is not recommended given the situation, check if calling is.
                    else:
                        # percepts -> call?
                        call = self.do_call(context, stack_size, opponents_stack_size, hand_strength)
                        if call:
                            fold = False
                        # if our algorithm doesn't suggest we raise or call, fold ultimately
            # if we need to reply to a check
            elif opponents_last_move == 'CHECK':
                #percepts -> bet?
                bet = self.do_bet(context, bot, stack_size, opponents_stack_size, hand_strength)
                if bet:
                    # bet info is stored in "do" dict when it is passed into the transition function
                    pass
                else:
                    # check by default
                    self.do['action'] = 'check'
                fold = False
            # lastly if we are responding to an opponent's raise
            elif opponents_last_move == 'RAISE':
                amount_to_call = context['legal_actions']['CALL']['amount']
                # if we are pressured to go all in from the last raise
                if amount_to_call >= stack_size:
                    # percepts -> all in?
                    call = self.do_call(context, stack_size, opponents_stack_size, hand_strength)
                    if call:
                        # all in! good luck.
                        fold = False
                # if our hand is strong, see if re-raising or checking is appropriate
                elif random() <= hand_strength:
                    # percepts -> re-raise?
                    _raise = self.do_raise(context, bot, stack_size, opponents_stack_size, hand_strength)
                    if _raise is not None:
                        fold = False
                    # else re-raising is not recommended, see if we should call the raise.
                    else:
                        # percepts -> call?
                        call = self.do_call(context, stack_size, opponents_stack_size, hand_strength)
                        if call:
                            fold = False
                # stochastically bluff when appropriate
                else:
                    # percepts -> appropriate to bluff?
                    if random() <= uniform(0.0, hand_strength/2.0):
                        _raise = self.do_raise(context, bot, stack_size, opponents_stack_size, hand_strength, True)
                        if _raise is not None:
                            fold = False

        if fold:
            self.do['action'] = 'fold'

        #print(do['action'])
        action = PokerStrategy.create_action(self.do, bot)
        return action

    def do_bet(self, context, bot, stack_size, opponents_stack_size, hand_strength):
        """
        Given percepts (aspects of the game state that our agent perceives such as:
        pot size, opponent's actions, hand strength, risk, aggression level, etc)
        from the world (poker game), determine whether or not a bet should be made, and if so, the quantity.

        The reduce the complexity of all the possible bets that could be made, I abstracted the betting sizes to three
        categories: large, medium, and small bets. Details can be seen in the code.

        :param context: (dict) A python dictionary containing an exhaustive table of everything related to the game,
                        including but not limited to move history, pot size, and players.
        :param bot: (MyBot) A MyBot object of the agent in the current HeadsUp poker game.
        :param stack_size: (int) The size of our bot's stack.
        :param opponents_stack_size: (int) The size of our opponent's stack.
        :param hand_strength: (float) The hand strength of our current hand/pocket which we are determining whether
                              or not to bet on.

        :return:
              bet (int) The size of the best bet determined given our situation.
              bet (None) None is returned if betting is determined to be disadvantageous.
        """
        min_bet = context['legal_actions']['BET']['min']
        bet = None

        # 3-> flop, 4-> turn, 5-> river
        turn = len(context['board'])

        # Reduce complexity by abstracting bets sizes into three categories: small, medium and large sized
        if random() <= hand_strength * (turn / 5.0):
            #maybe factor in the number of times I've already raised previously this turn
            #make large bet
            if self.calculate_aggression(bot.num_bets, bot.num_raises, bot.num_checks) < bot.aggression_factor and hand_strength >= 0.75:
                #ensure that bet cannot be smaller than min_bet
                bet = int(round(stack_size * hand_strength * (turn / 5.0)))
                bet = bet if bet > min_bet else min_bet
                bet = min(
                    bet,
                    stack_size
                )

            #make medium bet
            else:
                bet = int(round(stack_size / 2 * (1-hand_strength) * (turn / 5.0)))
                bet = bet if bet > min_bet else min_bet
                bet = min(
                    bet,
                    stack_size
                )
        #if risk is small and bot is aggressive, make a small bet
        elif random() <= (1 - self.calculate_risk(
                context,
                min_bet,
                stack_size
        ) and self.calculate_aggression(
            bot.num_bets,
            bot.num_raises,
            bot.num_checks
        ) < bot.aggression_factor):

            if stack_size < opponents_stack_size:
                bet = min_bet
            else:
                bet = min(
                    int(round(min_bet * (1 + hand_strength))),
                    stack_size
                )
        if bet:
            self.do['action'] = 'bet'
            self.do['amount'] = bet
            self.do['min'] = min_bet
            self.do['max'] = stack_size
        # print(bet)
        return bet

    def do_call(self, context, stack_size, opponents_stack_size, hand_strength):
        """
        Given percepts (aspects of the game state that our agent perceives such as:
        pot size, opponent's actions, hand strength, risk, aggression level, etc)
        from the world (poker game), determine whether or not a call should be made in response
        to a current bet or raise.

        :param context: (dict) A python dictionary containing an exhaustive table of everything related to the game,
                        including but not limited to move history, pot size, and players.
        :param stack_size: (int) The size of our bot's stack.
        :param opponents_stack_size: (int) The size of our opponent's stack.
        :param hand_strength: (float) The hand strength of our current hand/pocket which we are determining whether
                              or not to bet on.

        :return:
               call (boolean) True or False depending on whether or not we will call this round.
        """
        amount_to_call = context['legal_actions']['CALL']['amount']
        turn = len(context['board'])
        call = False
        at_stake = self.check_amount_in_pot(context)
        #If we are pressured to call ALL IN
        if amount_to_call >= stack_size:
            if random() / 3.0 * (turn / 5.0)  <= hand_strength:
                call = True
        elif random() <= hand_strength:
            #if risk is low and hand is strong, go ahead and call
            if random() <= (1- self.calculate_risk(context, amount_to_call, stack_size)):
                call = True
            #if we have alot at stake and we're at the river
            elif turn == 5 and random() <= (at_stake / context['pot']):
                call = True
        if call:
            self.do['action'] = 'call'
            self.do['amount'] = amount_to_call
        return call == True

    def do_raise(self, context, bot, stack_size, opponents_stack_size, hand_strength, all_in=False):
        """
        Given percepts (aspects of the game state that our agent perceives such as:
        pot size, opponent's actions, hand strength, risk, aggression level, etc)
        from the world (poker game), determine whether or not a (re)raise should be made in response
        to a current bet or raise.

        :param context: (dict) A python dictionary containing an exhaustive table of everything related to the game,
                        including but not limited to move history, pot size, and players.
        :param bot: (MyBot) A MyBot object of the agent in the current HeadsUp poker game.
        :param stack_size: (int) The size of our bot's stack.
        :param opponents_stack_size: (int) The size of our opponent's stack.
        :param hand_strength: (float) The hand strength of our current hand/pocket which we are determining whether
                              or not to bet on.
        :param all_in: (boolean) True or False value specifying whether or not we are making an all-in move

        :return:
               _raise (int) The size of the best (re)raise determined given our situation.
               _raise (None) None is returned if (re)raising is determined to be disadvantageous.
        """
        min_raise = context['legal_actions']['RAISE']['min']
        # turn's value will depend on the state of the board, 3-> flop, 4-> turn, 5-> river
        turn = len(context['board'])
        _raise = None

        if all_in:
            _raise = stack_size

        # Reducing complexity by abstracting 'raises' into three categories: small, medium and large sized
        elif random() <= hand_strength:
            #large raise
            if self.calculate_aggression(bot.num_bets, bot.num_raises, bot.num_checks) < bot.aggression_factor:
                #go all in
                if random() <= uniform(0.0, hand_strength/2.0):
                    _raise = stack_size
                #bet large
                else:
                    # ensure raise is at least the minimum value
                    _raise = int(round(stack_size / 2 * hand_strength * (turn / 5.0)))
                    _raise = _raise if _raise > min_raise else min_raise
                    _raise = min(
                        _raise,
                        stack_size
                    )

            #medium sized raise
            else:
                if stack_size > opponents_stack_size:
                    _raise = int(round(stack_size * (1-hand_strength) * (turn / 5.0)))
                    _raise = _raise if _raise > min_raise else min_raise
                    _raise = min(
                        _raise,
                        stack_size
                    )
                #small sized raise
                else:
                    _raise = min(
                        int(round(min_raise * (1 + hand_strength))),
                        stack_size
                    )

        if _raise:
            self.do['action'] = 'raise'
            self.do['amount'] = _raise
            self.do['min'] = min_raise
            self.do['max'] = stack_size

        return _raise

    def determine_preflop_action(self, context, bot, first_move, opponents_last_move, stack_size, opponents_stack_size):

        fold = True
        #50,000 takes roughly 7.4 seconds to calculate
        num_simulations = 50000
        preflop_odds = self.simulate_games(bot.pocket, context, num_simulations)
        hand_strength = self.calculate_pre_flop_hand_strength(bot.pocket)

        # if we are making the first move of the round
        if first_move:
            # percepts -> bet?
            # given percepts from the world, determine whether or not we should bet
            bet = self.do_bet(context, bot, stack_size, opponents_stack_size, hand_strength)
            if bet is not None:
                #bet info is stored in "do" dict
                pass
            else:
                self.do['action'] = 'check'
            fold = False
        # if we are going second this turn
        else:
            # if we are following a bet
            if opponents_last_move == 'BET':
                amount_to_call = context['legal_actions']['CALL']['amount']
                # if we are pressured to go all in
                if amount_to_call >= stack_size:
                    # percepts -> call?
                    # given percepts from the world, determine if we should call the bet
                    call = self.do_call(context, stack_size, opponents_stack_size, hand_strength)
                    if call:
                        fold = False
                    # fold otherwise
                # if our hand is strong or the move has low risk, evaluate possibility of raise/call
                elif random() <= hand_strength or random() / 2 <= (1 - self.calculate_risk(context, amount_to_call, stack_size)):
                    # percepts -> raise?
                    _raise = self.do_raise(context, bot, stack_size, opponents_stack_size, hand_strength)
                    if _raise is not None:
                        fold = False
                    # if raising is not recommended given the situation, check if calling is.
                    else:
                        # percepts -> call?
                        call = self.do_call(context, stack_size, opponents_stack_size, hand_strength)
                        if call:
                            fold = False
                        # if our algorithm doesn't suggest we raise or call, fold ultimately
            # if we need to reply to a check
            elif opponents_last_move == 'CHECK':
                #percepts -> bet?
                bet = self.do_bet(context, bot, stack_size, opponents_stack_size, hand_strength)
                if bet:
                    # bet info is stored in "do" dict when it is passed into the transition function
                    pass
                else:
                    # check by default
                    self.do['action'] = 'check'
                fold = False
            # lastly if we are responding to an opponent's raise
            elif opponents_last_move == 'RAISE':
                amount_to_call = context['legal_actions']['CALL']['amount']
                # if we are pressured to go all in from the last raise
                if amount_to_call >= stack_size:
                    # percepts -> all in?
                    call = self.do_call(context, stack_size, opponents_stack_size, hand_strength)
                    if call:
                        # all in! good luck.
                        fold = False
                # if our hand is strong, see if re-raising or checking is appropriate
                elif random() <= hand_strength:
                    # percepts -> re-raise?
                    _raise = self.do_raise(context, bot, stack_size, opponents_stack_size, hand_strength)
                    if _raise is not None:
                        fold = False
                    # else re-raising is not recommended, see if we should call the raise.
                    else:
                        # percepts -> call?
                        call = self.do_call(context, stack_size, opponents_stack_size, hand_strength)
                        if call:
                            fold = False
                # stochastically bluff when appropriate
                else:
                    # percepts -> appropriate to bluff?
                    if random() <= uniform(0.0, hand_strength/2.0):
                        _raise = self.do_raise(context, bot, stack_size, opponents_stack_size, hand_strength, True)
                        if _raise is not None:
                            fold = False
        '''TODO factor in aggression, risk, odds, and strength
        #risk = self.calculate_risk(context, bet_size, stack_size=)
        if first_move:
            #print((preflop_odds + hand_strength) / 2.0)
            if random() <= ((preflop_odds + hand_strength) / 2.0) * bot.aggression_factor:
                do['action'] = 'bet'
                do['amount'] = min(
                            int(round(context['legal_actions']['BET']['min'] * (1 + hand_strength))),
                            stack_size)
                do['min'] = context['legal_actions']['BET']['min']
                do['max'] = stack_size
            #temp
            else:
                do['action'] = 'check'
            fold = False
        else:
            #temp for sam
            if opponents_last_move == 'BET' or opponents_last_move == 'RAISE':
                amount_to_call = context['legal_actions']['CALL']['amount']
                #if pressured all-in
                if amount_to_call >= stack_size:
                    if random() <= ((preflop_odds + hand_strength) / 2.0) * bot.aggression_factor and hand_strength >= 0.75:
                        do['action'] = 'call'
                        do['amount'] = amount_to_call
                        fold = False
                #if risk is low call
                #elif random() <= ((preflop_odds + hand_strength) / 2.0) * self.aggression_factor:
                elif random() <= (1 - self.calculate_risk(context, amount_to_call, stack_size)):
                    do['action'] = 'call'
                    do['amount'] = amount_to_call
                    fold = False
                elif self.calculate_aggression(bot.num_bets, bot.num_raises, bot.num_checks) < bot.aggression_factor and random() <= preflop_odds:
                    do['action'] = 'raise'
                    do['amount'] = min(
                        int(round(context['legal_actions']['RAISE']['min'] * (1 + hand_strength))),
                        stack_size)
                    do['min'] = context['legal_actions']['RAISE']['min']
                    do['max'] = stack_size
                    fold = False
            else:
                do['action'] = 'check'
                fold = False
                #they checked
            #temp for sam'''

        if fold:
            self.do['action'] = 'fold'
        #print(do['action'])
        action = PokerStrategy.create_action(self.do, bot)
        return action

    def calculate_hand_strength(self, board, pocket):
        """
        Calculates hand strength by evaluating the current hand/pocket & visible board with every possible
        combination of hands the opponent may have. The algorithm is inspired by a similar one used by
        AI researchers at the University of Alberta. The literature is contained at this link:
        http://poker.cs.ualberta.ca/publications/billings.phd.pdf - see page 45

        :param board: (list) a list of 3-5 Card objects that depict the current visible game board
        :param pocket: (list) a list of 2 Card objects that depict the bot's current hand

        :return:
                hand_strength: (float) an irrational number between 0 and 1 and represents the
                strength of the current hand/pocket with respect to the current board.
        """

        ahead = 0
        behind = 0
        tied = 0

        # map each card in our pocket/hand and board from its str to integer representation
        curr_pocket = list(map(Card.new, pocket))
        board = list(map(Card.new, board))
        hand_rank = self.evaluator.evaluate(curr_pocket, board)

        #consider all combinations of cards that the opponent can have and rank ours against his/hers
        other_pockets = gen_hands(curr_pocket + board)

        # iterate through all possible opponent's hands
        for other_pocket in other_pockets:
            other_rank = self.evaluator.evaluate(other_pocket, board)
            #lower rank means stronger hand
            if hand_rank < other_rank:
                ahead += 1
            elif hand_rank == other_rank:
                tied += 1
            else:
                behind += 1
        hand_strength = (ahead + (tied / 2.0)) / (ahead + tied + behind)
        return hand_strength

    def calculate_effective_hand_strength(self, hand_strength, pos_potential, neg_potential, aggressive=True):
        """
        The difference between this and regular hand strength is that
        it factors in positive and/or negative potential into its calculation. I.e. it gives more weight to hands
        that have potential as more cards are revealed on the board, and less weight to hands that get weaker as
        more cards are revealed. (E.g. a [7h, 8h] may be weak on the flop, but has potential to become
        a straight or a flush after the turn, depending on the board)


        :param hand_strength: (float) The hand strength value of our current hand [0,1]
        :param pos_potential: (float) The positive potential of our hand, i.e. the probability
               that its strength will increase as more cards are revealed on the board.
        :param neg_potential: (float) The negative potential of our hand, i.e. the probability
               that its strength will decrease as more cards are revealed on the board.
        :param aggressive: (boolean) Whether or not our bot is playing aggressively. Determines whether or not
               we include negative potential in our calculation
        :return:
                (float) an irrational number between 0 and 1 that represents the effective hand strength of the current
                hand/pocket with respect to the current board.
        """
        if aggressive:
            return hand_strength + ((1-hand_strength) * pos_potential)
        return (hand_strength * (1 - neg_potential)) + ((1 - hand_strength) * pos_potential)


    def calculate_hand_potential(self, board, pocket):
        """
        Calculates positive and negative potential for a given hand. They are defined as:
        Positive potential: of all possible games with the current hand, all
        scenarios where the agent is behind but ends up winning are calculated.

        Negative potential: of all possible games with the current hand, all the
        scenarios where the agent is ahead but ends up losing are calculated.

        These values are used in conjunction with hand strength to estimate the effective
        hand strength value of a hand/pocket

        :param board: (list) a list of 3-5 Card objects that depict the current visible game board
        :param pocket: (list) a list of 2 Card objects that depict the bot's current hand

        :return:
                (list) containing the positive potential and negative potential respectively.
        """
        AHEAD = 0
        TIED = 1
        BEHIND = 2

        #init 3*3 array with 0's
        hand_potential = [[0] * 3 for i in range(3)]
        hp_total = [0] * 3

        curr_pocket = list(map(Card.new, pocket))
        board = list(map(Card.new, board))

        hand_rank = self.evaluator.evaluate(curr_pocket, board)

        other_pockets = gen_hands(curr_pocket + board)

        index = None
        for other_pocket in other_pockets:
            other_rank = self.evaluator.evaluate(other_pocket, board)
            #lower rank means stronger hand
            if hand_rank < other_rank:
                index = AHEAD
            elif hand_rank == other_rank:
                index = TIED
            else:
               index = BEHIND

            #check all possible future boards
            for possible_board in gen_boards(board, curr_pocket + other_pocket):

                our_best = self.evaluator.evaluate(curr_pocket, possible_board)
                other_best = self.evaluator.evaluate(other_pocket, possible_board)

                if our_best < other_best:
                    hand_potential[index][AHEAD] += 1
                elif our_best == other_best:
                    hand_potential[index][TIED] += 1
                else:
                    hand_potential[index][BEHIND] += 1
                hp_total[index] += 1

        pos_potential = 0.0
        try:
            pos_potential = (hand_potential[BEHIND][AHEAD] + (hand_potential[BEHIND][TIED]/2.0) +
                             (hand_potential[TIED][AHEAD]/2.0)) / (hp_total[BEHIND] + (hp_total[TIED]/2.0))
        except ZeroDivisionError:
            pos_potential = (hand_potential[BEHIND][AHEAD] + (hand_potential[BEHIND][TIED]/2.0) +
                             (hand_potential[TIED][AHEAD]/2.0)) / (hp_total[BEHIND] + (hp_total[TIED]/2.0) + EPSILON)

        neg_potential = 0.0
        try:
            neg_potential = (hand_potential[AHEAD][BEHIND] + (hand_potential[TIED][BEHIND]/2.0) +
                             (hand_potential[AHEAD][TIED]/2.0)) / (hp_total[AHEAD] + (hp_total[TIED]/2.0))
        except ZeroDivisionError:
            neg_potential = (hand_potential[AHEAD][BEHIND] + (hand_potential[TIED][BEHIND]/2.0) +
                             (hand_potential[AHEAD][TIED]/2.0)) / (hp_total[AHEAD] + (hp_total[TIED]/2.0) + EPSILON)

        return [pos_potential, neg_potential]

    def calculate_risk(self, context, bet_size, stack_size):
        """
        Calculates the 'risk' associated with a specific bet/raise action. The algorithm was inspired by
        a research paper on pattern classificaiton in No-Limit poker from the University of Regina.
        Source can be found here: http://www2.cs.uregina.ca/~hilder/refereed_conference_proceedings/canai07.pdf
        See page 4 for details.

        In a nutshell, the determinants of risk are the size of our bet and the potsize with respect to the maximum
        pot size (in the case that we go all in and the opponent calls). This number is forced to be between 0 and 1
        by multiplying for 4/3 then the geometric mean is taken.

        :param context: (dict) A python dictionary containing an exhaustive table of everything related to the game,
                        including but not limited to move history, pot size, and players.
        :param bet_size: (int) The size of the bet/raise that we are calculating risk for.
        :param stack_size: (int) The size of the bot's current stack.

        :return:
                risk (float) An irrational number between 0 and 1 that represents the 'riskiness' of a move,
                 as the number tends to 0, the move becomes less risky.
        """
        pot_size = context['pot']
        max_pot_size = context['pot'] + stack_size + self.check_stack_size(context, our_stack=False)
        risk = sqrt(
            (4 / 3.0) *
            ((bet_size * (2 * bet_size + pot_size)) /
             (max_pot_size * (bet_size + pot_size)))
        )

        return risk

    def simulate_games(self, pocket, context, iterations):
        wins = 0
        ties = 0
        evaluator = Evaluator()
        # change card representations from str to int
        pocket = list(map(Card.new, pocket))
        if len(context['board']) == 0:
            for i in range(iterations):
                deck = list(FULL_DECK - set(pocket))
                shuffle(deck)
                #set opponent's pocket
                opponent_pocket = [deck.pop() for i in range(2)]
                #generate random possible board
                board = [deck.pop() for i in range(5)]
                hand_rank = evaluator.evaluate(pocket, board)
                opponent_hand_rank = evaluator.evaluate(opponent_pocket, board)

                if hand_rank == opponent_hand_rank:
                    ties += 1
                    #smaller hand_rank means higher ranking cards
                elif hand_rank < opponent_hand_rank:
                    wins += 1

            odds = (wins + ties / 2.0) / iterations
            return odds
        else:
            raise Exception('not implemented yet')




