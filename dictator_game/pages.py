from otree.api import *
from .models import Constants,generate_numbers
import json
import re
import numpy as np
import settings


class GoalOriented(Page): 

    """ Page where users interact with ChatGPT in real-time """
    form_model = 'player'
    form_fields = []


    def is_displayed(self):
        """ Ensure GoalOriented runs for each round in the part """
        current_part = Constants.get_part(self.round_number)
        display_round = (self.round_number - 1) % Constants.rounds_per_part + 1

        return (current_part == 2 or (current_part == 3 and self.player.delegate_decision_optional)) and (display_round -1) % Constants.rounds_per_part ==0
    
    def vars_for_template(self):
        current_part = Constants.get_part(self.round_number)
        return {
            'current_part' : current_part,
         }
        
    def before_next_page(self):
        final_response=self.get_final_response()
        self.save_allocations_to_future_rounds(final_response)
        print('Saved Allocations from AI Assistant')
        
    def get_final_response(self):

        
        conversation = json.loads(self.player.orientation_history)
        print('Conversation:',conversation)

        index=str(self.player.sample_cnt-1)
        last_key = list(conversation.keys())[-1] 
        last_goal_message = conversation[last_key]
       
        if last_goal_message != None:
            print('Last goal Message: ',last_goal_message) 
            return last_goal_message
        else: 
            print('Error found, Sending Sample')
            return "10,10,10,10,10,10,10,10,10,10"

    def save_allocations_to_future_rounds(self, final_goal_response):
    
        allocation_values = list(map(int,final_goal_response['allocations'].split(',')))
        mean_value_selected = final_goal_response['slider_value']
        print('Last Allocation: ',allocation_values)
        try:
            if len(allocation_values) < 10:
                print("⚠️ Live method did not return 10 allocations, skipping storage.")
                return

            round_number=self.round_number
            print('Ongoing Round: ',round_number)
            for i in range(1,11):
                future_player = self.player.in_round(round_number)
                self.round_number=round_number

                future_player.allocation = allocation_values[i-1]
                print(f"✅ Saved allocation {future_player.allocation} for Round {round_number}")
                round_number = round_number + 1

        except (ValueError, IndexError):
            print("⚠️ Error:  response is not formatted correctly, skipping.")
    

    
    def live_method(self, data):
        print('In live method')
        if 'slider_value' in data:
            print('Received slider value:', float(data['slider_value']))
            
            allocations = generate_numbers(float(data['slider_value']),'goal')
            allocations_str = ','.join(map(str, allocations['allocations']))
            
            if not self.orientation_history:
                history = {}
            else:
                history = json.loads(self.orientation_history)
            
            history[self.sample_cnt] = {'slider_value': float(data['slider_value']) , 'allocations':  allocations_str }
            
            self.orientation_history = json.dumps(history)
            self.sample_cnt += 1

            print(f'Sample History: {self.orientation_history}')
            print('Sending back the msg to HTML:', allocations_str)
            return {self.id_in_group: {"response": allocations_str}}   

class InformedConsent(Page):
    form_model = 'player'
    form_fields = ['prolific_id']
    def is_displayed(self):
        return self.round_number == 1


class Introduction(Page):
    def is_displayed(self):
        print('Using pages.py')
        return self.round_number == 1


class ComprehensionTest(Page):
    form_model = 'player'
    form_fields = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8']

    def is_displayed(self):
        return not self.player.is_excluded and self.round_number == 1

    def error_message(self, values):
        correct_answers = {
            'q1': 'b',
            'q2': 'c',
            'q3': 'b',
            'q4': 'd',
            'q5': 'a',
            'q6': 'a',
            'q7': 'b',
            'q8': 'a',
        }

        incorrect = [
            q for q, correct in correct_answers.items()
            if values.get(q) != correct or not values.get(q)
        ]

        if incorrect:
            self.player.comprehension_attempts += 1

            if self.player.comprehension_attempts == 1:
                 return f"You have failed questions: {', '.join(incorrect)}. You now only have 2 attempts"
            
            elif self.player.comprehension_attempts == 2:
                 return f"You have failed questions: {', '.join(incorrect)}. You now only have 1 attempt"
            
            elif self.player.comprehension_attempts == 1:
                 return f"You have failed questions: {', '.join(incorrect)}. You now only have last attempt"
            else:
                self.player.is_excluded = True

