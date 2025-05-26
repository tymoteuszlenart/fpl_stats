import json
import re
import unicodedata

def sanitize_web_name(input_str):
    # Replace special characters with their ASCII equivalents
    replacements = {
        'Ø': 'O', 'ø': 'o', 'Å': 'A', 'å': 'a', 'Æ': 'Ae', 'æ': 'ae', 'ß': 'ss', 'Ç': 'C', 'ç': 'c',
        'Ñ': 'N', 'ñ': 'n', 'Ü': 'U', 'ü': 'u', 'Ö': 'O', 'ö': 'o', 'É': 'E', 'é': 'e', 'È': 'E', 'è': 'e',
        'Á': 'A', 'á': 'a', 'Í': 'I', 'í': 'i', 'Ó': 'O', 'ó': 'o', 'Ú': 'U', 'ú': 'u', 'Ý': 'Y', 'ý': 'y',
        'Ž': 'Z', 'ž': 'z', 'Š': 'S', 'š': 's', 'Č': 'C', 'č': 'c', 'Ł': 'L', 'ł': 'l', 'Đ': 'D', 'đ': 'd',
        'Ć': 'C', 'ć': 'c', 'Ę': 'E', 'ę': 'e', 'Ą': 'A', 'ą': 'a', 'Ś': 'S', 'ś': 's', 'Ź': 'Z', 'ź': 'z',
        'Ż': 'Z', 'ż': 'z', 'Ń': 'N', 'ń': 'n', 'Ů': 'U', 'ů': 'u', 'Ř': 'R', 'ř': 'r', 'Ť': 'T', 'ť': 't',
        'Ň': 'N', 'ň': 'n', 'Ě': 'E', 'ě': 'e', 'Ĺ': 'L', 'ĺ': 'l', 'Ľ': 'L', 'ľ': 'l', 'Ď': 'D', 'ď': 'd',
        'Ť': 'T', 'ť': 't', 'Ň': 'N', 'ň': 'n', 'Ŕ': 'R', 'ŕ': 'r', 'Ÿ': 'Y', 'ÿ': 'y', 'Õ': 'O', 'õ': 'o',
        'Ã': 'A', 'ã': 'a', 'Œ': 'Oe', 'œ': 'oe', 'ğ': 'g', 'ı': 'i'
    }
    for src, target in replacements.items():
        input_str = input_str.replace(src, target)
    # Remove diacritics and combining marks
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Replace spaces and multiple characters with a single space
    return re.sub(r'[^A-Za-z0-9. ]+', '', only_ascii)

# Open the JSON file and process data
with open('json/player_id_map.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

ids = []
try:
    for i in data['elements']:
        name = sanitize_web_name(i['web_name'])
        ids.append({"id":i['id'], "name":name})
except Exception as e:
    print(f"Exception: {e} - Sprawdź strukturę pliku JSON.")

print(ids[0:10])  # Print first 10 elements to check output

# Save processed data to a new JSON file
with open("json/player_id_mapped.json", "w", encoding='utf-8') as f:
    json.dump(ids, f, ensure_ascii=False, indent=2)