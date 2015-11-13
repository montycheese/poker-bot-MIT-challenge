__author__ = 'montanawong'

from montana.strategy import *

FULL_DECK = set(Deck().GetFullDeck())
EPSILON = float(1E-5)
EXT = '.txt'


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

    # generate boards with only one additional card (e.g. if at flop simulate turn, if at turn simulate river)
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

    The key is a sorted tuple of our bot's cards and the board. The value of the map was the hand strength.
    (e.g.) {(23123, 4343, 21343, 43111, 5353) : 0.75 }
    :return: (void)
    """
    strategy = HeadsUpStrategy()

    #generate all possible boards
    #board size = 3 first
    table = dict()
    deck = list(FULL_DECK)
    for first_card in range(len(deck)-2):
        for second_card in range(first_card+1, len(deck)-1):
            for third_card in range(second_card+1, len(deck)):
                board = [deck[first_card], deck[second_card], deck[third_card]]
                for pocket in generate_possible_hands(board):

                    hand_strength = strategy.calculate_hand_strength(board, pocket)
                    #key in table is sorted sequence of hand and board, value is the hand strength
                    #precompute values to avoid long computation times during gameplay
                    key = tuple(sorted(pocket + board))
                    table[key] = hand_strength

    #import ast
    with open('hand_strength_table.txt', 'a') as file:
        file.write(str(table))
    if file.closed:
        print("complete")
    else:
        raise IOError("Error closing file")




def create_ehs_table():
    """
    Pre computes all possible effective hand strengths for each combination of hands, boards, and opponent's hands.
    Stores these as a hashmap (dict)in a text file.

    The key is a sorted tuple of our bot's cards, opponent's cards, and the board. The value of the map was the ehs.

    I was unable to run this script in its entirety because I lack the time or computational power.
    This precomputed cache would trim down on calculations during gameplay however! Runs in roughly O(n^6) where n = 52
    :return: (void)
    """
    strategy = HeadsUpStrategy()
    #generate all possible boards
    table = dict()
    deck = list(FULL_DECK)
    i=0
    for first_card in range(len(deck)-2):
        for second_card in range(first_card+1, len(deck)-1):
            for third_card in range(second_card+1, len(deck)):
                board = [deck[first_card], deck[second_card], deck[third_card]]
                for pocket in generate_possible_hands(board):
                    hand_strength = strategy.calculate_hand_strength(board, pocket)
                    hand_potential = strategy.calculate_hand_potential(board, pocket)
                    ehs = strategy.calculate_effective_hand_strength(
                        hand_strength,
                        hand_potential[0],
                        hand_potential[1]
                    )
                    #key in table is sorted sequence of hand and board, value is the hand strength
                    #precompute values to avoid long computation times during gameplay
                    key = tuple(sorted(pocket + board))
                    table[key] = hand_strength


    with open('effective_hand_strength_table.txt', 'a') as file:
        file.write(str(table))
    if file.closed:
        print("complete")
    else:
        raise IOError("Error closing file")


def load_cache(key, table_name):
    import os.path
    import ast

    filename = table_name + EXT
    value = None
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            # parse file into python dict
            table = ast.literal_eval(file.read())
            # return the value stored at the key
            value = table[key]
    else:
        raise FileNotFoundError("%s doesn't exist", filename)

    if file.closed:
        return value
    else:
        raise IOError("Error closing file")


if __name__ == "__main__":
    create_ehs_table()
