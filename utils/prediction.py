__author__ = 'montanawong'

from deuces3x.deuces.deck import Deck
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