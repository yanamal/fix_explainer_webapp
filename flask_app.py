#!/usr/local/bin/python3.7

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, login_required, logout_user
from flask_migrate import Migrate
import json
from python_fix_explainer import fix_code, has_failing_unit_test
from pytz import timezone
import userdata

current_semester = "Spring2023"

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
    return jsonify({
        'result_type': help_request.result,
        'analysis': json.loads(help_request.analysis_output)
    })


@app.route('/view_analysis')
@login_required
def view_student_code():
    request_id = request.values.get('request_id')
    return render_template('retrieve_analysis.html', request_id=request_id)


@app.route('/request_queue', methods=["GET", "POST"])
@login_required
def render_help_queue():
    # if post request, then first process the "being helped" submitted value
    if request.method == "POST":
        being_helped_request = HelpRequest.query.filter_by(id=request.values.get('being_helped')).first()
        being_helped_request.being_helped = True
        db.session.commit()

    return render_template('request_queue.html',
        requests=HelpRequest.query.filter_by(being_helped=False).order_by(db.desc(HelpRequest.request_time)).all(),
        processed_requests=HelpRequest.query.filter_by(being_helped=True).order_by(db.desc(HelpRequest.request_time)).all(),
        in_study=userdata.students_in_study,
        timezone=timezone)


@app.route('/student_confirm')
def confirm_help_request():
    return render_template('student_confirm.html')


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
        student_code = request.form.get('code').strip()
        if len(student_code) > 0:
            try:
                compile(student_code, 'code field', 'exec')
            except SyntaxError as e:
                syntax_error_data = {
                        'code': request.form.get('code'),
                        'message': str(e),
                        'lineno': e.lineno,
                        'offset': e.offset,
                    }
                if request.form.get('allow_syntax_error'):
                    syntax_error_request = HelpRequest(
                        student_name=request.form.get('student-name'),
                        student_email=request.form.get('email'),
                        problem_id = request.form.get('problem'),
                        is_conceptual = 'Conceptual' in request.form,
                        is_implementing = 'Implementing' in request.form,
                        is_debugging = 'Debugging' in request.form,
                        student_code = request.form.get('code'),
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
            prob = Problem.query.filter_by(id=request.form.get('problem')).first()
            fix_output = fix_code(
                request.form.get('code'),
                [t.code for t in prob.tests],
                [p.code for p in prob.solutions])
            analysis_request = HelpRequest(
                student_name=request.form.get('student-name'),
                student_email=request.form.get('email'),
                problem_id = request.form.get('problem'),
                is_conceptual = 'Conceptual' in request.form,
                is_implementing = 'Implementing' in request.form,
                is_debugging = 'Debugging' in request.form,
                student_code = request.form.get('code'),
                result = 'Fixes Generated',
                analysis_output = json.dumps(fix_output)
            )
            db.session.add(analysis_request)
            db.session.commit()
            return jsonify({
                'result': 'submitted_code_with_analysis',
                'submitted': True,
            })


        # if we are here, there was no student code
        no_code_request = HelpRequest(
            student_name=request.form.get('student-name'),
            student_email=request.form.get('email'),
            problem_id = request.form.get('problem'),
            is_conceptual = 'Conceptual' in request.form,
            is_implementing = 'Implementing' in request.form,
            is_debugging = 'Debugging' in request.form,
            student_code = request.form.get('code'),
            result = 'No Code Submitted',
            analysis_output = ''
        )
        db.session.add(no_code_request)
        db.session.commit()
        return jsonify({
            'result': 'submitted_blank_code',
            'submitted': True,
        })


@app.route('/submit_problem', methods=["GET", "POST"])
def submit_page():
    if request.method == "GET":
        return render_template('submit_problem.html')
    elif request.method == "POST":
        form_contents = {
            'homework':  request.form.get('homework'),
            'prob_name':  request.form.get('prob_name'),
            'correct': request.form.getlist('correct[]'),
            'tests': request.form.getlist('test[]')
        }
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
        failing_solution = has_failing_unit_test(form_contents['correct'], form_contents['tests'])
        if failing_solution:
            code_i, test_i = failing_solution
            return render_template('submit_problem.html', test_failed=True,
                failing_code=form_contents['correct'][code_i],
                failing_test=form_contents['tests'][test_i],
                prefilled=form_contents
            )

        # actually record in db
        problem = Problem(name=form_contents['prob_name'], homework=form_contents['homework'])
        db.session.add(problem)
        for solution in form_contents['correct']:
            sol = Solution(code=solution, problem=problem)
            db.session.add(sol)
        for test in form_contents['tests']:
            t = Unittest(code=test, problem=problem)
            db.session.add(t)
        db.session.commit()
        # TODO: put submitted data and/or databse key into confirmation?
        return render_template('submit_confirmation.html')


# ~~~~~~~~


class Solution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # TODO: make sure this is long enough, get rid of character limit?..
    code = db.Column(db.String(4096))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'),
        nullable=False)


class Unittest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(4096))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'),
        nullable=False)


class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(4096))
    semester = db.Column(db.String(4096), default=current_semester)
    homework = db.Column(db.String(4096), default="HW1")
    solutions =  db.relationship('Solution', backref='problem')
    tests =  db.relationship('Unittest', backref='problem')


class HelpRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_time = db.Column(db.DateTime(timezone=False), server_default=db.func.now())
    being_helped = db.Column(db.Boolean, default=False)  # is the student already being helped, or are they still waiting in the queue?
    student_name = db.Column(db.String(4096))
    student_email = db.Column(db.String(4096))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    problem = db.relationship('Problem', foreign_keys=problem_id)
    is_conceptual = db.Column(db.Boolean, default=False)
    is_implementing = db.Column(db.Boolean, default=False)
    is_debugging = db.Column(db.Boolean, default=False)
    student_code = db.Column(db.String(4096))
    result = db.Column(db.String(4096))  # no code, syntax error, or generated fixes
    analysis_output = db.Column(db.String(65535))  # stringified json. TODO: was there a datatype for just json?..