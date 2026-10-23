"""Small subject catalogue; SQL keeps its reviewed content unchanged."""

from dataclasses import dataclass

from . import sql_content
from .sql_content import N_


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
        (N_("What does age = 20 do?"), (N_("Stores 20 under the name age"), N_("Prints 20"), N_("Defines a function")), "a", N_("The equals sign assigns a value to a variable name.")),
        (N_("Which value is a string?"), ("20", "'Hello'", "False"), "b", N_("Quotes mark text. 'Hello' is a string; 20 is an integer and False is a boolean.")),
        (N_("What is count after count = 2 followed by count = count + 3?"), ("2", "3", "5"), "c", N_("Read the old value 2, add 3, then store 5 in count.")),
        (N_("Which keyword defines a Python function?"), ("let", "def", "SELECT"), "b", N_("Use def, a function name, parentheses and a colon to define a function.")),
        (N_("Which line calls a function named greet?"), ("greet()", "def greet", "greet = 'Hi'"), "a", N_("Parentheses call a function. A definition alone does not run its body.")),
        (N_("In def add_one(number):, what is number?"), (N_("The result"), N_("A table"), N_("An input parameter")), "c", N_("A parameter is a name for a value supplied when a function is called.")),
        (N_("What does return do inside a function?"), (N_("Sends a value back to the caller"), N_("Always prints text"), N_("Starts a browser")), "a", N_("return ends the function call and supplies its result to the caller.")),
        (N_("If add_one returns number + 1, what is add_one(4)?"), ("4", "5", "1"), "b", N_("The argument 4 becomes number, so number + 1 gives 5.")),
        (N_("What marks a function's body in Python?"), (N_("Quotation marks"), N_("A semicolon only"), N_("Indentation")), "c", N_("Indented statements belong to the function. Use consistent indentation, normally four spaces.")),
        (N_("Why store result = add_one(4)?"), (N_("It deletes the function"), N_("It lets you reuse the returned value"), N_("It prints automatically")), "b", N_("The return value 5 is assigned to result. You can use it later or print it.")),
    )),
    questions("q", (
        (N_("What value is stored by name = 'Mia'?"), (N_("The number 3"), N_("The text Mia"), N_("A boolean")), "b", N_("Quoted text is a string. The variable name refers to that text.")),
        (N_("What is points after points = 3; points = points + 2?"), ("2", "3", "5"), "c", N_("The second assignment adds 2 to the previous value 3.")),
        (N_("Which definition returns its input plus one?"), ("def add_one(value):\n    return value + 1", "add_one = 1", "def add_one(value):\n    return 1"), "a", N_("The first function uses its parameter value and returns value + 1.")),
        (N_("How do you call add_one with the number 6?"), ("def add_one(6)", "add_one(6)", "add_one = 6"), "b", N_("Put the supplied value inside parentheses after the function name.")),
        (N_("How does return differ from print()?"), (N_("Both always save to SQLite"), N_("return displays a webpage"), N_("return supplies a result; print displays output")), "c", N_("A caller can store and reuse a returned value. print writes output instead.")),
    )))

JAVASCRIPT = SubjectContent("javascript-basics", "javascript-basics-quiz-v1", "javascript-basics-practice-v1",
    questions("practice", (
        (N_("Which value is a JavaScript string?"), ("'Hello'", "10", "false"), "a", N_("Quoted text is a string. Numbers and booleans are different value types.")),
        (N_("Which declaration allows later reassignment?"), ("const count = 0;", "let count = 0;", "def count = 0;"), "b", N_("Use let for a variable whose value will be reassigned.")),
        (N_("What does const prevent?"), (N_("All clicks"), N_("Reading the variable"), N_("Reassigning that variable binding")), "c", N_("A const binding cannot be reassigned. It does not freeze an object's properties.")),
        (N_("What does document.querySelector('#message') select?"), (N_("Every button"), N_("The first element with id message"), N_("A database row")), "b", N_("The # selector matches an HTML id. querySelector returns the first match.")),
        (N_("What is returned if querySelector finds no match?"), ("null", N_("An empty paragraph"), N_("The number 1")), "a", N_("A missing match returns null. Check it before accessing element properties.")),
        (N_("Which property changes an element's plain text?"), ("valueType", "SELECT", "textContent"), "c", N_("Assign a string to textContent to replace an element's text.")),
        (N_("Which event name represents a button press with a mouse?"), ("click", "sql", "return"), "a", N_("A click listener runs when a click event occurs, including keyboard activation of a button.")),
        (N_("Which method registers an event handler?"), ("queryAnswer()", "addEventListener()", "saveDatabase()"), "b", N_("addEventListener connects an event name to a function that will handle it.")),
        (N_("When does the function passed to a click listener normally run?"), (N_("When the variable is declared"), N_("Before the page exists"), N_("When the click event occurs")), "c", N_("Registering the handler waits for future events. It does not call the handler immediately.")),
        (N_("Why place a simple DOM script after the HTML it uses?"), (N_("To create a login"), N_("So the elements exist before selection"), N_("To turn text into SQL")), "b", N_("The browser parses those elements first, so querySelector can find them.")),
    )),
    questions("q", (
        (N_("Which value is a boolean?"), ("'true'", "true", "42"), "b", N_("Unquoted true is a boolean. 'true' is text.")),
        (N_("What can follow let score = 1; to change score to 2?"), ("def score(2)", "score == 2;", "score = 2;"), "c", N_("The equals sign assigns the new value. let allows reassignment.")),
        (N_("How do you select the element with id greeting?"), ("document.querySelector('#greeting')", "document.querySelector('greeting-id')", "SELECT greeting FROM page"), "a", N_("The # character identifies an id in a CSS selector.")),
        (N_("Which statement replaces a selected element's text?"), ("message.query = 'Ready';", "message.textContent = 'Ready';", "message = SELECT Ready;"), "b", N_("Assigning textContent updates plain text in the DOM.")),
        (N_("What does button.addEventListener('click', handler) do?"), (N_("Calls handler immediately"), N_("Saves a quiz score"), N_("Registers handler to run on a click")), "c", N_("The function is passed as a handler. The event triggers it later.")),
    )))

