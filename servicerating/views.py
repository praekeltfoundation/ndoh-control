import math

from django.shortcuts import render

from servicerating.models import Response

def empty_response_map():
    response_map = {
        'question_1_friendliness':
            {
                'very-satisfied': 0,
                'satisfied': 0,
                'not-satisfied': 0,
                'very-unsatisfied': 0 
            },
        'question_2_waiting_times_feel':
            {
                'very-satisfied': 0,
                'satisfied': 0,
                'not-satisfied': 0,
                'very-unsatisfied': 0
            },
        'question_3_waiting_times_length':
            {
                'less-than-an-hour': 0,
                'between-1-and-3-hours': 0,
                'more-than-4-hours': 0,
                'all-day': 0
            },
        'question_4_cleanliness':
            {
                'very-satisfied': 0,
                'satisfied': 0,
                'not-satisfied': 0,
                'very-unsatisfied': 0
            },
        'question_5_privacy':
            {
                'very-satisfied': 0,
                'satisfied': 0,
                'not-satisfied': 0,
                'very-unsatisfied': 0
            }
    }
    return response_map


# Create your views here.
def dashboard(request):
    averages = {}

    all_responses = Response.objects.all()
    num_questions = 5.0
    total_responses = 0

    response_map = empty_response_map();

    for response in all_responses:
        total_responses += 1
        response_map[response.key][response.value] += 1

    num_ratings = math.ceil(total_responses / num_questions)

    averages_questions = [
        'question_1_friendliness',
        'question_2_waiting_times_feel',
        'question_4_cleanliness',
        'question_5_privacy'
    ]

    waiting_times = {
        'less_than_an_hour': round(
            (response_map['question_3_waiting_times_length']['less-than-an-hour'] / num_ratings * 100), 1),
        'between_1_and_3_hours': round((response_map['question_3_waiting_times_length']['between-1-and-3-hours'] / num_ratings * 100), 1),
        'more_than_4_hours': round((response_map['question_3_waiting_times_length']['more-than-4-hours'] / num_ratings * 100), 1),
        'all_day': round((response_map['question_3_waiting_times_length']['all-day'] / num_ratings * 100), 1)
    }
    
    for question in averages_questions:
        averages[question] = round((
            (response_map[question]['very-satisfied'] * 4) +
            (response_map[question]['satisfied'] * 3) +
            (response_map[question]['not-satisfied'] * 2) +
            (response_map[question]['very-unsatisfied'] * 1)
            ) / num_ratings, 1)

    context = {
        'averages': averages,
        'waiting_times': waiting_times
    }

    return render(request, 'admin/servicerating/dashboard.html', context)
