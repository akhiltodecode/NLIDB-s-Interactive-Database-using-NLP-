from nltk import load_parser
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords, state_union

import re

supported_questions_str_list = ['what','which','how','who']
sen_words = ['between', 'not', 'do']

stop_words = set(stopwords.words("english"))

class Parse(object):

    def parse_sentence(parser_grammer, sent, trace = 0):
        try:
            # 1- if it's a sentence else throw exceptions
            if is_question(sent) < 1:
                return  Exception("Only one questions is allowed, and should be asked using ",supported_questions_str_list,", questions types")
            # 2- senitize it
            sent = senitize_question(sent)
            # More Senitize by removing stop words
            words = word_tokenize(sent)
            sent = ' '.join([w for w in words if not w in stop_words or w in supported_questions_str_list or w in sen_words])

            # 3- parse it
            cp = load_parser(parser_grammer, trace)
            trees = list(cp.parse(sent.split()))

            answer = trees[0].label()['SEM']
            answer = [s for s in answer if s ]

            q = ' '.join(answer)
        except IndexError as e:
            raise e
        return q    # string return 



    def organize_sql_statment(sent):
        try:
            sent = sent.replace(" (","(") # Fix min max indexing i.e. MAX (value) raise error.. should be MAX(value)
        except ValueError as e:
            raise e
        qq = re.split("(BREAK_S | BREAK_F | BREAK_W)", sent)


        sen_s = 'SELECT '
        sen_f = 'FROM '
        sen_w = 'WHERE '
        bool_w = False # To check if there is a where clause or not

        for item in qq:
            if 'select' in item.lower():
                sen_s += item.lower().replace('select','')+', '
            elif 'from' in item.lower():
                sen_f += str(item.lower().replace('from',''))+', '
            elif 'where' in item.lower():
                bool_w = True
                sen_w += str(item.lower().replace('where',''))+' and '
        if bool_w:
            sql_query = sen_s[:-2]+' '+sen_f[:-2]+' '+sen_w[:-4]
            if 'TMP_1'.lower() in sql_query.lower():
                sql_query = sql_query.replace('TMP_1'.lower(), filter(None, sen_f.split(' '))[1].replace(',','') )
        else:
            sql_query = sen_s[:-2]+' '+sen_f[:-2]
        if 'max' in sql_query.lower():
            tmp = re.split('(\(|\))', sql_query)
            value = tmp[2]
            tmp = tmp[0] +''+tmp[-1]
            if ',' in tmp:
                comma = ','
            else:
                comma = ''
            sql_query = tmp.lower().replace('max', value+comma) + ' order by '+value+' DESC limit 1'
        if 'min' in sql_query.lower():
            tmp = re.split('(\(|\))', sql_query)
            value = tmp[2]
            tmp = tmp[0] +''+tmp[-1]
            if ',' in tmp:
                comma = ','
            else:
                comma = ''
            sql_query = tmp.lower().replace('min', value+comma)+ ' order by '+value+' ASC limit 1'

        return sql_query

        # '''
        # Senitize question from:
        #     * 's clauses
        #     * ?
        # Takes WH sentense and return the sentense after stripping off unwanted charcters
        # # Note only support the supported questions strings
        # SELECT  salary, first_name, last_name, employees.emp_no FROM  salaries,  employees WHERE   employees.emp_no = salaries.emp_no  order by salary desc limit 1
        # '''
    def senitize_question(sent):
        sent = sent.replace('?', '').replace("\'s","").replace("\'re","").replace("\n't"," not ")
        return sent

    def is_question(sent):
        words = word_tokenize(sent)
        is_q = [w for w in words if w.lower() in supported_questions_str_list ]
        number_of_questions = len(is_q)
        if number_of_questions < 1: # Not a question.. Should start with the supported questions format only
            return -1
        elif number_of_questions > 1: # More than one question
            return 0
        return 1




    # Main

    parser_grammer = 'grammars/extends.fcfg'


    def parse_sent(sent):
        try:
            output = organize_sql_statment(parse_sentence(parser_grammer ,sent))
        except Exception  as e:
            # print '*'*30
            # print str(e)
            raise e
        return output