SAP = SubjectContent("sap-basics", "sap-basics-quiz-v1", "sap-basics-practice-v1",
    questions("practice", (
        (N_("What does ERP stand for?"), ("Enterprise Resource Planning", "Every Record Printed", "External Radio Protocol"), "a", N_("ERP means Enterprise Resource Planning: connected software for core business processes.")),
        (N_("Why connect purchasing, inventory and finance?"), (N_("To hide all records"), N_("To share consistent business information"), N_("To remove every business rule")), "b", N_("Shared information helps departments coordinate without retyping the same facts independently.")),
        (N_("Which is an example of master data?"), (N_("Today's delivery event"), N_("One supplier invoice"), N_("A supplier's address")), "c", N_("Master data describes reusable business entities such as suppliers, customers and materials.")),
        (N_("Which is transactional data?"), (N_("A material description"), N_("A particular purchase order"), N_("A supplier's contact details")), "b", N_("A purchase order records a specific business event rather than general supplier information.")),
        (N_("A shop buys chairs from a supplier. Which document records what it orders?"), (N_("Purchase order"), N_("Customer payment"), N_("Website stylesheet")), "a", N_("A purchase order records the goods and quantities being ordered from a supplier.")),
        (N_("The ordered chairs arrive. Which step records their arrival?"), (N_("Send a sales quote"), N_("Register a new learner"), N_("Post a goods receipt")), "c", N_("A goods receipt records that goods have been received. In this stock example it updates inventory.")),
        (N_("After receiving a supplier invoice, what should the company do before payment?"), (N_("Check it against the order and receipt"), N_("Always pay without checking"), N_("Delete the supplier")), "a", N_("Checking the order, receipt and invoice helps identify quantity or price differences before payment.")),
        (N_("Which is a simplified purchasing sequence?"), (N_("Pay, delete, forget"), N_("Purchase order, goods receipt, invoice check, payment"), N_("Customer payment, customer order, purchase order")), "b", N_("This common stock-purchasing example connects buying, receiving and finance; real workflows can vary.")),
        (N_("A customer orders products from the shop. Which document records that request?"), (N_("Supplier invoice"), N_("Goods receipt from a supplier"), N_("Sales order")), "c", N_("A sales order records what the business agrees to supply to a customer.")),
        (N_("What is this SAP lesson designed to teach?"), (N_("How to access a real company's SAP system"), N_("Basic connected business-process concepts"), N_("That a quiz score proves business expertise")), "b", N_("These are simplified learning scenarios. They do not run SAP transactions or confirm your understanding automatically.")),
    )),
    questions("q", (
        (N_("What is a main purpose of ERP?"), (N_("Only drawing webpages"), N_("Connecting core business processes and data"), N_("Replacing all human decisions")), "b", N_("ERP connects business work such as sales, procurement, inventory and finance.")),
        (N_("Which item is master data?"), (N_("One goods receipt"), N_("One invoice"), N_("A customer's address")), "c", N_("A customer's address is reusable business information; invoices and receipts describe specific events.")),
        (N_("Which document orders goods from a supplier?"), (N_("Purchase order"), N_("Sales invoice to a customer"), N_("Browser event")), "a", N_("A purchase order specifies a business's requested goods or services from a supplier.")),
        (N_("In the chair example, what records delivery into stock?"), (N_("A new variable"), N_("A goods receipt"), N_("A customer payment")), "b", N_("The goods receipt records incoming goods and updates stock in this example.")),
        (N_("Why check a supplier invoice against its order and receipt?"), (N_("To change learning status"), N_("To skip inventory records"), N_("To find differences before payment")), "c", N_("Comparing these records helps check that billed quantities and prices match the agreed and received goods.")),
    )))

SUBJECTS = {
    "sql": {"name": "SQL", "title": "SELECT and WHERE", "content": sql_content},
    "python": {"name": "Python", "title": N_("Variables and simple functions"), "content": PYTHON},
    "javascript": {"name": "JavaScript", "title": N_("Values, DOM elements, and events"), "content": JAVASCRIPT},
    "sap": {"name": "SAP", "title": N_("Basic ERP concepts and business-process scenarios"), "content": SAP},
}
