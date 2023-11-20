# Using this tutorial as starting point:
# https://blog.pythonanywhere.com/198/

from time import sleep, gmtime, localtime
from datetime import datetime
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flask_app import HelpRequest, Problem, InteractionLog, reduce_code, reduce_student_functions # TODO: move reduce_code, reduce_student_functions here?
from python_fix_explainer import fix_code, has_failing_unit_test, MutableAst, breadth_first, get_run_trace

import ast

import logging, sys

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# TODO: use sqlalchemy and a single config across all parts of the app?
#  (rather than flask-squalchemy in the flask portion of the app)


# Database setup
username = "teacodefix"     # you may put your username instead
password = "8pa3lehz"  # use your MySQL password
hostname = "teacodefix.mysql.pythonanywhere-services.com"
databasename = "teacodefix$classdata"

SQLALCHEMY_DATABASE_URI = (
    f"mysql://{username}:{password}@{hostname}/{databasename}"
)
SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 299}
SQLALCHEMY_TRACK_MODIFICATIONS = False


engine = create_engine(
    SQLALCHEMY_DATABASE_URI, **SQLALCHEMY_ENGINE_OPTIONS
)
Session = sessionmaker(engine, autocommit=True)

def find_pending_request():
    session = Session()
    with session.begin():
        help_request = session.query(HelpRequest).filter_by(result="Processing").first()
        if help_request:
            print('processing request', help_request.id, flush=True)
            print()
            reduced_student_code = reduce_code(help_request.student_code)


            prob = help_request.problem
            reduced_solutions = [reduce_code(p.code) for p in prob.solutions]
            reduced_student_code = reduce_student_functions(reduced_student_code, reduced_solutions)

            # Add test set-up code to all versions
            setup_code = prob.test_setup_code if prob.test_setup_code else ""
            reduced_solutions = [s + '\n' + setup_code for s in reduced_solutions]
            reduced_student_code = reduced_student_code + '\n' + setup_code

            print('student code:')
            print(reduced_student_code, flush=True)
            print()


            print('solutions:')
            for s in reduced_solutions:
                print(s, flush=True)
                print()

            print('unit tests:')
            print([t.code for t in prob.tests], flush=True)

            return {
                'request_id': help_request.id,
                'student_code': reduced_student_code,
                'tests': [t.code for t in prob.tests],
                'solutions': reduced_solutions,
            }

def store_logs(input_data, client_ip):
    session = Session()
    with session.begin():
        log = InteractionLog(log_data=input_data, client_ip=client_ip)
        session.add(log)

def process_request(data):

    try:
        store_logs([{
                'timestamp': int(datetime.now().timestamp()),
                'event_type': 'analysis_request',
                'page_data':{
                    'help_request_id': data['request_id']
                },
                'data': data
            }],
            client_ip=None)

        fix_output = fix_code(
            data['student_code'],
            data['tests'],
            data['solutions']
        )

        store_logs([{
                'timestamp': int(datetime.now().timestamp()),
                'event_type': 'analysis_complete',
                'page_data':{
                    'help_request_id': data['request_id']
                },
                'data': fix_output
            }],
            client_ip=None)

        result = 'Analysis Generated'
        output = json.dumps(fix_output)
        print('fix_code done')
    except Exception as e:
        result = 'Error analyzing'
        output = str(e)
        print('error processing:', str(e), flush=True)

    session = Session()
    with session.begin():
        session.query(HelpRequest).filter_by(id=data['request_id']).update({
                'result': result,
                'analysis_output': output
            })


if __name__ == "__main__":
    while True:
        request_data = find_pending_request()
        if request_data:
            process_request(request_data)
            pass
        else:
            sleep(1)