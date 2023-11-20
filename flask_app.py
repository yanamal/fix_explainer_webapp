#!/usr/local/bin/python3.7

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, login_required, logout_user
from flask_migrate import Migrate
import json
import itertools
from collections import defaultdict
from pytz import timezone
import ast
import os
import requests
from lxml import html

from python_fix_explainer import fix_code, has_failing_unit_test, MutableAst, breadth_first
import userdata

current_semester = "Fall2023"

app = Flask(__name__)
SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="teacodefix",
    password="8pa3lehz",
    hostname="teacodefix.mysql.pythonanywhere-services.com",
    databasename="teacodefix$classdata",
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = userdata.init(app)


@login_manager.user_loader
def load_user(user_id):
    return userdata.all_users.get(user_id)


@app.route('/')
def index_page():
    return render_template('fix_explainer.html')


@app.route("/login", methods=["GET", "POST"])
@login_manager.unauthorized_handler
def login():
    if request.method=="POST":
        username = request.values["username"]
        if username not in userdata.all_users:
            return render_template("login.html", error=True)

        user = userdata.all_users[username]
        if not user.check_password(request.values["password"]):
            return render_template("login.html", error=True)

        login_user(user)
        return redirect(url_for('render_help_queue'))
    elif request.method=="GET":
        return render_template('login.html')


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/generate', methods=['POST'])
def generate_fixes():
    input_data = request.get_json()
    print(input_data)
    fix_output = fix_code(input_data['code'], input_data['tests'], input_data['correct'])
    return jsonify(fix_output)


@app.route('/retrieve', methods=['POST'])
def retrieve_fix_data():
    print('retrieving analysis for request id', request.values.get('request_id'))
    help_request = HelpRequest.query.filter_by(id=request.values.get('request_id')).first()

    exercise_url = None
    chapter = None
    num_exercises = 0
    if help_request.problem.assignment:
        chapter = help_request.problem.assignment.chapter_url
        exercise_url = '/'.join((help_request.problem.assignment.book_url, chapter, 'Exercises.html'))
        ex_result = requests.get(exercise_url)
        if ex_result.status_code//100 == 2: # 200 or 2XX code
            ex_tree = html.fromstring(ex_result.content)
            num_exercises = len(ex_tree.xpath('//*[@data-component="question"]'))
        else:
            # some non-200 status code was returned - no exercises
            exercise_url = None
            chapter = None

    practice_options = []
    for p in help_request.problem.practice_problems:
        practice_options.append({
            'description': p.issue_description,
            'url': f'{help_request.student_book_url}/{p.page_url}#{p.practice_name}'
        })

    # //*[@data-component="question"]
    return jsonify({
        'result_type': help_request.result,
        'exercise_url': exercise_url,
        'chapter': chapter,
        'num_exercises': num_exercises,
        'analysis': json.loads(help_request.analysis_output),
        'practice_problems': practice_options
    })

@app.route('/feedback', methods=['POST'])
def analysis_feedback():
    new_feedback = Feedback(
        request_id = request.values.get('request_id'),
        interface_broken = 'interface_broken' in request.values,
        analysis_bad = 'analysis_bad' in request.values,
        confusing = 'confusing' in request.values,
        feedback_text = request.values.get('feedback_text')
        )

    db.session.add(new_feedback)
    db.session.commit()

    return jsonify({
        'status': 'success'
    })


@app.route('/view_analysis')
@login_required
def view_student_code():
    request_id = request.values.get('request_id')
    return render_template('retrieve_analysis.html', request_id=request_id)


@app.route('/debug_info')
@login_required
def view_debug_info():
    help_request = HelpRequest.query.filter_by(id=request.values.get('request_id')).first()
    # TODO: store reduced code in DB when processing request?
    reduced_student_code = reduce_code(help_request.student_code)
    prob = help_request.problem
    reduced_solutions = [reduce_code(p.code) for p in prob.solutions]
    reduced_student_code = reduce_student_functions(reduced_student_code, reduced_solutions)

    return render_template('debug_info.html',
                           orig_student_code = help_request.student_code,
                           orig_solutions = [p.code for p in prob.solutions],
                           unit_tests = [t.code for t in prob.tests],
                           reduced_student_code = reduced_student_code,
                           reduced_solutions = reduced_solutions,
                           analysis_output = help_request.analysis_output)


