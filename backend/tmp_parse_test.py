from services.parser import parse_amount

tests = [
    'Receive 5000 today',
    'Paid 5000 today',
    'Received 5000 from client',
    'Pay 5000 rent',
    'I receive salary 50000',
    'I paid 5000 for groceries',
]

for t in tests:
    print(t, '->', parse_amount(t))
