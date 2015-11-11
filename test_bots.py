__author__ = 'montanawong'
from .my_bot import MyBot
from .utils.prediction import *


class TestBot1(MyBot):
    """
    This bot always checks/calls no matter what
    """
    def get_action(self, context):
        if len(context['board']) == 0:
            return self.get_preflop_action(context)

        #assume for now at this point we are post flop
        stack_size = self.check_stack_size(context, True)
        opponents_stack_size = self.check_stack_size(context, False )

        do = dict()
        fold = True
        first_move = False
        opponents_last_move = None

        if context['history'][-1]['type'] == 'DEAL':
            first_move = True
        else:
            opponents_last_move = self.check_opponents_last_move(context)

        #try rudimentary algorithm
        #add weight to bet if they already have alot invested
        #at_stake = 0.0 #propagate this to attribute level

        #check if all in
        if stack_size == 0:
            do['action'] = 'check'
            return create_action(do, self)

        #if this is the first action in round and bot is first
        if first_move:
            do['action'] = 'check'
            fold = False
        else:
            #if second
            #if I need to call a bet
            if opponents_last_move == 'BET' or opponents_last_move == 'RAISE':
                amount_to_call = context['legal_actions']['CALL']['amount']
                do['action'] = 'call'
                do['amount'] = amount_to_call
                fold = False
            #else if I need to reply to a check
            elif opponents_last_move == 'CHECK':
                do['action'] = 'check'
                fold = False
            #raise
            elif opponents_last_move == 'RAISE':
                amount_to_call = context['legal_actions']['CALL']['amount']
                do['action'] = 'call'
                do['amount'] = amount_to_call
                fold = False

        if fold:
            do['action'] = 'fold'

        print(self.name + ' is: ' + do['action'] + 'ing')
        return create_action(do,self)

    def set_pocket(self, card1, card2):
        super().set_pocket(card1, card2)

class TestBot2(MyBot):
    """
    This bot always bets/calls no matter what
    """
    def get_action(self, context):
        if len(context['board']) == 0:
            return self.get_preflop_action(context)

        #assume for now at this point we are post flop
        stack_size = self.check_stack_size(context, True)
        opponents_stack_size = self.check_stack_size(context, False )

        do = dict()
        fold = True
        first_move = False
        opponents_last_move = None

        if context['history'][-1]['type'] == 'DEAL':
            first_move = True
        else:
            opponents_last_move = self.check_opponents_last_move(context)

        #try rudimentary algorithm
        #add weight to bet if they already have alot invested
        #at_stake = 0.0 #propagate this to attribute level

        #check if all in
        if stack_size == 0:
            do['action'] = 'check'
            return create_action(do, self)

        #if this is the first action in round and bot is first
        if first_move:
            do['action'] = 'bet'
            do['amount'] = context['legal_actions']['BET']['min']
            do['min'] = context['legal_actions']['BET']['min']
            do['max'] = stack_size
            fold = False
        else:
            #if second
            #if I need to call a bet
            if opponents_last_move == 'BET':
                amount_to_call = context['legal_actions']['CALL']['amount']
                do['action'] = 'call'
                do['amount'] = amount_to_call
                fold = False
            #else if I need to reply to a check
            elif opponents_last_move == 'CHECK':
                do['action'] = 'bet'
                do['amount'] = context['legal_actions']['BET']['min']
                do['min'] = context['legal_actions']['BET']['min']
                do['max'] = stack_size
                fold = False
            #raise
            elif opponents_last_move == 'RAISE':
                amount_to_call = context['legal_actions']['CALL']['amount']
                do['action'] = 'call'
                do['amount'] = amount_to_call
                fold = False

        if fold:
            do['action'] = 'fold'

        print(self.name + ' is: ' + do['action'] + 'ing')
        return create_action(do,self)

    def set_pocket(self, card1, card2):
        super().set_pocket(card1, card2)