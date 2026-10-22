"""Small subject catalogue; SQL keeps its reviewed content unchanged."""

from dataclasses import dataclass

from . import sql_content


def question(identifier, prompt, choices, correct, explanation):
    return {"id": identifier, "prompt": prompt, "choices": dict(zip(("a", "b", "c"), choices)),
            "correct": correct, "explanation": explanation}


@dataclass(frozen=True)
class SubjectContent:
    TOPIC_ID: str
    CONTENT_VERSION: str
    PRACTICE_VERSION: str
    PRACTICE: tuple
    QUIZ: tuple

    def questions_for(self, kind):
        if kind == "practice":
            return self.PRACTICE
        if kind == "quiz":
            return self.QUIZ
        raise ValueError("Unknown activity.")

    def public_questions(self, kind, questions=None):
        source = self.questions_for(kind) if questions is None else questions
        return [{"id": q["id"], "prompt": q["prompt"], "choices": q["choices"]} for q in source]

    quiz_feedback = staticmethod(sql_content.quiz_feedback)


def questions(prefix, rows):
    return tuple(question(f"{prefix}{index}", *row) for index, row in enumerate(rows, 1))


PYTHON = SubjectContent("python-basics", "python-basics-quiz-v1", "python-basics-practice-v1",
    questions("practice", (
        ("What does age = 20 do?", ("Stores 20 under the name age", "Prints 20", "Defines a function"), "a", "The equals sign assigns a value to a variable name."),
        ("Which value is a string?", ("20", "'Hello'", "False"), "b", "Quotes mark text. 'Hello' is a string; 20 is an integer and False is a boolean."),
        ("What is count after count = 2 followed by count = count + 3?", ("2", "3", "5"), "c", "Read the old value 2, add 3, then store 5 in count."),
        ("Which keyword defines a Python function?", ("let", "def", "SELECT"), "b", "Use def, a function name, parentheses and a colon to define a function."),
        ("Which line calls a function named greet?", ("greet()", "def greet", "greet = 'Hi'"), "a", "Parentheses call a function. A definition alone does not run its body."),
        ("In def add_one(number):, what is number?", ("The result", "A table", "An input parameter"), "c", "A parameter is a name for a value supplied when a function is called."),
        ("What does return do inside a function?", ("Sends a value back to the caller", "Always prints text", "Starts a browser"), "a", "return ends the function call and supplies its result to the caller."),
        ("If add_one returns number + 1, what is add_one(4)?", ("4", "5", "1"), "b", "The argument 4 becomes number, so number + 1 gives 5."),
        ("What marks a function's body in Python?", ("Quotation marks", "A semicolon only", "Indentation"), "c", "Indented statements belong to the function. Use consistent indentation, normally four spaces."),
        ("Why store result = add_one(4)?", ("It deletes the function", "It lets you reuse the returned value", "It prints automatically"), "b", "The return value 5 is assigned to result. You can use it later or print it."),
    )),
    questions("q", (
        ("What value is stored by name = 'Mia'?", ("The number 3", "The text Mia", "A boolean"), "b", "Quoted text is a string. The variable name refers to that text."),
        ("What is points after points = 3; points = points + 2?", ("2", "3", "5"), "c", "The second assignment adds 2 to the previous value 3."),
        ("Which definition returns its input plus one?", ("def add_one(value):\n    return value + 1", "add_one = 1", "def add_one(value):\n    return 1"), "a", "The first function uses its parameter value and returns value + 1."),
        ("How do you call add_one with the number 6?", ("def add_one(6)", "add_one(6)", "add_one = 6"), "b", "Put the supplied value inside parentheses after the function name."),
        ("How does return differ from print()?", ("Both always save to SQLite", "return displays a webpage", "return supplies a result; print displays output"), "c", "A caller can store and reuse a returned value. print writes output instead."),
    )))