class FailedTest(Page):
    def is_displayed(self):
        return self.player.is_excluded



class Instructions(Page):
    def is_displayed(self):
        current_part = Constants.get_part(self.round_number)

        return  (self.round_number - 1) % Constants.rounds_per_part == 0

    def vars_for_template(self):
        current_part = Constants.get_part(self.round_number)
        return {
            'current_part': current_part,
            'incorrect_answers': self.player.incorrect_answers,

        }




class Decision(Page):
    form_model = 'player'
    form_fields = ['allocation']

 

    def is_displayed(self):
        current_part = Constants.get_part(self.round_number)
        return not (current_part == 2 or (current_part == 3 and self.player.delegate_decision_optional))
    

    def vars_for_template(self):
        current_part = Constants.get_part(self.round_number)
        display_round = (self.round_number - 1) % Constants.rounds_per_part + 1
        allocation = 0
       
        if current_part == 2:
            current_player = self.player.in_round(display_round)
            allocation=current_player.allocation
        elif current_part == 3 and self.player.delegate_decision_optional:
             allocation = self.player.get_agent_decision_optional(display_round)
        
        elif current_part ==3 and not self.player.delegate_decision_optional:
            current_player = self.player.in_round(display_round)
            allocation=current_player.allocation
        return {
            'round_number': display_round,
            'current_part': current_part,
            'decision_mode': (
                "agent" if (current_part == 2 or (current_part == 3 and self.player.delegate_decision_optional)) else "manual"
            ),
            'player_allocation': allocation,
            'alert_message': self.participant.vars.get('alert_message', ""),
                }

    def before_next_page(self):
        import json
        import random

 
        current_part = Constants.get_part(self.round_number)
        display_round = (self.round_number - 1) % Constants.rounds_per_part + 1

        if current_part == 1  :
            if self.timeout_happened or self.player.allocation is None:
                self.player.allocation = random.randint(0, 100)
                self.participant.vars['alert_message'] = (
                    f"You did not make a choice, so {self.player.allocation} was chosen for you. "
                )
                self.player.random_decisions = True
            else:
                self.participant.vars['alert_message'] = None
                self.player.random_decisions = False



        elif current_part == 2:
            self.player.allocation = self.player.get_agent_decision_mandatory(display_round)
            self.participant.vars['alert_message'] = ""
            self.player.random_decisions = True

        elif current_part == 3 and self.player.delegate_decision_optional:
            self.player.allocation = self.player.get_agent_decision_optional(display_round)
            self.participant.vars['alert_message'] = ""
            self.player.random_decisions = True
        
        elif current_part == 3 and not self.player.delegate_decision_optional:
            if self.timeout_happened or self.player.allocation is None:
                self.player.allocation = random.randint(0, 100)
                self.participant.vars['alert_message'] = (
                    f"You did not make a choice, so {self.player.allocation} was chosen for you. "
                )
                self.player.random_decisions = True

            else:
                self.participant.vars['alert_message'] = ''
                self.player.random_decisions = False
            



        print(f"round:{self.round_number}  self.player.allocation: {self.player.allocation}")



class DelegationDecision(Page):
    form_model = 'player'
    form_fields = ['delegate_decision_optional']

    def is_displayed(self):

        return Constants.get_part(self.round_number) == 3 and (self.round_number - 1) % Constants.rounds_per_part == 0

    def before_next_page(self):
        if Constants.get_part(self.round_number) == 3:
            part_rounds = self.player.in_rounds(
                (Constants.get_part(self.round_number) - 1) * Constants.rounds_per_part + 1,
                Constants.get_part(self.round_number) * Constants.rounds_per_part
            )
            for p in part_rounds:
                p.delegate_decision_optional = self.player.delegate_decision_optional




