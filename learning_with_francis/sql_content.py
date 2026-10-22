"""Reviewed beginner SQL content. Answer keys stay on the Python server."""

TOPIC_ID = "sql-select-basics"
CONTENT_VERSION = "sql-select-where-v1"
PRACTICE_VERSION = "sql-select-where-practice-v2"

PRACTICE = (
    {"id": "practice1", "prompt": "Which query shows only the names of learners whose city is Berlin?",
     "choices": {"a": "SELECT name FROM learners WHERE city = 'Berlin';",
                 "b": "SELECT city FROM learners;",
                 "c": "SELECT name FROM learners;"},
     "correct": "a", "explanation": "SELECT name chooses the name column. WHERE city = 'Berlin' keeps only rows for Berlin."},
    {"id": "practice2", "prompt": "Which query shows every column from the learners table?",
     "choices": {"a": "SELECT name FROM learners;", "b": "SELECT * FROM learners;",
                 "c": "SELECT city FROM learners;"},
     "correct": "b", "explanation": "The star (*) after SELECT means every column. Here that means name, city and age."},
    {"id": "practice3", "prompt": "Which query displays only the age column?",
     "choices": {"a": "SELECT * FROM learners;", "b": "SELECT name FROM learners;",
                 "c": "SELECT age FROM learners;"},
     "correct": "c", "explanation": "Put the column you want after SELECT. SELECT age reads only the age column."},
    {"id": "practice4", "prompt": "How do you display the name and age columns together?",
     "choices": {"a": "SELECT name age FROM learners;", "b": "SELECT name, age FROM learners;",
                 "c": "SELECT name FROM learners;"},
     "correct": "b", "explanation": "A comma separates column names. SELECT name, age displays both columns."},
    {"id": "practice5", "prompt": "In SELECT name FROM learners;, what does FROM learners tell SQL?",
     "choices": {"a": "Read rows from the learners table", "b": "Display a column called learners",
                 "c": "Keep only learners called name"},
     "correct": "a", "explanation": "FROM identifies the table to read. SELECT identifies the columns to display."},
    {"id": "practice6", "prompt": "Which name matches SELECT name FROM learners WHERE age < 18;?",
     "choices": {"a": "Alex", "b": "Sam", "c": "Mia"},
     "correct": "c", "explanation": "Mia is 16, so she matches age < 18. Alex is 22 and Sam is 19."},
    {"id": "practice7", "prompt": "Which learners match WHERE age >= 18?",
     "choices": {"a": "Alex and Sam", "b": "Only Mia", "c": "All three learners"},
     "correct": "a", "explanation": "Greater than or equal to 18 includes Alex (22) and Sam (19). Mia (16) does not match."},
    {"id": "practice8", "prompt": "Which condition keeps only learners whose city is Hamburg?",
     "choices": {"a": "WHERE age = 18", "b": "WHERE city = 'Hamburg'", "c": "WHERE city = 'Berlin'"},
     "correct": "b", "explanation": "Compare the city column with the text 'Hamburg'. Single quotes identify the text value."},
    {"id": "practice9", "prompt": "Which name matches SELECT name FROM learners WHERE age = 19;?",
     "choices": {"a": "Mia", "b": "Alex", "c": "Sam"},
     "correct": "c", "explanation": "The equals sign keeps an exact match. Sam is 19, so only Sam's row is returned."},
    {"id": "practice10", "prompt": "Which name matches SELECT name FROM learners WHERE age > 20;?",
     "choices": {"a": "Mia", "b": "Alex", "c": "Sam"},
     "correct": "b", "explanation": "The > symbol means greater than. Alex is 22, so he is the only learner older than 20."},
)

QUIZ = (
    {"id": "q1", "prompt": "What does SELECT choose in a query?",
     "choices": {"a": "The table's name", "b": "The columns to display", "c": "The rows to delete"},
     "correct": "b", "explanation": "The column names after SELECT decide which columns appear in the result."},
    {"id": "q2", "prompt": "Which query displays the name and city columns for every learner?",
     "choices": {"a": "SELECT name AND city FROM learners;", "b": "SELECT learners FROM name, city;",
                 "c": "SELECT name, city FROM learners;"},
     "correct": "c", "explanation": "Separate selected column names with a comma. FROM names the table: learners."},
    {"id": "q3", "prompt": "Which query displays learners aged 18 or older?",
     "choices": {"a": "SELECT * FROM learners WHERE age >= 18;", "b": "SELECT * FROM learners WHERE age < 18;",
                 "c": "SELECT * FROM learners;"},
     "correct": "a", "explanation": "WHERE age >= 18 keeps rows where age is greater than or equal to 18. The star selects every column."},
    {"id": "q4", "prompt": "Which WHERE condition correctly matches the text value Berlin?",
     "choices": {"a": "WHERE city > 18", "b": "WHERE city = 'Berlin'", "c": "WHERE city = Berlin"},
     "correct": "b", "explanation": "Text values use single quotes. The equals sign compares the city column with the text 'Berlin'."},
    {"id": "q5", "prompt": "Using the lesson's learners table, which name is returned by SELECT name FROM learners WHERE age < 18;?",
     "choices": {"a": "Alex", "b": "Sam", "c": "Mia"},
     "correct": "c", "explanation": "Mia is 16, so her row matches age < 18. Alex (22) and Sam (19) do not match."},
)


def questions_for(kind):
    if kind == "practice":
        return PRACTICE
    if kind == "quiz":
        return QUIZ
    raise ValueError("Unknown activity.")


def public_questions(kind, questions=None):
    """Never include keys or explanations in an unanswered form."""
    source = questions_for(kind) if questions is None else questions
    return [{"id": q["id"], "prompt": q["prompt"], "choices": q["choices"]} for q in source]


def quiz_feedback(score, name):
    if score <= 2:
        return f"Keep practicing, {name}! Review the lesson and try again. You can do it!"
    if score <= 4:
        return f"Well done, {name}! You passed the quiz. Keep practicing to improve your score!"
    return f"Congratulations, {name}! Perfect score! You answered all five questions correctly!"
