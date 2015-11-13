__author__ = 'montanawong'

from deuces3x.deuces.deck import Deck
from deuces3x.deuces.card import Card
from deuces3x.deuces.evaluator import Evaluator


FULL_DECK = set(Deck().GetFullDeck())
EPSILON = float(1E-5)


def generate_possible_hands(cards_in_play):
    """
    Generates a list containing possible hands for an opponent given
    visible board cards, and the bot's hand.
    :param cards_in_play: cards currently visible to the bot
    :return:
            combinations (list) a multidimensional array containing all
            possible hands the opponent can have.
    """
    cards_in_play = set(cards_in_play)

    #deck only contains cards not visible by our player
    deck = list(FULL_DECK - cards_in_play)
    combinations = []

    #generate all 2 pair combinations of cards that the other player may have
    for first_card in range(len(deck)-1):
        for second_card in range(first_card+1, len(deck)):
            combinations.append([deck[first_card], deck[second_card]])

    #print(combinations) #amount should be len(deck) Choose 2
    return combinations


def generate_possible_boards(curr_board, player_hands):
    """
    Generates a list of possible boards given a board at either the flop or the turn.

    :param curr_board: (list) The current board in the round
    :param player_hands: (list) containing the bot's hand and a simulation of the opponents hand.

    :return:
            (list) a multidimensional array containing all possible boards of len(curr_board) + 1
    """
    if len(curr_board) < 3 or len(curr_board) >= 5:
        raise Exception('invalid board length')

    cards_in_play = set(curr_board + player_hands)
    deck = list(FULL_DECK - cards_in_play)

    # generate boards with an additional card
    return [([deck[i]] + curr_board[:]) for i in range(len(deck))]

    '''
    Computing boards up to size 5 from the flop is too computationally
    expensive.
    board is only size 3
    new_boards = []

    for first_card in range(len(deck)-1):
        for second_card in range(first_card+1, len(deck)):
            new_boards.append(curr_board[:] + [deck[first_card], deck[second_card]])


    return new_boards
    '''



def create_hand_strength_table():
    """
    Pre computes all possible hand strengths for each combination of hands, boards, and opponent's hands.
    I was unable to run this script in its entirety because I lack the time or computational power.
    This precomputed cache would trim down on calculations during gameplay however!
    :return: (void)
    """
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
    Pre computes all possible effective hand strengths for each combination of hands, boards, and opponent's hands.
    Stores these as a hashmap (dict)in a text file.

    The key is a sorted tuple of our bot's cards, opponent's cards, and the board. The value of the map was the ehs.

    I was unable to run this script in its entirety because I lack the time or computational power.
    This precomputed cache would trim down on calculations during gameplay however!
    :return: (void)
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


def load_cache():
    pass


if __name__ == "__main__":
    create_ehs_table()