@app.route('/request_queue', methods=["GET", "POST"])
@login_required
def render_help_queue():
    # if post request, then first process the submitted value(s)
    if request.method == "POST":
        if 'being_helped' in request.values:
            being_helped_request = HelpRequest.query.filter_by(id=request.values.get('being_helped')).first()
            being_helped_request.being_helped = True
        if 'rerun' in request.values:
            rerun_request = HelpRequest.query.filter_by(id=request.values.get('rerun')).first()
            rerun_request.result = 'Processing'
        db.session.commit()
        return redirect(url_for('render_help_queue'))
        # This redirect is silly, but it prevents accidentally re-submitting the post request when refreshing the page
        # by redirecting to a get request for the same page after doing the work.

    return render_template('request_queue.html',
        requests=HelpRequest.query.filter_by(being_helped=False).filter_by(semester=current_semester).order_by(db.desc(HelpRequest.request_time)).all(),
        processed_requests=HelpRequest.query.filter_by(being_helped=True).filter_by(semester=current_semester).order_by(db.desc(HelpRequest.request_time)).all(),
        in_study=userdata.students_in_study,
        timezone=timezone)

@app.route('/rerun_all', methods=["POST"])
@login_required
def rerun_all():
    # TODO: only current semester?..
    HelpRequest.query.filter(HelpRequest.result.notin_(['No Code Submitted', 'Syntax Error'])).update({HelpRequest.result: "Processing"}, synchronize_session=False)
    db.session.commit()
    return redirect(url_for('render_help_queue'))



@app.route('/student_confirm')
def confirm_help_request():
    return render_template('student_confirm.html')


@app.route('/encoding_error')
def show_encoding_Error():
    return render_template('encoding_error.html')


@app.route('/help_request', methods=["GET", "POST"])
def student_help_request():
    # respond to get request (get request form)
    if request.method == "GET":
        # Get problem data
        problems = []
        homeworks = set()
        semester_problems = Problem.query.filter_by(semester=current_semester)
        for p in semester_problems:
            problems.append({
                'homework': p.homework,
                'name': p.name,
                'id': p.id
            })
            homeworks.add(p.homework)
        return render_template('help_request.html', problems=problems, homeworks=homeworks)
    # respond to post request (submit help request)
    elif request.method == "POST":
        student_code=""
        code_file = request.files.get('codefile')
        if code_file:
            student_code = code_file.read()  # .decode('utf-8')
        if len(student_code) > 0:
            try:
                compile(student_code, 'code field', 'exec')
            except ValueError:  # student code has unreadable 'null' bytes in it. must be a bad encoding.
                return render_template('encoding_error.html')
            except SyntaxError as e:
                syntax_error_data = {
                        'code': student_code.decode('utf-8'),
                        'message': str(e),
                        'lineno': e.lineno,
                        'offset': e.offset,
                    }
                if request.form.get('allow_syntax_error'):
                    syntax_error_request = HelpRequest(
                        student_name=request.form.get('student-name'),
                        student_email=request.form.get('email'),
                        problem_id = request.form.get('problem'),
                        student_book_url = request.form.get('section_url'),
                        is_conceptual = 'Conceptual' in request.form,
                        is_implementing = 'Implementing' in request.form,
                        is_debugging = 'Debugging' in request.form,
                        student_code = student_code,
                        result = 'Syntax Error',
                        analysis_output = json.dumps(syntax_error_data)
                    )
                    db.session.add(syntax_error_request)
                    db.session.commit()

                    return jsonify({
                        'result': 'submitted_syntax_error',
                        'submitted': True,
                    })

                # if whe are here, there was a syntax error
                # (and the student didn't explicitly ask to submit with the syntax error)
                return jsonify({
                    'result': 'syntax_error',
                    'submitted': False,
                    'error': syntax_error_data,
                })

            # if we are here, the student code compiled.

            # first, record in-progress request in the database
            analysis_request = HelpRequest(
                student_name=request.form.get('student-name'),
                student_email=request.form.get('email'),
                problem_id = request.form.get('problem'),
                student_book_url = request.form.get('section_url'),
                is_conceptual = 'Conceptual' in request.form,
                is_implementing = 'Implementing' in request.form,
                is_debugging = 'Debugging' in request.form,
                student_code = student_code,
                result = 'Processing',
                analysis_output = ''
            )
            db.session.add(analysis_request)
            db.session.commit()

            # request_id = analysis_request.id
            # print(request_id)

            # # then, process the analysis
            # prob = Problem.query.filter_by(id=request.form.get('problem')).first()

            # reduced_student_code = reduce_code(student_code)
            # reduced_solutions = [reduce_code(p.code) for p in prob.solutions]

            # reduced_student_code = reduce_student_functions(reduced_student_code, reduced_solutions)

            # fix_output = fix_code(
            #     reduced_student_code,
            #     [t.code for t in prob.tests],
            #     reduced_solutions)

            # print('fix_code done')

            # analysis_request = HelpRequest.query.filter_by(id=request_id).first()
            # analysis_request.result = 'Analysis Generated'
            # analysis_request.analysis_output = json.dumps(fix_output)
            # db.session.commit()


            return jsonify({
                'result': 'submitted_code_with_analysis',
                'submitted': True,
            })


        # if we are here, there was no student code
        no_code_request = HelpRequest(
            student_name=request.form.get('student-name'),
            student_email=request.form.get('email'),
            problem_id = request.form.get('problem'),
            student_book_url = request.form.get('section_url'),
            is_conceptual = 'Conceptual' in request.form,
            is_implementing = 'Implementing' in request.form,
            is_debugging = 'Debugging' in request.form,
            student_code = student_code,
            result = 'No Code Submitted',
            analysis_output = ''
        )
        db.session.add(no_code_request)
        db.session.commit()
        return jsonify({
            'result': 'submitted_blank_code',
            'submitted': True,
        })


