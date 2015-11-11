__author__ = 'montanawong'

from deuces3x.deuces.deck import Deck
from deuces3x.deuces.card import Card
from deuces3x.deuces.evaluator import Evaluator
from api import LegalFold, LegalRaise, LegalCall, LegalBet, LegalCheck


FULL_DECK = set(Deck().GetFullDeck())
EPSILON = float(1E-5)

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

def create_hand_strength_table():
    #algorithm http://paginas.fe.up.pt/~niadr/PUBLICATIONS/LIACC_publications_2011_12/pdf/CN10_Estimating_Probability_Winning_LFT.pdf
    evaluator = Evaluator()
    #generate all possible boards
    #board size = 3 first
    table = {}
    deck = list(FULL_DECK)
    for first_card in range(len(deck)-2):
        for second_card in range(first_card+1, len(deck)-1):
            for third_card in range(second_card+1, len(deck)):
                board = [deck[first_card], deck[second_card], deck[third_card]]
                for pocket in generate_possible_hands(board):
                    ahead = 0
                    behind = 0
                    tied = 0

                    hand_rank = evaluator.evaluate(pocket, board)
                    #consider all combinations of cards that the opponent can have and rank ours against his/hers
                    other_pockets = generate_possible_hands(pocket + board)

                    for other_pocket in other_pockets:
                        other_rank = evaluator.evaluate(other_pocket, board)
                        #lower rank means stronger hand
                        if hand_rank < other_rank:
                            ahead += 1
                        elif hand_rank == other_rank:
                            tied += 1
                        else:
                            behind += 1
                    hand_strength =  (ahead + (tied / 2.0)) / (ahead + tied + behind)

                    '''
                    print(hand_strength)
                    print(list(map(Card.int_to_pretty_str,board)))
                    print(list(map(Card.int_to_pretty_str,pocket)))
                    print(list(map(Card.int_to_pretty_str,other_pocket)))
                    '''
                    #key in table is sorted sequence of hand and board, value is the hand strength
                    #precompute values to avoid long computation times during gameplay
                    key = tuple(sorted(pocket + board))
                    table[key] = hand_strength
                    import ast
                    with open('hand_strength_table.txt', 'a') as file:
                        file.write(str(table))
                    exit(0)


    import ast
    with open('hand_strength_table.txt', 'a') as file:
        file.write(str(table))




def create_ehs_table():
    """
    create effective hand strength cache. Prevents large calculation time during game
    :return: None
    """
    evaluator = Evaluator()
    #generate all possible boards
    table = {}
    deck = list(FULL_DECK)
    i=0
    for first_card in range(len(deck)-2):
        for second_card in range(first_card+1, len(deck)-1):
            for third_card in range(second_card+1, len(deck)):
                board = [deck[first_card], deck[second_card], deck[third_card]]
                for pocket in generate_possible_hands(board):
                    AHEAD = 0
                    TIED = 1
                    BEHIND = 2
                    ahead = 0
                    tied = 0
                    behind = 0

                    #init 3*3 array with 0's
                    hand_potential = [[0] * 3 for i in range(3)]
                    hp_total = [0] * 3

                    hand_rank = evaluator.evaluate(pocket, board)
                    #consider all combinations of cards that the opponent can have and rank ours against his/hers
                    other_pockets = generate_possible_hands(pocket + board)

                    for other_pocket in other_pockets:
                        other_rank = evaluator.evaluate(other_pocket, board)
                        #lower rank means stronger hand
                        if hand_rank < other_rank:
                            index = AHEAD
                            ahead += 1
                        elif abs(hand_rank == other_rank) < EPSILON:
                            index = TIED
                            tied += 1
                        else:
                            index = BEHIND
                            behind += 1

                        for possible_board in generate_possible_boards(board, pocket + other_pocket):

                            our_best = evaluator.evaluate(pocket, possible_board)
                            other_best = evaluator.evaluate(other_pocket, possible_board)

                            if our_best < other_best:
                                hand_potential[index][AHEAD] += 1
                            elif abs(our_best - other_best) < EPSILON:
                                hand_potential[index][TIED] += 1
                            else:
                                hand_potential[index][BEHIND] += 1
                            hp_total[index] += 1
                    hand_strength = (ahead + (tied / 2.0)) / (ahead + tied + behind)

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

                    effective_hand_strength = hand_strength + ((1-hand_strength) * pos_potential)
                    #key in table is sorted sequence of hand and board, value is the hand strength
                    #precompute values to avoid long computation times during gameplay
                    key = tuple(sorted(pocket + board))
                    table[key] = effective_hand_strength
                    i += 1
                    print(i)

    import ast
    with open('effective_hand_strength_table.txt', 'a') as file:
        file.write(str(table))
    print("complete")



if __name__ == "__main__":
    create_ehs_table()