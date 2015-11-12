__author__ = 'montanawong'

from deuces3x.deuces.deck import Deck
from deuces3x.deuces.card import Card
from deuces3x.deuces.evaluator import Evaluator
from api import LegalFold, LegalRaise, LegalCall, LegalBet, LegalCheck


FULL_DECK = set(Deck().GetFullDeck())
EPSILON = float(1E-5)

class Brain():

    def calculate_aggression(self, num_bets, num_raises, num_checks):
        return num_bets + num_raises / num_checks

    def calculate_hand_strength(self, board=None):
        #assume this is only called post flop

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

        if high_rank == low_rank:
            score += (max(high_rank * 2, 5))
        else:
            score += high_rank
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

        return score

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
            elif abs(hand_rank == other_rank) < EPSILON:
                index = TIED
            else:
               index = BEHIND
            #hp_total[index] += 1

            #check all possible future boards
            for possible_board in gen_boards(board, curr_pocket + other_pocket):

                our_best = self.evaluator.evaluate(curr_pocket, possible_board)
                other_best = self.evaluator.evaluate(other_pocket, possible_board)

                if our_best < other_best:
                    hand_potential[index][AHEAD] += 1
                elif abs(our_best - other_best) < EPSILON:
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
             (max_pot_size * (bet_size + pot_size))))
        print("risk= " + str(risk))
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

    def generate_possible_hands(cards_in_play):
        cards_in_play = set(cards_in_play)

        #domain only contains cards not visible by our player
        domain = list(FULL_DECK - cards_in_play)
        combinations = []

        #generate all 2 pair combinations of cards that the other player may have
        for first_card in range(len(domain)-1):
            for second_card in range(first_card+1, len(domain)):
                combinations.append([domain[first_card], domain[second_card]])

        #print(combinations) #amount should be len(domain) Choose 2
        return combinations

    def generate_possible_boards(curr_board, player_hands):

        if len(curr_board) < 3 or len(curr_board) >= 5:
            raise Exception('invalid board length')

        cards_in_play = set(curr_board + player_hands)
        domain = list(FULL_DECK - cards_in_play)

        #if len(curr_board) == 4:
        #testing only trying next card b/c doing 2 takes way too long
        return [([domain[i]] + curr_board[:]) for i in range(len(domain))]


        #board is only size 3
        new_boards = []

        for first_card in range(len(domain)-1):
            for second_card in range(first_card+1, len(domain)):
                new_boards.append(curr_board[:] + [domain[first_card], domain[second_card]])


        return new_boards


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