@app.route('/problems', methods=["GET"])
def list_problems():
    problems=Problem.query.filter_by(semester=current_semester)
    return render_template('problems.html', problems=problems)



@app.route('/submit_problem', methods=["GET", "POST"])
def submit_page():
    if request.method == "GET":
        # request is to render the problem edit/create form
        # TODO: somehow having 0 unit tests makes default unit test come back?..

        if 'problem_id' in request.values:
            problem = Problem.query.filter_by(id=request.values.get('problem_id')).first()
            form_fill = {
                'problem_id': request.values.get('problem_id'),
                'homework':  problem.homework,
                'prob_name':  problem.name,
                'correct': [s.code for s in problem.solutions],
                'tests': [t.code for t in problem.tests],
                'test_setup_code': problem.test_setup_code,
                'practice_pages': [p.page_url for p in problem.practice_problems],
                'practice_activities': [p.practice_name for p in problem.practice_problems],
                'practice_descs': [p.issue_description for p in problem.practice_problems],
            }
            print(form_fill)
        else:
            form_fill = None
        return render_template('submit_problem.html', prefilled=form_fill)
    elif request.method == "POST":
        # request is to submit the problem into the database
        # (presumably from the submit_problem.html form)
        form_contents = {
            'problem_id': request.form.get('problem_id'),
            'homework':  request.form.get('homework'),
            'prob_name':  request.form.get('prob_name'),
            'correct': request.form.getlist('correct[]'),
            'tests': request.form.getlist('test[]'),
            'test_setup_code': request.form.get('test_setup_code'),
            'practice_pages': request.form.getlist('page_url[]'),
            'practice_activities': request.form.getlist('exercise_name[]'),
            'practice_descs': request.form.getlist('issue_desc[]'),
        }
        print(form_contents)
        # Check that all the code fields compile without syntax errors
        for i, solution in enumerate(form_contents['correct']):
            try:
                compile(solution, 'code field', 'exec')
            except SyntaxError as e:
                which_code_string = f'Solution {i+1}'
                return render_template(
                    'submit_problem.html', syntax_error=True, bad_code=solution,
                    prefilled=form_contents, which=which_code_string,
                    error = str(e), lineno=e.lineno, offset=e.offset)

        for i, test in enumerate(form_contents['tests']):
            try:
                compile(test, 'code field', 'exec')
            except SyntaxError as e:
                which_code_string = f'Unit Test {i+1}'
                return render_template(
                    'submit_problem.html', syntax_error=True, bad_code=test,
                    prefilled=form_contents, which=which_code_string,
                    error = str(e), lineno=e.lineno, offset=e.offset)

        # check that each solution passes each unit test
        # TODO: reduce code first?..
        code_to_test = [s + '\n' + form_contents['test_setup_code'] for s in form_contents['correct']]
        failing_solution = has_failing_unit_test(code_to_test, form_contents['tests'])
        if failing_solution:
            code_i, test_i = failing_solution
            return render_template('submit_problem.html', test_failed=True,
                failing_code=form_contents['correct'][code_i],
                failing_test=form_contents['tests'][test_i],
                prefilled=form_contents
            )

        # if we are here, we passed tests - actually record in db

        if form_contents['problem_id']:
            # we are editing an existing problem
            print('existing problem')
            problem = Problem.query.filter_by(id=request.values.get('problem_id')).first()

            # replace values as needed
            problem.name=form_contents['prob_name']
            problem.homework=form_contents['homework']
            problem.test_setup_code = form_contents['test_setup_code']

            # delete all linked data (solutions/tests/practice problems) because we will have to re-add later
            # (no good way to tell which ones were edited/deleted/added)
            for solution in problem.solutions:
                db.session.delete(solution)
            for test in problem.tests:
                db.session.delete(test)
            for practice in problem.practice_problems:
                db.session.delete(practice)
        else:
            # we are creating a new problem
            print('new problem')
            problem = Problem(name=form_contents['prob_name'], homework=form_contents['homework'], test_setup_code = form_contents['test_setup_code'])
            db.session.add(problem)

        # either way, add / re-add solutions, tests, practice problems
        for solution in form_contents['correct']:
            sol = Solution(code=solution, problem=problem)
            db.session.add(sol)
        for test in form_contents['tests']:
            t = Unittest(code=test, problem=problem)
            db.session.add(t)
        for page, activity, desc in zip(form_contents['practice_pages'], form_contents['practice_activities'], form_contents['practice_descs']):
            p = ProblemPractice(page_url=page, practice_name=activity, issue_description=desc, problem=problem)
            db.session.add(p)
        db.session.commit()
        # TODO: put submitted data and/or databse key into confirmation?
        return render_template('submit_confirmation.html')


