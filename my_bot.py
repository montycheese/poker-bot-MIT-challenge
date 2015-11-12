__author__ = 'montanawong'

from random import uniform, random
from math import sqrt
from bots.bot import Bot
from deuces3x.deuces.evaluator import Evaluator
from deuces3x.deuces.card import Card
from .utils.prediction import generate_possible_hands as gen_hands, \
                                generate_possible_boards as gen_boards, \
                                EPSILON, \
                                create_action, \
                                simulate_games


#bug in engine, if both players tie, game gets OperatingError: Pot should be at zero

class MyBot(Bot):

    def __init__(self, name=None):
        super().__init__(name)
        self.evaluator = Evaluator()
        self.notes = dict()
        #ratio of betting to checking, adding another stochastic element to the agent
        self.aggression_factor = round(1 / uniform(0.3, 0.9))
        #player's index in player array
        self.player_index = None
        self.num_bets = 0
        self.num_checks = 0
        self.num_raises = 0
        self.at_stake = 0.0

    def get_memory(self):
        return self.notes


    '''
    notes: make betting decisions on hand value, risk and aggressiveness
    Since our agent is playing nolimit
    holdem and raise amounts are not pre-defined, we divide raises into three
    categoriessmall, medium, and large raiseswhich are considered as separate
    actions.
    create exhaustive lookup table of all combinations of hand/board
    http://www2.cs.uregina.ca/~hilder/refereed_conference_proceedings/canai07.pdf
    Dive into this tonight.
    http://arxiv.org/pdf/1301.5943.pdf
    opponent model is based on the percentage the player folds w/ his aggression factor.
    aggression factor = #bet+#raises/numcalls


    Calls are typically made in low risk situations. Raises, it is quite apparent, appear with high hand values.

    '''

    def get_action(self, context):
        #print(context)
        #print(self.pocket)

        do = dict()
        fold = True
        first_move = False
        opponents_last_move = None
        hand_strength = None
        stack_size = self.check_stack_size(context, True)
        opponents_stack_size = self.check_stack_size(context, False)

        #set whether or not we are making the first move
        if context['history'][-1]['type'] == 'DEAL':
            first_move = True
        elif context['history'][-1]['type'] == 'POST' and len(context['board']) == 0:
            first_move = True
        else:
            #if we aren't going first, determine the move is preceeding this one
            opponents_last_move = self.check_opponents_last_move(context)
            if opponents_last_move is None:
                raise Exception('Error reading history')

        #preflop
        if len(context['board']) == 0:
            return self.get_preflop_action(context, first_move, opponents_last_move, stack_size)

        if len(context['board']) < 5:
            potential = self.calculate_hand_potential(context['board'])
            hand_strength = self.calculate_effective_hand_strength(
                self.calculate_hand_strength(context['board']),
                potential[0],
                potential[1])

        elif len(context['board']) == 5:
            hand_strength = self.calculate_hand_strength(context['board'])
        else:
            raise Exception('Invalid board length')

        #try rudimentary algorithm
        #add weight to bet if they already have alot invested
        #at_stake = 0.0 #propagate this to attribute level

        #check if all in
        if stack_size == 0:
            do['action'] = 'check'
            return create_action(do, self)





        #if this is the first action in round and bot is first
        if first_move:
            if random() <= hand_strength:
                if self.calculate_aggression() < self.aggression_factor: #random() <= .3:
                    do['action'] = 'bet'
                    if hand_strength >= 0.85:
                        #all in
                        do['amount'] = stack_size

                    else:
                        do['amount'] = min(
                            int(round(context['legal_actions']['BET']['min'] * (1 + hand_strength))),
                            stack_size)

                else:
                    do['action'] = 'bet'
                    do['amount'] = context['legal_actions']['BET']['min']

                do['min'] = context['legal_actions']['BET']['min']
                do['max'] = stack_size
            else:
                do['action'] = 'check'
            fold = False
        else:
            #if second
            #if I need to call a bet
            if opponents_last_move == 'BET':# or opponents_last_move == 'RAISE':
                amount_to_call = context['legal_actions']['CALL']['amount']
                #pressured to go all in
                if amount_to_call >= stack_size:
                    if random() / 2.0 <= hand_strength:
                        do['action'] = 'call'
                        do['amount'] = amount_to_call
                        fold = False

                elif random() <= hand_strength:
                    #call/re raise if risk is low
                    if random() <= (1 - self.calculate_risk(context, amount_to_call, stack_size)):
                        if self.calculate_aggression() < self.aggression_factor: #random() <= .5:
                            do['action'] = 'raise'
                            do['amount'] = min(
                                int(round(context['legal_actions']['RAISE']['min'] * (1 + hand_strength))),
                                stack_size)
                            do['min'] = context['legal_actions']['RAISE']['min']
                            do['max'] = stack_size
                        else:
                            do['action'] = 'call'
                            do['amount'] = amount_to_call
                        fold = False
                    elif hand_strength >= 0.70:
                        do['action'] = 'call'
                        do['amount'] = amount_to_call
                        fold = False
                elif random()/ 2 <= (1 - self.calculate_risk(context, amount_to_call, stack_size)):
                    do['action'] = 'call'
                    do['amount'] = amount_to_call
                    fold = False
                    #fold otherwise
                    #not currently pressured to go all in
                    '''elif random() <= hand_strength:
                        #maybe factor in the number of times I've already raised previously this turn
                        if self.calculate_aggression() < self.aggression_factor: #random() <= .5:
                            do['action'] = 'raise'
                            do['amount'] = min(
                                int(round(context['legal_actions']['RAISE']['min'] * (1 + hand_strength))),
                                stack_size)
                            do['min'] = context['legal_actions']['RAISE']['min']
                            do['max'] = stack_size

                        else:
                            do['action'] = 'call'
                            do['amount'] = amount_to_call
                        fold = False
                        '''

                #else we have to fold
            #else if I need to reply to a check
            elif opponents_last_move == 'CHECK':
                if random() <= hand_strength:
                    #maybe factor in the number of times I've already raised previously this turn
                    #try using aggression_factor as a determinant of betting
                    if self.calculate_aggression() < self.aggression_factor:
                        do['action'] = 'bet'
                        do['amount'] = min(
                            int(round(context['legal_actions']['BET']['min'] * (1 + hand_strength))),
                            stack_size)

                        do['min'] = context['legal_actions']['BET']['min']
                        do['max'] = stack_size
                    else:
                        do['action'] = 'check'
                else:
                    do['action'] = 'check'
                fold = False

            elif opponents_last_move == 'RAISE':
                amount_to_call = context['legal_actions']['CALL']['amount']
                #pressured to go all in
                if amount_to_call >= stack_size:
                    if random() / 2.0 <= hand_strength:
                        do['action'] = 'call'
                        do['amount'] = amount_to_call
                        fold = False
                elif random() <= hand_strength:
                    #if hand_strength > .70:
                    if self.calculate_aggression() < self.aggression_factor:
                        do['action'] = 'raise'
                        do['amount'] = min(
                            int(round(context['legal_actions']['RAISE']['min'] * (1 + hand_strength))),
                            stack_size)
                        do['min'] = context['legal_actions']['RAISE']['min']
                        do['max'] = stack_size
                    else:
                        do['action'] = 'call'
                        do['amount'] = amount_to_call
                else:
                    #bluff
                    if random() <= uniform(0.0, hand_strength/2.0):
                         do['action'] = 'raise'
                         do['amount'] = stack_size
                         do['min'] = context['legal_actions']['RAISE']['min']
                         do['max'] = stack_size
                         fold = False


        if fold:
            do['action'] = 'fold'

        print(do['action'])
        return create_action(do, self)


    def set_pocket(self, card1, card2):
        self.pocket = [card1, card2]

    def set_memory(self, notes):
        self.notes = notes

    def do_bet(self, context, stack_size, opponents_stack_size, hand_strength):
        min_bet = context['legal_actions']['BET']['min']
        # 3-> flop, 4-> turn, 5-> river
        turn = len(context['board'])

      # abstract bets into three categories, small, medium and large sized
        if random() <= hand_strength:
            #maybe factor in the number of times I've already raised previously this turn
            #make large bet
            if self.calculate_aggression() < self.aggression_factor:
                bet = min(
                    int(round(stack_size * hand_strength * (turn / 5.0))),
                    stack_size
                )

            #make medium bet
            else:
                bet = min(
                    int(round(stack_size * (1-hand_strength) * (turn / 5.0))),
                    stack_size
                )
        #if risk is small and bot is aggressive, make a small bet
        elif random() <= (1 - self.calculate_risk(context, min_bet, stack_size) and self.calculate_aggression() < self.aggression_factor):
            bet = min(
                 int(round(min_bet * (1 + hand_strength) * (1 + uniform(0.0, turn / 5.0)))),
                 stack_size
            )
        else:
            return None

        return bet



    def do_raise(self, context, hand_strength, risk, aggressiveness):
        pass


    def get_preflop_action(self, context, first_move, opponents_last_move, stack_size):
        do = dict()
        fold = True
        #50,000 takes roughly 7.4 seconds to calculate
        num_simulations = 50000
        preflop_odds = simulate_games(self.pocket, context, num_simulations)
        hand_strength = self.calculate_pre_flop_hand_strength()

        #TODO factor in aggression, risk, odds, and strength
        #risk = self.calculate_risk(context, bet_size, stack_size=)
        if first_move:
            #print((preflop_odds + hand_strength) / 2.0)
            if random() <= ((preflop_odds + hand_strength) / 2.0) * self.aggression_factor:
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
                    if random() <= ((preflop_odds + hand_strength) / 2.0) * self.aggression_factor and hand_strength >= 0.75:
                        do['action'] = 'call'
                        do['amount'] = amount_to_call
                        fold = False
                #if risk is low call
                #elif random() <= ((preflop_odds + hand_strength) / 2.0) * self.aggression_factor:
                elif random() <= (1 - self.calculate_risk(context, amount_to_call, stack_size)):
                    do['action'] = 'call'
                    do['amount'] = amount_to_call
                    fold = False
                elif self.calculate_aggression() < self.aggression_factor and random() <= preflop_odds:
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
            #temp for sam

        if fold:
            do['action'] = 'fold'
        print(do['action'])
        return create_action(do, self)

    def calculate_aggression(self):
        aggression = None
        try:
            aggression = self.num_bets + self.num_raises / self.num_checks
        except ZeroDivisionError:
            aggression = self.num_bets + self.num_raises / (self.num_checks + EPSILON)
        return aggression

    def calculate_hand_strength(self, board=None):
        #this is only called post flop
        #algorithm http://paginas.fe.up.pt/~niadr/PUBLICATIONS/LIACC_publications_2011_12/pdf/CN10_Estimating_Probability_Winning_LFT.pdf
        ahead = 0
        behind = 0
        tied = 0

        curr_pocket = list(map(Card.new, self.pocket))
        board = list(map(Card.new, board))
        hand_rank = self.evaluator.evaluate(curr_pocket, board)
        #consider all combinations of cards that the opponent can have and rank ours against his/hers
        other_pockets = gen_hands(curr_pocket + board)

        for other_pocket in other_pockets:
            other_rank = self.evaluator.evaluate(other_pocket, board)
            #lower rank means stronger hand
            if hand_rank < other_rank:
                ahead += 1
            elif hand_rank == other_rank:
                tied += 1
            else:
                behind += 1
        return (ahead + (tied / 2.0)) / (ahead + tied + behind)

    def calculate_effective_hand_strength(self, hand_strength, pos_potential, neg_potential, aggressive=True):
        if aggressive:
            return hand_strength + ((1-hand_strength) * pos_potential)
        return (hand_strength * (1 - neg_potential)) + ((1 - hand_strength) * pos_potential)


    def calculate_pre_flop_hand_strength(self):
        #process inspired from Poker expert Bill Chen http://www.simplyholdem.com/chen.html
        curr_pocket = list(map(Card.new, self.pocket))
        score = 0

        high_rank = max(Card.get_rank_int(curr_pocket[0]), Card.get_rank_int(curr_pocket[1]))
        low_rank = min(Card.get_rank_int(curr_pocket[0]), Card.get_rank_int(curr_pocket[1]))

        #skew = lambda x: (x + 2) / 2.0

        #convert deuces hank rankings to bill chen's scale
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
        #print(score / 20.0)
        #normalize score to give percentage
        return score / 20.0

    def calculate_hand_potential(self, board=None):
        AHEAD = 0
        TIED = 1
        BEHIND = 2

        #init 3*3 array with 0's
        hand_potential = [[0] * 3 for i in range(3)]
        hp_total = [0] * 3

        curr_pocket = list(map(Card.new, self.pocket))
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

        '''
        Positive potential: of all possible games with the current hand, all
        scenarios where the agent is behind but ends up winning are calculated.
        '''
        pos_potential = 0.0
        try:
            pos_potential = (hand_potential[BEHIND][AHEAD] + (hand_potential[BEHIND][TIED]/2.0) +
                             (hand_potential[TIED][AHEAD]/2.0)) / (hp_total[BEHIND] + (hp_total[TIED]/2.0))
        except ZeroDivisionError:
            pos_potential = (hand_potential[BEHIND][AHEAD] + (hand_potential[BEHIND][TIED]/2.0) +
                             (hand_potential[TIED][AHEAD]/2.0)) / (hp_total[BEHIND] + (hp_total[TIED]/2.0) + EPSILON)

        '''
        Negative potential: of all possible games with the current hand, all the
        scenarios where the agent is ahead but ends up losing are calculated.
        '''
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
        calculates the risk of calling a bet/raise
        :param context:
        :return:
        """
        pot_size = context['pot']
        max_pot_size = context['pot'] + stack_size + self.check_stack_size(context, our_stack=False)
        risk = sqrt(
            (4 / 3.0) *
            ((bet_size * (2 * bet_size + pot_size)) /
             (max_pot_size * (bet_size + pot_size)))
        )
        #print("risk= " + str(risk))
        return risk

    def check_stack_size(self, context, our_stack):
        if self.player_index and our_stack:
            return context['players'][self.player_index]['stack']

        players = context['players']
        for i, player_data in enumerate(players):
            #return our stack
            if our_stack:
                if player_data['name'] == self.name:
                    self.player_index = i
                    return player_data['stack']
            #return their stack
            else:
                if player_data['name'] != self.name:
                    return player_data['stack']

            #if player_data['name'] == self.name:
             #   if player_data['name'] == self.name:
              #      self.player_index = i
               # return player_data['stack']
        raise Exception("Player not found in players")

    def check_opponents_last_move(self, context):

        try:
            #go through history starting with most recent action
            for action_info in reversed(context['history']):
                if action_info['actor'] != self.name and action_info['actor'] is not None:
                    return action_info['type']
        except Exception:
            return None


