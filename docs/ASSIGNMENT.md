
MCP, Skills ו־Agent Harness
מה צריך לעשות
משימה: סוכן אחד, שני harnesses

המטרה

תחשבי על סוכן משלך, שבאמת היה עוזר לך, ותבני אותו פעמיים:

API/: על ה-Messages API הגולמי. את כל ה-harness את כותבת בעצמך.

SDK/: על Claude Agent SDK. Claude Code מריץ את ה-harness, ואת רק מגדירה אותו.

בסוף תמדדי את שתי הגרסאות ותסבירי מה ה-SDK חסך לך ומה הוא עלה לך.

1. בחרי סוכן
אפשר כל תחום. כמה רעיונות: מתכנן לימודים, רשימת קריאה, מעקב חיפוש עבודה, תקציב אישי, מאמן כושר, ארגון מתכונים וקניות.

הסוכן חייב לכלול:

Tools: לפחות 3 כלים משלך, ואחד מהם חיצוני (אינטרנט, API או קבצים).

Memory: משהו שהוא זוכר בין סשנים, כמו החלטות, העדפות או היסטוריה.

Context engineering: הוא לא מקבל את כל המידע בכל תור, אלא רק את מה שרלוונטי.

Token optimization: פלט כלים קומפקטי, ומדידה של כמה כל תור עולה.

2. מה בונים בכל גרסה
API/: את כותבת	SDK/: את מגדירה
לולאת הסוכן	loop.py: הלולאה רצה כל עוד stop_reason == "tool_use". כל ה-tool_result חוזרים בהודעה אחת	client.query() + receive_response()
כלים	tools.py: סכמות JSON, dispatch, ושגיאות שחוזרות ל-model כ-is_error	@tool + create_sdk_mcp_server, וכלים מובנים
שיחה	history.py: נשמרת לדיסק, append-only	resume=session_id
זיכרון	memory.py: איפה נשמר הזיכרון ואיך שולפים ממנו	למשל CLAUDE.md עם setting_sources=["project"]
קונטקסט	context.py: מה נכנס לכל תור	מה Claude Code מוסיף לבד, ומה המודל שולף בכלים
חלון קונטקסט	compaction.py: מסכמים את כל השיחה מעבר לסף	אוטומטי
caching	caching.py: נקודות cache_control	אוטומטי
טוקנים	tokens.py: שימוש ועלות לכל תור	ResultMessage.usage ו-total_cost_usd
חובה:

ב-API, קובץ אחד לכל אחריות בתוך API/harness/, וכל פעולה בזמן ריצה מודפסת עם שם הקובץ שביצע אותה.

ב-SDK, כל שורה שמחליפה קובץ כזה מסומנת # replaces: <שם>.

בהגדרות ה-SDK: system prompt משלך, רשימת כלים מצומצמת, ו-strict_mcp_config=True.

קוד הדומיין (הכלים והנתונים) נמצא ב-shared/, ושתי הגרסאות משתמשות בו.

3. מבנה
<agent-name>-<השם-שלך>/
  shared/        כלים ונתונים משותפים
  API/           main.py  agent.py  harness/{loop,tools,history,memory,context,compaction,caching,tokens}.py
  SDK/           main.py  agent.py  tools.py
  tests/         בדיקות offline עם client מדומה, בלי מפתח
  scenario.json  התרחיש שלך
  results/       api.json  sdk.json
  REPORT.md
4. תרחיש ומדידה
תכתבי scenario.json עם 6 עד 8 פניות בשני סשנים. סשן 2 רץ על מופע חדש של הסוכן שטוען את המצב מהדיסק. התרחיש חייב לכלול:

שימוש בכלים.

שמירה לזיכרון.

שליפה מהזיכרון בסשן 2.

שימוש בכלי החיצוני.

בקשה שסותרת משהו שנשמר.

תגדירי לפחות 5 בדיקות pass/fail, ורובן על המצב שנשמר, לא רק על טקסט התשובה.

python API/main.py --scenario scenario.json --out results/api.json
python SDK/main.py --scenario scenario.json --out results/sdk.json
בקובץ התוצאות, לכל תור: הטוקנים (input, cache read, cache write, output), מספר הקריאות למודל, הכלים שהופעלו, העלות והזמן. בנוסף: תוצאות הבדיקות, וספירת שורות הקוד לכל חלק ב-harness.

כללי השוואה:

אותו מודל ואותו effort בשתי הגרסאות (מומלץ claude-opus-5-5 עם medium).

גרסאות ספריות נעולות.

כל ריצה מתחילה ממצב נקי.

5. דוח (REPORT.md)
טבלה: API מול SDK, עם טוקנים, אחוז cache, קריאות למודל, עלות ובדיקות שעברו.

שורות קוד לכל חלק ב-harness, API מול SDK.

איפה ה-SDK עלה יותר טוקנים ואיפה פחות, ולמה?

על מה הייתה לך שליטה ב-API ואיבדת ב-SDK?

איזו גרסה היית בוחרת לסוכן הזה, ולמה?

6. הרשאות
SDK: רץ על ה-login שלך ב-Claude Code, לשימוש אישי. ANTHROPIC_API_KEY לא צריך להיות מוגדר, אחרת החיוב עובר למפתח.

API: צריך מפתח מ-Claude Console. מגדירים אותו רק כמשתנה סביבה בטרמינל, לעולם לא בקוד ולא ב-git.

ציון

רכיב	נקודות
רעיון הסוכן ו-4 הנושאים	15
API harness	30
SDK	15
בדיקות offline	10
תרחיש, מדידה ובדיקות	15
דוח