JAVASCRIPT = SubjectContent("javascript-basics", "javascript-basics-quiz-v1", "javascript-basics-practice-v1",
    questions("practice", (
        ("Which value is a JavaScript string?", ("'Hello'", "10", "false"), "a", "Quoted text is a string. Numbers and booleans are different value types."),
        ("Which declaration allows later reassignment?", ("const count = 0;", "let count = 0;", "def count = 0;"), "b", "Use let for a variable whose value will be reassigned."),
        ("What does const prevent?", ("All clicks", "Reading the variable", "Reassigning that variable binding"), "c", "A const binding cannot be reassigned. It does not freeze an object's properties."),
        ("What does document.querySelector('#message') select?", ("Every button", "The first element with id message", "A database row"), "b", "The # selector matches an HTML id. querySelector returns the first match."),
        ("What is returned if querySelector finds no match?", ("null", "An empty paragraph", "The number 1"), "a", "A missing match returns null. Check it before accessing element properties."),
        ("Which property changes an element's plain text?", ("valueType", "SELECT", "textContent"), "c", "Assign a string to textContent to replace an element's text."),
        ("Which event name represents a button press with a mouse?", ("click", "sql", "return"), "a", "A click listener runs when a click event occurs, including keyboard activation of a button."),
        ("Which method registers an event handler?", ("queryAnswer()", "addEventListener()", "saveDatabase()"), "b", "addEventListener connects an event name to a function that will handle it."),
        ("When does the function passed to a click listener normally run?", ("When the variable is declared", "Before the page exists", "When the click event occurs"), "c", "Registering the handler waits for future events. It does not call the handler immediately."),
        ("Why place a simple DOM script after the HTML it uses?", ("To create a login", "So the elements exist before selection", "To turn text into SQL"), "b", "The browser parses those elements first, so querySelector can find them."),
    )),
    questions("q", (
        ("Which value is a boolean?", ("'true'", "true", "42"), "b", "Unquoted true is a boolean. 'true' is text."),
        ("What can follow let score = 1; to change score to 2?", ("def score(2)", "score == 2;", "score = 2;"), "c", "The equals sign assigns the new value. let allows reassignment."),
        ("How do you select the element with id greeting?", ("document.querySelector('#greeting')", "document.querySelector('greeting-id')", "SELECT greeting FROM page"), "a", "The # character identifies an id in a CSS selector."),
        ("Which statement replaces a selected element's text?", ("message.query = 'Ready';", "message.textContent = 'Ready';", "message = SELECT Ready;"), "b", "Assigning textContent updates plain text in the DOM."),
        ("What does button.addEventListener('click', handler) do?", ("Calls handler immediately", "Saves a quiz score", "Registers handler to run on a click"), "c", "The function is passed as a handler. The event triggers it later."),
    )))

SAP = SubjectContent("sap-basics", "sap-basics-quiz-v1", "sap-basics-practice-v1",
    questions("practice", (
        ("What does ERP stand for?", ("Enterprise Resource Planning", "Every Record Printed", "External Radio Protocol"), "a", "ERP means Enterprise Resource Planning: connected software for core business processes."),
        ("Why connect purchasing, inventory and finance?", ("To hide all records", "To share consistent business information", "To remove every business rule"), "b", "Shared information helps departments coordinate without retyping the same facts independently."),
        ("Which is an example of master data?", ("Today's delivery event", "One supplier invoice", "A supplier's address"), "c", "Master data describes reusable business entities such as suppliers, customers and materials."),
        ("Which is transactional data?", ("A material description", "A particular purchase order", "A supplier's contact details"), "b", "A purchase order records a specific business event rather than general supplier information."),
        ("A shop buys chairs from a supplier. Which document records what it orders?", ("Purchase order", "Customer payment", "Website stylesheet"), "a", "A purchase order records the goods and quantities being ordered from a supplier."),
        ("The ordered chairs arrive. Which step records their arrival?", ("Send a sales quote", "Register a new learner", "Post a goods receipt"), "c", "A goods receipt records that goods have been received. In this stock example it updates inventory."),
        ("After receiving a supplier invoice, what should the company do before payment?", ("Check it against the order and receipt", "Always pay without checking", "Delete the supplier"), "a", "Checking the order, receipt and invoice helps identify quantity or price differences before payment."),
        ("Which is a simplified purchasing sequence?", ("Pay, delete, forget", "Purchase order, goods receipt, invoice check, payment", "Customer payment, customer order, purchase order"), "b", "This common stock-purchasing example connects buying, receiving and finance; real workflows can vary."),
        ("A customer orders products from the shop. Which document records that request?", ("Supplier invoice", "Goods receipt from a supplier", "Sales order"), "c", "A sales order records what the business agrees to supply to a customer."),
        ("What is this SAP lesson designed to teach?", ("How to access a real company's SAP system", "Basic connected business-process concepts", "That a quiz score proves business expertise"), "b", "These are simplified learning scenarios. They do not run SAP transactions or confirm your understanding automatically."),
    )),
    questions("q", (
        ("What is a main purpose of ERP?", ("Only drawing webpages", "Connecting core business processes and data", "Replacing all human decisions"), "b", "ERP connects business work such as sales, procurement, inventory and finance."),
        ("Which item is master data?", ("One goods receipt", "One invoice", "A customer's address"), "c", "A customer's address is reusable business information; invoices and receipts describe specific events."),
        ("Which document orders goods from a supplier?", ("Purchase order", "Sales invoice to a customer", "Browser event"), "a", "A purchase order specifies a business's requested goods or services from a supplier."),
        ("In the chair example, what records delivery into stock?", ("A new variable", "A goods receipt", "A customer payment"), "b", "The goods receipt records incoming goods and updates stock in this example."),
        ("Why check a supplier invoice against its order and receipt?", ("To change learning status", "To skip inventory records", "To find differences before payment"), "c", "Comparing these records helps check that billed quantities and prices match the agreed and received goods."),
    )))

SUBJECTS = {
    "sql": {"name": "SQL", "title": "SELECT and WHERE", "content": sql_content},
    "python": {"name": "Python", "title": "Variables and simple functions", "content": PYTHON},
    "javascript": {"name": "JavaScript", "title": "Values, DOM elements, and events", "content": JAVASCRIPT},
    "sap": {"name": "SAP", "title": "Basic ERP concepts and business-process scenarios", "content": SAP},
}
