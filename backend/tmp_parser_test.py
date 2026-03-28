from services.parser import parse_text_input

cases = [
    'i say receive 5000',
    'i say paid 5000',
    'receive 5000',
    'paid 5000',
    'i say receive it goes as outflow',
    'i say paid it goes as outflow',
    'i said receive 5000 from client',
    'i meant to say paid 5000 for groceries',
    'i did not receive 5000',
    'i did not pay 5000',
]

for c in cases:
    p = parse_text_input(c)
    print(f"{c} -> type={p['type']}, amount={p['amount']}, desc='{p['description']}'")
