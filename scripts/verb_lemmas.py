# Hand-written Hebrew verb -> FDOSH lemma map.
# FDOSH cites verbs in 3rd-person masculine past; the app stores infinitives and
# present-tense forms. Automatic mapping is unsafe here: it conflates nouns with
# verbs (ספר "book" vs סיפר "told", דעת "knowledge" vs ידע "knew") and mis-handles
# irregular roots (פ"י, פ"נ, ל"ה), which can throw a core verb five levels too deep.
# Every entry below is set by hand. Infinitive and present forms share one lemma,
# which is correct: they are the same word.

VERB_LEMMA = {
 # ── irregulars the heuristic gets wrong ──
 "לדעת":"ידע", "יודע":"ידע", "יודעת":"ידע",
 "ללכת":"הלך", "הולך":"הלך", "הולכת":"הלך",
 "לתת":"נתן", "נותן":"נתן", "נותנת":"נתן",
 "לקחת":"לקח", "לוקח":"לקח", "לוקחת":"לקח",
 "לצאת":"יצא", "לרדת":"ירד", "ליפול":"נפל",
 "לשבת":"ישב", "יושב":"ישב", "יושבת":"ישב",
 "לישון":"ישן", "ישן":"ישן", "ישנה":"ישן",
 # ── noun/verb collisions ──
 "לספר":"סיפר", "לסדר":"סידר", "מסדר":"סידר",
 "לשיר":"שר", "לשחות":"שחה", "לשנות":"שינה",
 "לומד":"למד", "לומדת":"למד", "ללמוד":"למד", "ללמד":"לימד",
 "אוכל":"אכל", "אוכלת":"אכל", "לאכול":"אכל",
 # ── pi'el / hif'il present forms ──
 "לשחק":"שיחק", "לקוות":"קיווה", "מקווה":"קיווה",
 "מנסה":"ניסה", "לנסות":"ניסה",
 "מחפש":"חיפש", "מחפשת":"חיפש", "לחפש":"חיפש",
 "מצלם":"צילם", "מבשל":"בישל", "לבשל":"בישל", "מנקה":"ניקה",
 "מדבר":"דיבר", "מדברת":"דיבר", "לדבר":"דיבר",
 "מביא":"הביא", "מביאה":"הביא",
 "מרגיש":"הרגיש", "מרגישה":"הרגיש",
 "מבין":"הבין", "מבינה":"הבין",
 # ── regular present forms -> past lemma ──
 "רוצה":"רצה", "צריך":"צריך", "צריכה":"צריך",
 "יכול":"יכול", "יכולה":"יכול",
 "אוהב":"אהב", "אוהבת":"אהב",
 "חושב":"חשב", "חושבת":"חשב",
 "אומר":"אמר", "אומרת":"אמר",
 "בא":"בא", "באה":"בא",
 "עושה":"עשה", "רואה":"ראה",
 "שומע":"שמע", "שומעת":"שמע",
 "שותה":"שתה",
 "גר":"גר", "גרה":"גר",
 "עובד":"עבד", "עובדת":"עבד",
 "כותב":"כתב", "כותבת":"כתב",
 "קורא":"קרא", "קוראת":"קרא",
 "עומד":"עמד", "עומדת":"עמד",
 "קם":"קם", "קמה":"קם",
 "נוסע":"נסע", "נוסעת":"נסע",
 "חוזר":"חזר", "חוזרת":"חזר",
 "זוכר":"זכר", "זוכרת":"זכר",
 "שוכח":"שכח", "שוכחת":"שכח",
}

# Infinitives whose automatic match was verified correct are handled by the
# fallback heuristic in build_frequency.py; these are the ones it gets wrong.
