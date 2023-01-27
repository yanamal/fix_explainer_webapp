homework_1 = {
    'count_lte': {
        'solutions': [
            `def count_lte(target, nums):
    count = 0
    for num in nums:
        if num > 0 and num <= target:
            count += 1
    return count`
        ],
        'tests': [
            'count_lte(4, [-2, 2, 3]) == 2',
            'count_lte(2, [0, 1, -2, 2, 3]) == 2',
            'count_lte(3, [0, 1, -2, 2, 3]) == 3',
            'count_lte(2, [0, 1, -2, -3]) == 1',
            'count_lte(10, []) == 0'
        ]
    },
    'total_by_twos': {
        'solutions': [
            `def total_by_twos(end):
    total = 0
    for x in range(1, end+1, 2):
        total += x
    return total`
        ],
        'tests': [
            'total_by_twos(3) == 4',
            'total_by_twos(0) == 0',
            'total_by_twos(1) == 1',
            'total_by_twos(9) == 25',
            'total_by_twos(13) == 13'
        ]
    },
    'check_all_neg': {
        'solutions': [
            `def check_all_neg(num_list):
    for num in num_list:
        if num >= 0:
            return False
    return True`
        ],
        'tests': [
            'check_all_neg([-1, -2]) == True',
            'check_all_neg([5, -3]) == False',
            'check_all_neg([-1, -3, -5]) == True',
            'check_all_neg([-100, 30, 5]) == False',
            'check_all_neg([0, -3]) == False'
        ]
    }
}
