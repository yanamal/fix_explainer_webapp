#!/usr/bin/python3.7
# A very simple Flask Hello World app for you to get started with...

from flask import Flask, render_template, request, jsonify
from python_fix_explainer import fix_code


student_code = '''
def helloWorld():
    return('Hello World!')
'''


unit_tests = [
    'helloWorld() == "Hello World!"',
]

correct = [
    '''
def helloWorld():
    return 'Hello World!'
    '''
]

fix_data = fix_code(student_code, unit_tests, correct)

app = Flask(__name__)

@app.route('/')
def index_page():
    app.logger.info(fix_data)
    return render_template('fix_explainer.html')


@app.route('/generate', methods= ['POST'])
def generate_fixes():
    input_data = request.get_json()
    print(input_data)
    fix_output = fix_code(input_data['code'], input_data['tests'], input_data['correct'])
    return jsonify(fix_output)
