import os
import subprocess
import re
import shutil

DATABASE_NAME = "course"
MYSQL_DEFAULT_OUTPUT_DIR = "/var/lib/mysql/{}/".format(DATABASE_NAME)  # this is the only location mysql can write to


def initialize_sql_db(user = 'root', pw = 'root', db_name = DATABASE_NAME):
    """
    Start mySQL service and initialize mysql database.
    :param user:
    :param pw:
    :return:
    """
    subprocess.call('service mysql start', shell=True)
    # command to create a database
    cmd = '''mysql -u {} -p{} -e "CREATE DATABASE {}"'''.format(user, pw, db_name)
    res = subprocess.call(cmd, shell=True)
    return None

def load_sql_dump(file, course, run, pw = 'root', user = 'root', db_name = DATABASE_NAME):
    command = '''mysql -u {} -p{} {} < /input/{}/{}/{}'''.format(user, pw, db_name, course, run, file)
    res = subprocess.call(command, shell=True)
    return


def load_sql_dumps(course, session):
    sql_dir = '/input/{}/{}/'.format(course, session)
    sql_files = [x for x in os.listdir(sql_dir) if re.search('\.sql$', x)]
    for file in sql_files:
        load_sql_dump(file, course, session)
    return


def execute_mysql_query(query):
    """
    Executes a mySQL query. This is a simple function but saves MANY repeated lines of code.
    :param query: Text of query to execute.
    :return:
    """
    command = '''mysql -u root -proot course -e"{}"'''.format(query)
    print("[INFO] executing mySQL query {}".format(query))
    res = subprocess.call(command, shell=True)
    return None


def execute_mysql_query_into_csv(query, file):
    """
    Execute mysql query into file, by first writing to a temporary location and moving the results to location at file.
    Note that query should NOT end with semicolon because additional information is appended onto csv.
    :return:
    """
    filename = os.path.basename(file)
    temp_fp = os.path.join(MYSQL_DEFAULT_OUTPUT_DIR, filename)
    query_suffix = """ INTO OUTFILE '{}' FIELDS TERMINATED BY ',' ENCLOSED BY '\\"' ESCAPED BY '\' ;  """.format(temp_fp)
    # check to ensure query doesnt end with semicolon
    if query.endswith(";"):
        query = query[:-1]
    # execute the query into a temporary location
    execute_mysql_query(query + query_suffix)
    # move the result into the desired location
    shutil.move(temp_fp, file)
    return


def extract_forum_text_csv_from_sql(course, session, outdir='/output'):
    """
    Execute queries to generate discussion forum CSVs needed for downstream extraction.
    :return:
    """
    # execute queries to dump info into text files
    # forum text
    csvname = '{}_{}_forum_text.csv'.format(course, session)
    outfile = os.path.join(outdir, csvname)
    query = """SELECT 'id', 'thread_id', 'post_time', 'user_id', 'votes', 'post_text', 'session_user_id', 'post_type' UNION ALL SELECT * FROM (SELECT * FROM (SELECT id , a.thread_id , a.post_time , a.user_id , a.votes , REPLACE(a.post_text, '\\"', '') as post_text , b.session_user_id , 'forum_post' as post_type FROM forum_posts as a LEFT JOIN hash_mapping as b ON a.user_id = b.user_id WHERE is_spam != 1 ) as temp1 UNION ALL ( SELECT id, a.thread_id, a.post_time, a.user_id, a.votes, REPLACE(a.comment_text, '\\"', '') AS post_text, b.session_user_id, 'forum_comment' AS post_type FROM forum_comments AS a LEFT JOIN hash_mapping AS b ON a.user_id = b.user_id WHERE a.is_spam != 1 ORDER BY post_time)) AS temp2 """
    execute_mysql_query_into_csv(query, outfile)
    return


def extract_quiz_csv_from_sql(course, session, outdir):
    quiz_csvname = '{}_{}_quiz.csv'.format(course, session)
    quiz_meta_csvname = '{}_{}_quiz_metadata.csv'.format(course, session)
    # quiz
    query = """SELECT 'item_id', 'session_user_id', 'submission_time', 'submission_number', 'raw_score', 'open_time', 'soft_close_time', 'hard_close_time', 'maximum_submissions', 'quiz_type' UNION ALL SELECT * FROM (SELECT a.item_id ,a.session_user_id ,a.submission_time ,a.submission_number ,a.raw_score ,b.open_time ,b.soft_close_time ,b.hard_close_time ,b.maximum_submissions ,b.quiz_type FROM quiz_submission_metadata as a JOIN quiz_metadata as b on a.item_id = b.id where parent_id = -1 AND grading_error = 0 order by a.item_id, a.session_user_id, a.submission_time) AS temp2 """
    execute_mysql_query_into_csv(query, os.path.join(outdir, quiz_csvname))
    # quiz meta
    query = """SELECT 'id', 'parent_id', 'open_time', 'soft_close_time', 'hard_close_time', 'maximum_submissions', 'duration', 'quiz_type', 'proctoring_requirement', 'authentication_required', 'deleted', 'last_updated' UNION ALL SELECT * FROM (SELECT id, parent_id, open_time, soft_close_time, hard_close_time, maximum_submissions, duration, quiz_type, proctoring_requirement, authentication_required, deleted, last_updated FROM quiz_metadata WHERE parent_id = -1 AND open_time IS NOT NULL AND deleted = 0) AS temp2 """
    execute_mysql_query_into_csv(query, os.path.join(outdir, quiz_meta_csvname))
    return
