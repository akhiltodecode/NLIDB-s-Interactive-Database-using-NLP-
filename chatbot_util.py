

from __future__ import print_function

from nltk import load_parser
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords, state_union

import re
import random

from six.moves import input
from tkinter import *
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

import mySql_demon 

supported_questions_str_list = ['what','which','how','who']
sen_words = ['between', 'not', 'do']

stop_words = set(stopwords.words("english"))

reflections = {
  "i am"       : "you are",
  "i was"      : "you were",
  "i"          : "you",
  "i'm"        : "you are",
  "i'd"        : "you would",
  "i've"       : "you have",
  "i'll"       : "you will",
  "my"         : "your",
  "you are"    : "I am",
  "you were"   : "I was",
  "you've"     : "I have",
  "you'll"     : "I will",
  "your"       : "my",
  "yours"      : "mine",
  "you"        : "me",
  "me"         : "you"
}

class Chat(object): 
    def __init__(self, pairs, reflections={}):

        # DB Connection
        self.db = mySql_demon.DB()
        self._keywords = ['name']
        self._data_arr = []
        self._pairs = [(re.compile(x, re.IGNORECASE),y) for (x,y) in pairs]
        self._reflections = reflections
        self._regex = self._compile_reflections()
        
        
    parser_grammer = 'grammars/extends.fcfg'
    
    def parse_sentence(self, parser_grammer, sent, trace = 0):
        try:
            # 1- if it's a sentence else throw exceptions
            if self.is_question(sent) < 1:
                return  Exception("Only one questions is allowed, and should be asked using ",supported_questions_str_list,", questions types")
            # 2- senitize it
            sent = self.senitize_question(sent)
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



    def organize_sql_statment(self, sent):
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
    def senitize_question(self, sent):
        sent = sent.replace('?', '').replace("\'s","").replace("\'re","").replace("\n't"," not ")
        return sent

    def is_question(self, sent):
        words = word_tokenize(sent)
        is_q = [w for w in words if w.lower() in supported_questions_str_list ]
        number_of_questions = len(is_q)
        if number_of_questions < 1: # Not a question.. Should start with the supported questions format only
            return -1
        elif number_of_questions > 1: # More than one question
            return 0
        return 1




    # Main

    


    def parse_sent(self, sent):
        try:
            output = self.organize_sql_statment(self.parse_sentence(self.parser_grammer ,sent))
        except Exception  as e:
            # print '*'*30
            # print str(e)
            raise e
        return output




    def _compile_reflections(self):
        sorted_refl = sorted(self._reflections.keys(), key=len,
                reverse=True)
        return  re.compile(r"\b({0})\b".format("|".join(map(re.escape,
            sorted_refl))), re.IGNORECASE)

    def _substitute(self, str):
        """
        Substitute words in the string, according to the specified reflections,
        e.g. "I'm" -> "you are"

        :type str: str
        :param str: The string to be mapped
        :rtype: str
        """

        return self._regex.sub(lambda mo:
                self._reflections[mo.string[mo.start():mo.end()]],
                    str.lower())

    def _wildcards(self, response, match, sent = ''):
        pos = response.find('%')
        while pos >= 0:
            num = int(response[pos+1:pos+2])
            response = response[:pos] + \
                self._substitute(match.group(num)) + \
                response[pos+2:]
            pos = response.find('%')
        if len(self._data_arr) > 0:
            response = response.replace('##username##', self._data_arr[0])
            if self.is_question(sent) > 0:
                try:
                    sql_statment = self.parse_sent(sent)
                    response = response.replace('##sql_statment##', sql_statment)
                    response = response.replace('##sql_result##', self.db.query_pretty(sql_statment))
                    
                except Exception as e:
                   # response = str('That seems off topic! Please type help to see some questions that I can help with.')
                    response = str(e)
            
        else:
            response = "Please Enter your name using the format name {your name}. Example: name John Due"
        return response

    def respond(self, str):

        # Store user input
        if any(x in str for x in self._keywords):
            self._data_arr.append(str.replace('name', ''))
        # check each pattern
        for (pattern, response) in self._pairs:
            match = pattern.match(str)

            # did the pattern match?
            if match:
                resp = random.choice(response)    # pick a random response
                resp = self._wildcards(resp, match, str) # process wildcards

                # fix munged punctuation at the end
                if resp[-2:] == '?.': resp = resp[:-2] + '.'
                if resp[-2:] == '??': resp = resp[:-2] + '?'
                return resp

    # Hold a conversation with a chatbot -- USING GUI Interface
    def get_input(self, event):
        try: user_input = self.entry.get()
        except EOFError:
            print(user_input)
        if user_input.lower() == "quit":
            sys.exit(0)
        elif user_input:
                while user_input[-1] in "!.": user_input = user_input[:-1]
                response = self.respond(user_input)
                self.textPad.insert(END, "\nYou > "+user_input+"\nChatbot > " + str(response) + "\n")
                self.textPad.see(END)
                self.entry.delete(0, 'end')
                response = ''
                user_input = ''
        if response != None:
            response = ''
            user_input = ''
       
    def converse(self, quit="quit"):
        self.root = Tk(className=" NLP To SQL (QA)")
  
        # --- put frame in canvas ---
        width_window, height_window = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry('%dx%d+0+0' % (width_window,height_window))

        # Scroll text Model
        self.entry = Entry(self.root,  width=width_window)
        
        self.entry.bind("<Return>", self.get_input)
        self.entry.pack(side = BOTTOM, ipady=10 )

        self.textPad = ScrolledText(self.root, width=width_window, height = height_window)
        self.textPad.pack(side="left", fill="both", expand=True)

        self.textPad.insert(INSERT, "NLIDB database QA System\n--------")
        self.textPad.insert(INSERT, "\nTalk to the program by typing in plain English, using normal upper-")
        self.textPad.insert(INSERT, "\nand lower-case letters and punctuation.  Enter 'quit' when done.\n")
        self.textPad.insert(INSERT, '='*72)
        self.textPad.insert(INSERT, "\n\nChatbot >Please Enter your name using the format name {your name}. Example: name John Due")

        self.root.mainloop()