@app.route('/validate_compile', methods=["GET","POST"])
def try_compiling():
    input_data = request.get_json()
    code=input_data['code']
    print(code)
    try:
        compile(code, 'code field', 'exec')
    except SyntaxError as e:
        return jsonify({
            'compiles': False,
            'error': str(e),
            'lineno': e.lineno,
            'offset': e.offset
        })
    return jsonify({
        'compiles': True
    })


@app.route('/log_interactions', methods=['POST'])
def store_js_logs():
    input_data = request.get_json()
    client_ip =request.headers['X-Real-IP']
    return store_logs(input_data, client_ip)


def store_logs(input_data, client_ip):
    log = InteractionLog(log_data=input_data, client_ip=client_ip)
    db.session.add(log)
    db.session.commit()
    # TODO: catch exception, return fail?
    return jsonify({
        'status': 'success'
    })

@app.route('/view_log_set')
def view_log_set():
    log_ids = request.values.getlist('log_id')
    logs = InteractionLog.query.filter(InteractionLog.id.in_(log_ids)).all()
    return list(itertools.chain.from_iterable([l.log_data for l in logs]))

@app.route('/summarize_logs')
def summarize_logs():
    logs = InteractionLog.query.all()  # TODO: explicitly sort by store_time?..

    # First, group by ip address (same ip=same user, possibly same session/interaction set)
    logs_by_ip = defaultdict(list)
    for log_set in logs:
        logs_by_ip[log_set.client_ip].append(log_set)

    # Next, within each ip/user, find contiguous groups based on help request id (assuming the log is a help request log)
    # also record per-log-set metadata
    all_grouped_logs = []
    for ip in logs_by_ip: # for each ip/user
        ip_logs = logs_by_ip[ip]
        current_request_id = None  # request id of current batch
        first_timestamp = None  # store timestamp of first logset in current batch (for current request id)
        current_group = []  # current running group of log_sets
        for log_set in ip_logs:  # for each logset within the current user
            if first_timestamp is None:
                first_timestamp = log_set.store_time
            # figure out the request_id for this log_set (assuming there is one, it should be the same across the log set)
            this_request_id = None
            if isinstance(log_set.log_data, list):
                if len(log_set.log_data) > 0:
                    a_log_entry = log_set.log_data[0]
                    if 'page_data' in a_log_entry and 'help_request_id' in a_log_entry['page_data']:
                        this_request_id = a_log_entry['page_data']['help_request_id']
            if this_request_id == current_request_id:
                # this log_set belongs to the current running group - same request id.
                # add it to the group.
                current_group.append(log_set.id)
            else:
                # this request id is different from our current running set. finish up current set and start a new one.
                if len(current_group) > 0:
                    # current set actually has something in it. add relevant metadata to all_grouped_logs
                    all_grouped_logs.append({
                        'ip': ip,
                        'start_time': timezone('Etc/UTC').localize(first_timestamp).astimezone(timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z'),
                        'timestamp': first_timestamp,
                        'logs_params': '&'.join([f'log_id={i}' for i in current_group ]),
                        'help_request_id': current_request_id  # (the old "current" request)
                    })

                # now resent the variables for the current running set
                current_group = []
                current_group.append(log_set.id) # TODO: restructure if/else to do this regardless?
                current_request_id = this_request_id
                first_timestamp = log_set.store_time
        # add the last "current group" to all_grouped_logs
        all_grouped_logs.append({
            'ip': ip,
            'start_time': timezone('Etc/UTC').localize(first_timestamp).astimezone(timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z'),
            'timestamp': first_timestamp,
            'logs_params': '&'.join([f'log_id={i}' for i in current_group ]),
            'help_request_id': current_request_id  # (the old "current" request)
        })

    # finally, sort all_grouped_logs by time
    all_grouped_logs.sort(key=lambda l: l['timestamp'])

    return render_template('summarize_logs.html', grouped_logs=all_grouped_logs)

# ~~~~~~~~


def reduce_code(code_str, remove_main = False, remove_tests = False): # TODO - remove main based on HW?!
    code_tree = MutableAst(py_ast=ast.parse(code_str))

    to_remove = []
    for node in breadth_first(code_tree):
        if node.nodeType == 'Str' and node.parent.nodeType == 'Expr':
            to_remove.append(node.parent)
        elif node.nodeType == 'FunctionDef' and node.name == 'FunctionDef name: main' and remove_main:
            to_remove.append(node)
        elif node.nodeType == 'Attribute' \
                and node.name == 'Attribute(ctx=Load)(attr = TestCase)' \
                and node.children_dict['value'].name == 'Load identifier unittest' \
                and node.parent.name == 'NodeList: bases of ClassDef' \
                and remove_tests:
            to_remove.append(node.parent.parent)
        elif node.nodeType == 'Compare' and node.name == "Compare operators: ['Eq']" \
                and node.parent.name == 'If' \
                and node.children_dict['left'].name == 'Load identifier __name__' \
                and node.children_dict['comparators'].children_dict[0].name == 'Str(s = __main__)':
            to_remove.append(node.parent)
        elif node.nodeType == 'Call' and node.children_dict['func'].name == 'Load identifier main':
            to_remove.append(node.parent) # expression which calls main
        elif node.name == 'Attribute(ctx=Load)(attr = show)' \
             and node.children_dict['value'].name == 'Load identifier plt':
            to_remove.append(node.parent.parent) # expression which calls plt.show()

    for node in to_remove:
        node.parent.remove_child(node)

    return str(code_tree)


# reduce top-level student functions to just those present in at least one solution
def reduce_student_functions(student_code, solutions):
    solution_funcs = set()
    solution_classes = set()
    for s in solutions:
        s_tree = MutableAst(py_ast=ast.parse(s))
        for top_level_expr in s_tree.children_dict['body'].children:
            if top_level_expr.nodeType == 'FunctionDef':
                solution_funcs.add(top_level_expr.ast.name)
            elif top_level_expr.nodeType == 'ClassDef':
                solution_classes.add(top_level_expr.ast.name)

    to_remove = []
    some_functions_left = False
    student_tree = MutableAst(py_ast=ast.parse(student_code))
    for top_level_expr in student_tree.children_dict['body'].children:
        if top_level_expr.nodeType == 'FunctionDef':
            if not (top_level_expr.ast.name in solution_funcs):
                to_remove.append(top_level_expr)
            else:
                # we are not removing this one, yay!
                some_functions_left = True
        elif top_level_expr.nodeType == 'ClassDef':
            # TODO: combine class and function logic?..
            if not (top_level_expr.ast.name in solution_classes):
                to_remove.append(top_level_expr)
            else:
                # if there are classes left, those count as something left too
                some_functions_left = True


    for node in to_remove:
        node.parent.remove_child(node)

    if not some_functions_left:
        # oops, we removed everything.
        return student_code  # never mind, let's just roll that back
        # TODO: only if there aren't also classes remaining?.. do same with classes?..

    return str(student_tree)



def test_file_stuff():
    py_ast = ast.parse("""
import os

print('file stuff:')
print(os.getcwd())
print(os.listdir())
    """)
    code_tree = MutableAst(py_ast=py_ast)
    code_tree.test([False])

    print(eval('os.getcwd()'))




# ~~~~~~~~


class Solution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # TODO: make sure this is long enough, get rid of character limit?..
    code = db.Column(db.String(65535))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'),
        nullable=False)


class Unittest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(65535))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'),
        nullable=False)