class Results(Page):
    def is_displayed(self):
        return self.round_number % Constants.rounds_per_part == 0

    def vars_for_template(self):
        import json

        current_part = Constants.get_part(self.round_number)
        if current_part  == 2 or (current_part == 3 and self.player.delegate_decision_optional):
            is_delegation=False
        else: 
            is_delegation=  self.player.field_maybe_none('delegate_decision_optional')

        player  = self.player
        rounds_data = []

        for r in range(
                (current_part - 1) * Constants.rounds_per_part + 1,
                current_part     * Constants.rounds_per_part + 1
        ):
            rr         = player.in_round(r)
            allocation = rr.field_maybe_none('allocation') or 0
            rounds_data.append({
                'round'     : r - (current_part - 1) * Constants.rounds_per_part,
                'kept'      : 100 - allocation,
                'allocated' : allocation,
                'total'     : 100,
            })

        return dict(
            current_part = current_part,
            rounds_data  = rounds_data,
            is_delegation = is_delegation,
        )



class Debriefing(Page):
    form_model = 'player'
    form_fields = []
    def is_displayed(self):
        return  self.round_number == Constants.num_rounds


    def vars_for_template(self):
        import json
        import random

        results_by_part = {}
        totals_by_part= {}

        round_number=self.round_number
        random_payoff_part=random.randint(1,3)

        for part in range(1, 4):
            part_data = []
            for round_number in range(
                (part - 1) * Constants.rounds_per_part + 1,
                part * Constants.rounds_per_part + 1
            ):
                round_result = self.player.in_round(round_number)
                part_data.append({
                    "round": round_number,
                    "kept": 100 - (round_result.field_maybe_none('allocation') or 0),
                    "allocated": round_result.field_maybe_none('allocation')or 0,
                    "decision" : round_result.field_maybe_none('random_decisions'),
                })

            results_by_part[part] = part_data
            total_kept = sum(item["kept"] for item in part_data)
            total_allocated = sum(item["allocated"] for item in part_data)
            totals_by_part[part] = {
            "total_kept": total_kept,
        }


        agent_allocation_chosen = self.player.field_maybe_none('delegate_decision_optional')
        if self.player.field_maybe_none('random_payoff_part') == None: 
            random_payoff_part=self.random_payoff_selection()
            self.player.random_payoff_part=random_payoff_part
        else: 
            random_payoff_part=self.player.random_payoff_part

        

        payoff_data=results_by_part[self.player.random_payoff_part]
        total_kept,total_allocated=self.calculate_total_payoff(payoff_data)


        return {
            'results_by_part': results_by_part,
            'totals_by_part': totals_by_part,

            'totals_by_1': totals_by_part[1]['total_kept'],
            'totals_by_2': totals_by_part[2]['total_kept'],
            'totals_by_3': totals_by_part[3]['total_kept'],
            'agent_allocation_chosen': agent_allocation_chosen,
            'random_payoff_part': random_payoff_part,
            'total_kept' : total_kept,
            'payoff_cents' : (int(total_kept) + 5) // 10,
            'total_allocated' : total_allocated
               }
    

    def random_payoff_selection(self): 
        import random

        round_number=self.round_number
        random_payoff_part=random.randint(1,3)
        return random_payoff_part

    def calculate_total_payoff(self, part_data): 
        total_kept=0
        total_allocated=0
        for round in part_data: 
                total_kept=total_kept+round["kept"]
                total_allocated=total_allocated+round["allocated"]
        
        return total_kept,total_allocated


class ExitQuestionnaire(Page):
    form_model = 'player'
    form_fields = [
        'gender',
        'age',
        'occupation',
        'ai_use',
        'task_difficulty',
        'feedback',
    ]

    def is_displayed(self):
        return  self.round_number == Constants.num_rounds


class Thankyou(Page):


    def vars_for_template(self):
        prolific_url = 'https://bsky.app/profile/iterrucha.bsky.social'

        return dict(url=prolific_url)
    
    def is_displayed(self): 
        return self.round_number == Constants.num_rounds



page_sequence = [
    InformedConsent,
    Introduction,
    ComprehensionTest,
    FailedTest,
    Instructions,
    DelegationDecision,
    GoalOriented,
    Decision,
    Results,
    Debriefing,
    ExitQuestionnaire,
    Thankyou,
]