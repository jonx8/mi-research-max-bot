def get_fagerstrom_questions():
    """Возвращает вопросы теста Фагерстрёма"""
    return [
        {
            'number': 1,
            'question': 'Как скоро после утреннего пробуждения Вы выкуриваете первую сигарету?',
            'options': [
                'В течение первых 5 мин',
                'В течение первых 6-30 мин', 
                'В течение первых 30-60 мин',
                'Через час'
            ],
            'scores': [3, 2, 1, 0],
            'field': 'fagerstrom_1'
        },
        {
            'number': 2,
            'question': 'Трудно ли Вам воздерживаться от курения в местах, где оно запрещено?',
            'options': ['Да', 'Нет'],
            'scores': [1, 0],
            'field': 'fagerstrom_2'
        },
        {
            'number': 3,
            'question': 'От какой сигареты Вам труднее всего отказаться?',
            'options': [
                'Первая сигарета утром',
                'Любая другая'
            ],
            'scores': [1, 0],
            'field': 'fagerstrom_3'
        },
        {
            'number': 4,
            'question': 'Сколько сигарет Вы выкуриваете в день?',
            'options': [
                '10 и меньше',
                '11-20',
                '21-30', 
                '31 и более'
            ],
            'scores': [0, 1, 2, 3],
            'field': 'fagerstrom_4'
        },
        {
            'number': 5,
            'question': 'Вы курите чаще в первые часы утром, после того как проснетесь, или в течение остального дня?',
            'options': ['Курю чаще в первые часы утром', 'Курю чаще в течение дня'],
            'scores': [1, 0],
            'field': 'fagerstrom_5'
        },
        {
            'number': 6,
            'question': 'Курите ли Вы, если сильно больны и вынуждены находиться в кровати целый день?',
            'options': ['Да', 'Нет'],
            'scores': [1, 0],
            'field': 'fagerstrom_6'
        }
    ]

def calculate_fagerstrom_score(answers):
    """Рассчитывает общий балл по тесту Фагерстрёма"""
    total_score = sum(answers.values())
    
    if total_score <= 2:
        level = "Очень слабая зависимость"
    elif total_score <= 4:
        level = "Слабая зависимость" 
    elif total_score == 5:
        level = "Средняя зависимость"
    elif total_score <= 7:
        level = "Высокая зависимость"
    else:
        level = "Очень высокая зависимость"
    
    return total_score, level

def get_prochaska_questions():
    """Возвращает вопросы опросника Прохаски"""
    return [
        {
            'number': 1,
            'question': 'Бросили бы Вы употреблять табак/никотин, если бы это было легко?',
            'options': [
                'Определенно нет',
                'Вероятнее всего нет',
                'Возможно да',
                'Вероятнее всего да', 
                'Определенно да'
            ],
            'scores': [0, 1, 2, 3, 4],
            'field': 'prochaska_1'
        },
        {
            'number': 2, 
            'question': 'Как сильно Вы хотите бросить употреблять табак/никотин?',
            'options': [
                'Не хочу вообще',
                'Слабое желание',
                'В средней степени',
                'Сильное желание',
                'Очень хочу бросить курить'
            ],
            'scores': [0, 1, 2, 3, 4],
            'field': 'prochaska_2'
        }
    ]

def calculate_prochaska_score(answers):
    """Рассчитывает общий балл по опроснику Прохаски"""
    total_score = sum(answers.values())
    
    if total_score >= 6:
        level = "Высокая мотивация"
    elif total_score >= 3:
        level = "Слабая мотивация" 
    else:
        level = "Отсутствие мотивации"
    
    return total_score, level