class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(4096))
    semester = db.Column(db.String(4096), default=current_semester)
    homework = db.Column(db.String(4096), default="HW1")
    solutions =  db.relationship('Solution', backref='problem')
    tests =  db.relationship('Unittest', backref='problem')
    test_setup_code = db.Column(db.String(65535), default="")  # Code to append to solution as set-up to evaluating unit test.
    # TODO: test_setup_code should probably be per unit test, and handled in the library
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
    practice_problems = db.relationship('ProblemPractice', backref='problem')


class ProblemPractice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_url = db.Column(db.String(4096))
    practice_name = db.Column(db.String(4096))
    issue_description = db.Column(db.String(65535))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'),
        nullable=False)


# TODO: clean up assignment-specific practice problem stuff
class PracticeLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(4096))
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'),
        nullable=False)



# define an assignment which is (optionally) associated with a chapter in a Runestone book
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(4096))
    chapter_url = db.Column(db.String(4096))  # TODO: no longer applicable?
    book_url = db.Column(db.String(4096))   # TODO: no longer applicable?
    practice_problems = db.relationship('PracticeLink', backref='assignment')
    problems = db.relationship('Problem', backref='assignment')


class HelpRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_time = db.Column(db.DateTime(timezone=False), server_default=db.func.now())
    being_helped = db.Column(db.Boolean, default=False)  # is the student already being helped, or are they still waiting in the queue?
    student_name = db.Column(db.String(4096))
    student_email = db.Column(db.String(4096))
    student_book_url =  db.Column(db.String(4096), default='https://runestone.academy/ns/books/published/Fall23-SI206-TTh/')
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    problem = db.relationship('Problem', foreign_keys=problem_id)
    is_conceptual = db.Column(db.Boolean, default=False)
    is_implementing = db.Column(db.Boolean, default=False)
    is_debugging = db.Column(db.Boolean, default=False)
    student_code = db.Column(db.String(65535))
    result = db.Column(db.String(4096))  # no code, syntax error, or generated fixes
    semester = db.Column(db.String(4096), default=current_semester)
    analysis_output = db.Column(db.String(65535))  # stringified json. TODO: was there a datatype for just json?..


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer)  # TODO: maybe actually set foreign key to helprequest.id? but not super necessary and may be annoying to figure out?
    report_time = db.Column(db.DateTime(timezone=False), server_default=db.func.now())
    interface_broken = db.Column(db.Boolean, default=False)
    analysis_bad = db.Column(db.Boolean, default=False)
    confusing = db.Column(db.Boolean, default=False)
    feedback_text = db.Column(db.String(65535))

class InteractionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_time = db.Column(db.DateTime(timezone=False), server_default=db.func.now())
    client_ip = db.Column(db.String(4096), default="")
    log_data = db.Column(db.JSON)
