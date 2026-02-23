from extract import extract_all_fields
from fill_form import fill_form

FORM_URL = "https://forms.office.com/Pages/ResponsePage.aspx?id=YqoZ1Uzwqkq9InjY9PVpRY0iK7jNqbdKirfJcvEDPytUNUxNRE5DSlVXVzFINlJTRVFQN0ZGWE9VRC4u"

data = extract_all_fields("input.png")

print("Extracted Data:")
for k, v in data.items():
    print(f"{k}: {v}")

fill_form(FORM_URL, data)
