<div dir=rtl>
# הקשר לפרויקט

## מי אני
מפתחת Full-Stack ג'וניור. מכירה Python, אבל לא עבדתי בעבר עם tool use,
agent loops, caching או compaction, ולכן אני צריכה הסברים תוך כדי עבודה.
מעדיפה המלצות החלטיות על פני רשימת אפשרויות. שפת עבודה: עברית.

## המטלה בקצרה
סוכן אחד שבנוי פעמיים:
- API/: על Messages API הגולמי, כשאני כותבת את כל ה-harness בעצמי.
- SDK/: על Claude Agent SDK, כשאני רק מגדירה.
אחר כך מדידה על אותו scenario, ודוח השוואה. הפירוט המלא ב-docs/ASSIGNMENT.md.
API harness שווה 30 נקודות, ולכן שם עיקר ההשקעה.

## החלטות שכבר התקבלו
- הסוכן: מעקב חיפוש עבודה (job tracker).
- הכלים, ב-shared/jobs.py, עם נתונים ב-data/jobs.json:
  - add_application(company, role, url)
  - update_status(company, status)
  - search_applications(status=None), שמחזירה מחרוזת קצרה ולא JSON ענק
  - fetch_job_posting(url), הכלי החיצוני (אינטרנט)
- זיכרון בין סשנים: העדפות, למשל remote_only, וסטטוסים של מועמדויות.
- סתירה לתרחיש: בסשן 1 "רק עבודה היברידית", ובסשן 2 "בעצם גם משרד מלא זה בסדר".
- מודל: claude-opus-5-5 עם effort medium, זהה בשתי הגרסאות.
- המפתח מוגדר רק כמשתנה סביבה. בטרמינל של ה-SDK אסור ש-ANTHROPIC_API_KEY יהיה מוגדר.
- הוראות הפיתוח נמצאות ב-docs/ ולא ב-CLAUDE.md, כדי לא לזהם את הזיכרון של סוכן ה-SDK.

## סדר עבודה
0. סביבה: venv, pip install anthropic, pip freeze > requirements.txt (גרסאות נעולות).
1. shared/: הכלים כפונקציות Python רגילות, בלי AI. לבדוק ידנית שהן עובדות.
2. API/scratch.py: לולאה מינימלית בקובץ אחד. כל עוד stop_reason == "tool_use",
   מריצים את הכלים ומחזירים את כל ה-tool_result בהודעת user אחת.
3. פירוק ל-API/harness/{loop,tools,history,memory,context,compaction,caching,tokens}.py.
   כל פעולה בזמן ריצה מודפסת עם שם הקובץ, למשל [loop.py] ...
4. tests/: בדיקות offline עם client מדומה, בלי מפתח.
5. SDK/: אותם כלים מ-shared/, כל שורה מסומנת "# replaces: <שם>",
   strict_mcp_config=True, ורשימת כלים מצומצמת.
6. scenario.json (6–8 פניות, 2 סשנים), לפחות 5 בדיקות pass/fail
   שרובן בודקות מצב בדיסק, הרצה של שתי הגרסאות, ו-REPORT.md.

## איפה אני עכשיו
שלבים 0–5 הושלמו (API ו-SDK רצו מול המודל האמיתי).
tests/: 34 בדיקות offline (python -m pytest tests), FakeClient ב-conftest.py, תיקיית נתונים זמנית לכל בדיקה.
שלב 6: scenario.json (7 פניות, 2 סשנים, 6 בדיקות) ו-shared/scenario.py (runner משותף) כתובים ונבדקו offline.
שתי הגרסאות רצו על התרחיש (6/6 בשתיהן), ו-REPORT.md כתוב.
- ב-SDK, total_cost_usd מצטבר לאורך הסשן. תוקן ב-SDK/agent.py (הפרש לכל תור), ו-results/sdk.json תוקן בדיעבד (שדה note).
- Claude Code משתמש ב-cache TTL של שעה ($8 למיליון), וה-API ב-5 דקות ($5 למיליון).
- בוצע: ההעדפות עברו מה-system prompt לבלוק <memory> בהודעת ה-user הראשונה של כל סשן. ה-system עכשיו סטטי וזהה בכל הסשנים.
  שתי הגרסאות הורצו שוב אחרי השינוי (6/6 בשתיהן), ו-REPORT.md עודכן לפי ההרצה הזו.
- הריפו: https://github.com/meanochi/meanochi-job-tracker-michal

החלטות שלב 6:
- runner אחד משותף (shared/scenario.py) לשתי הגרסאות: מוחק את runs/<version>/ בהתחלה (מצב נקי),
  מריץ כל סשן על מופע Agent חדש, מריץ את הבדיקות, סופר שורות קוד וכותב את קובץ התוצאות.
- 5 מתוך 6 בדיקות הן על מצב (jobs.json, preferences.json, הכלים שהופעלו); אחת על טקסט התשובה (שליפה מזיכרון בסשן 2).
- שורות קוד: ב-API שורות קוד בכל קובץ harness בלי הערות ו-docstrings; ב-SDK שורות עם "# replaces: <file>".

החלטות שלב 5:
- זיכרון ב-SDK: save_preference (אותו כלי מ-shared) כותב preferences.json; בתחילת סשן agent.py מרנדר אותו
  ל-data/CLAUDE.md, ו-setting_sources=["project"] + cwd=data/ גורמים ל-Claude Code לטעון אותו. כך בדיקות הדיסק זהות בשתי הגרסאות.
- tools=[] (בלי כלים מובנים), allowed_tools = 5 כלי ה-MCP, strict_mcp_config=True, system_prompt משלנו.
- אין ב-SDK קונטקסט לכל תור (<context>): המודל שולף סטטוסים בעצמו עם search_applications. זו נקודת השוואה לדוח.

החלטות שלב 3:
- נתונים בתיקייה (JOB_TRACKER_DIR, ברירת מחדל data/): jobs.json, preferences.json, sessions/<id>.jsonl.
- כלי חמישי: save_preference ב-shared/preferences.py (מפתח אחד לכל נושא, ערך חדש דורס את הישן, וכך נפתרת הסתירה).
- Opus 5.5 בודק שההיסטוריה לא נערכה ("preserved thinking"). לכן: היסטוריה append-only,
  ה-system prompt קפוא לכל סשן (נשמר כשורה ראשונה ב-jsonl), קונטקסט לכל תור מצורף להודעת ה-user,
  ו-compaction "פשוט" (סיכום של כל השיחה, בלי זנב).
- caching: 2 נקודות cache_control (סוף ה-system, סוף ההודעה האחרונה), רק על עותקים.
- מחירים ב-tokens.py: $4 input, $20 output, $5 cache write (5 דק'), $0.20 cache read, למיליון טוקנים.
- requirements.txt נעול ב-UTF-8 (כולל claude-agent-sdk ו-pytest).
- shared/jobs.py: ארבעת הכלים, שגיאות כ-ToolError, תיקיית הנתונים מ-JOB_TRACKER_DIR (ברירת מחדל data/).
- כל main שמדבר עם ה-API חייב לקרוא ל-truststore.inject_into_ssl() בהתחלה (NetFree), אחרת APIConnectionError.
- fetch_job_posting משתמש ב-truststore בגלל ה-CA של NetFree; אתרים חסומים ב-NetFree חוזרים כ-ToolError.