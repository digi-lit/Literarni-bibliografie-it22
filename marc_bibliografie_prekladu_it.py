# -----------------------------------------------------------
# Script that transforms data from a table to a marc file
# The table consists of information about the Italian translations of the Czech books
# Written for the ČLB ÚČL AV ČR
#
# (C) 2023 Charlotte Panušková, Prague, Czechia
# email charlottepanuskova@gmail.com
# -----------------------------------------------------------

from pymarc import Record, MARCReader
import pandas as pd
from pymarc.field import Field
from datetime import datetime
import re
import random

# file with all czech translations and their id's 
czech_translations="data/czech_translations_full_18_01_2022.mrc"
# list of identifiers
identifiers = []
# dictionary with author - work:id pairs
dict_author_work = {}

# saves data from czech_translations file to dictionary dict_author_work  
with open(czech_translations, 'rb') as data:
    reader = MARCReader(data, to_unicode=True, force_utf8=True, utf8_handling="strict")
    for record in reader:
        if not record is None:
            if not record['595'] is None: 
                id = record['595']['1']
                if not id in identifiers:
                    identifiers.append(id)
                author = record['595']['a']
                author = author[0:len(author)-1]
                work = record['595']['t']
                if not work is None: 
                    if work[-1] == '.':
                        work = work[0:len(work)-1]
                    if author.lower() in dict_author_work.keys():
                        dict_author_work[author.lower()].update({work.lower() : id })  
                    else:
                        dict_author_work[author.lower()] = {work.lower() : id }
# initial table 
IN = 'Bibliografie_prekladu.csv'
# final file
OUT = 'data/marc_it.mrc'

df = pd.read_csv(IN, encoding='utf_8')

# table with authority codes
finalauthority_path = 'data/finalauthority_simple.csv'
finalauthority = pd.read_csv(finalauthority_path,  index_col=0)
finalauthority.index= finalauthority['nkc_id']

# list of italian articles for field 245 
italian_articles =  ['il', 'lo', 'la', 'gli', 'le', 'i', 'un', 'una', 'uno', 'dei', 'degli', 'delle']

def delete_whitespaces(string):
    """Method for deleting unnecessary spaces and new lines in strings"""   
    while string[0] == '\n' or string[0] == ' ':  
        string = string[1:]
    while string[-1] == '\n' or string[-1] == ' ': 
        string = string[0:-1]
    return string    


def add_008(row, record):
    """Creates fixed length data and adds them to field 008 """ 
    date_record_creation = str(datetime.today().strftime('%y%m%d'))
    letter = 's'

    if pd.isnull(row['Rok']):
        publication_date = '--------'
    else:
        publication_date = str(int(row['Rok']))+ '----' 

    if pd.isnull(row['Město vydání, země vydání, nakladatel']):
        publication_country = 'xx-'

    else:
        publication = row['Město vydání, země vydání, nakladatel'] 
        start = publication.find('(')+1
        end = publication.find(')') 
        country = publication[start:end]
        if country == 'Itálie':
            publication_country = 'it-'
        elif country == 'Česká republika':
            publication_country = 'xr-'    
        else:
            publication_country = 'xx-'

    material_specific =  '-----------------'
    language = 'ita'
    modified = '-'
    cataloging_source = 'd'
    data = date_record_creation + letter + publication_date +  publication_country + material_specific + language + modified + cataloging_source
    record.add_ordered_field(Field(tag='008', indicators = [' ', ' '], data = data))

def generate_id(code):
    """Generates 11 positional id for field 595. 
    In case there is no authority code, id is random.
    Otherwise generates id from the authority code.""" 
    ID_LENGTH = 11
    if code is None:
        rand_number = str(random.randint(00000000000,99999999999))
        # in case random number has less than 11 positions, add zeros at the beginning
        if len(rand_number) < ID_LENGTH:
            for i in range(ID_LENGTH-len(rand_number)):
                rand_number = "0" + rand_number
        return "ubc"+rand_number
    rand_number = str(random.randint(1000,9999))
    ret = "ubc"+code[0:4]+str(code[-2:])+rand_number
    # in case generated id already exists, create a new one
    while ret in identifiers:
        rand_number = str(random.randint(1000,9999))
        ret = "ubc"+code[0:4]+str(code[-2:])+rand_number
    return ret  

def add_595(record, row, author, code):
    """Adds data to field 595. 
    Consists of author's name in subfield 'a', birth (and death) year in subfield 'd'
    author's code in subfield '7', original title of the work in subfield 't' and generated id in subfield 't'""" 
    original_work_title = delete_whitespaces(str(row['Původní název']))   
    if author is None:
        if not(pd.isnull(row['Původní název'])):  
            record.add_ordered_field(Field(tag='595', indicators = ['1', '2'], subfields = ['t', original_work_title  ]))                                                                         
    else:
        if not code is None:
            if code in finalauthority.index:
                    date = str(finalauthority.loc[code]['cz_dates' ]) 
            else:
                date = None        
        else:
            date = None            
            id = generate_id(code)
        if not author.lower() in dict_author_work.keys():
            if ("originál neznámý" in original_work_title.lower())  or ("originál neexistuje" in original_work_title.lower()):
                id = None  
            else:
                id = generate_id(code)          
        else:
            dict_works = dict_author_work[author.lower()]
            if original_work_title.lower() in dict_works.keys():
                id = dict_works[original_work_title.lower()]
            else:
                if ("originál neznámý" in original_work_title.lower())  or ("originál neexistuje" in original_work_title.lower()):
                    id = None  
                else:
                    id = generate_id(code) 
           
        if code is None:
            record.add_ordered_field(Field(tag='595', indicators = ['1', '2'], subfields = ['a', author, 
                                                                            't', original_work_title  ]))
        else: 
            if date is None: 
                if id is None:
                    record.add_ordered_field(Field(tag='595', indicators = ['1', '2'], subfields = ['a', author,
                                                                            '7', str(code),
                                                                            't', original_work_title ])) 
                else:
                    record.add_ordered_field(Field(tag='595', indicators = ['1', '2'], subfields = ['a', author,
                                                                            '7', str(code),
                                                                            't', original_work_title ,
                                                                            '1', id ]))                                                             
            else:
                if id is None:
                    record.add_ordered_field(Field(tag='595', indicators = ['1', '2'], subfields = ['a', author,
                                                                            'd', date, 
                                                                            '7', str(code),
                                                                            't', original_work_title ]))
                else:                                                            
                    record.add_ordered_field(Field(tag='595', indicators = ['1', '2'], subfields = ['a', author,
                                                                            'd', date, 
                                                                            '7', str(code),
                                                                            't', original_work_title ,
                                                                            '1', id ]))   
             
def add_773(record, row):
    """Adds data to field 773. Only for magazines.
    Consists of jurnal issue data. 
    In subfield 't' magazine's title, in subfield 'g' additional magazine data, in subfield '9' year of publication
    """ 
    data = row['Údaje o časopiseckém vydání']
    comma = data.find(',') 
    if not comma == -1:
        magazine = data[:comma]
        rest = delete_whitespaces(data[comma+1:])
        year = str(row['Rok'])
        record.add_ordered_field(Field(tag='773', indicators = ['0', ' '], subfields = ['t', magazine, 
                                                                            'g', rest,
                                                                            '9', year ]))
                                                                    

def add_author_code(data, record):
    """Adds authors name and code into field 100.
    Also returns author's name and code as a tuple.
    """ 
    if not(pd.isnull(data)):
        start = data.find('(')
        end = data.find(')') 
        if start == -1:
            record.add_ordered_field(Field(tag='100', indicators=['1',' '], subfields=['a', delete_whitespaces(data), 
                                                                                '4', 'aut']))
            return (data, None)
        # matches everything before '(' character 
        author = delete_whitespaces(re.search('.*(?=\s+\()', data).group(0))
        code = delete_whitespaces(data[start+1: end])
        if code in finalauthority.index:
                date = str(finalauthority.loc[code]['cz_dates' ]) 
                record.add_ordered_field(Field(tag='100', indicators=['1',' '], subfields=['a', author,
                                                                                'd', date,
                                                                                '7', code, 
                                                                                '4', 'aut']))    
        else:
                date = None  
                record.add_ordered_field(Field(tag='100', indicators=['1',' '], subfields=['a', author,
                                                                                '7', code, 
                                                                                '4', 'aut']))
        return (author, code)
    else:
        return (None, None)

def get_title_subtitle(data):
    """Splits work's title into title and subtitle.
    Returns as tuple.
    """
    data = delete_whitespaces(data)
    split = data.find(':')
    if split == -1:
        return (data, '' )
    else:
        title = data[:split]
        subtitle = data[split+1:]
        title = delete_whitespaces(title)
        subtitle = delete_whitespaces(subtitle)         
        return(title, subtitle)   

def add_264(row, record):
    """Adds data to subfield 264. 
    Consists of city of publication, coutry of publications and the publisher
    """
    if pd.isnull(row['Město vydání, země vydání, nakladatel']):
        return record    
    city_country_publisher = row['Město vydání, země vydání, nakladatel']
    while True:
        # matches first words in string 
        city =  re.search('^[\w\s]+', city_country_publisher).group(0)
        if '§' in city_country_publisher:
            # finds position of character §
            start = city_country_publisher.find('§') 
            # finds the character ":" a matches everything behind it 
            publisher = re.search('(?<=\:\s).+', delete_whitespaces(city_country_publisher[:start])).group(0)
            year = row['Rok'] 
            record.add_ordered_field(Field(tag = '264', indicators = [' ', '1'], subfields = ['a', city + ':', 
                                                                            'b', publisher, 
                                                                            'c', str(int(year))]))
            city_country_publisher = city_country_publisher[start + 1: ]
           
        else:
            break    
    # finds the character ":" a matches everything behind it     
    publisher = re.search('(?<=\:\s).+', city_country_publisher).group(0)
    year = row['Rok']
    record.add_ordered_field(Field(tag = '264', indicators = [' ', '1'], subfields = ['a', city + ':', 
                                                                            'b', publisher + ',',
                                                                            'c', str(int(year)) ]))    

def add_translator(translators, record):
    """Adds translators to field 700.
    In case there are more than 1 translator, multiplies field 700.
    """
    # iterates through all iteraters devided by character §
    while '§' in translators:
            start = translators.find('§') 
            t = delete_whitespaces(translators[:start ])
            record.add_ordered_field(Field(tag='700', indicators=['1',' '], subfields=['a', t,
                                                                                        '4', 'trl'])) 
            translators = translators[start+1:]
    t = delete_whitespaces(translators)        
    record.add_ordered_field(Field(tag='700', indicators=['1',' '], subfields=['a', t,
                                                                                        '4', 'trl']))
def c_245(row, liability,author, translators):
    """Method for creating string used in field 245 subfield c.
    String structure: [Author's name] [Author's name] ; traduzione di [translator's name] [translator's surname] ; liability informations 
    """
    c = ""
    if not pd.isnull(author): 
        # finds the character "," a matches everything ahead it 
        surname = delete_whitespaces(re.search('.*(?=,)', author ).group(0)) 
        # finds the character "," a matches everything behind it
        name = delete_whitespaces(re.search('(?<=\,\s).+', author).group(0))
        c += name + ' ' + surname + ' '
    if not(pd.isnull(translators)):  
        c += '; traduzione di '
        while True:
                # there are more than 1 translator
                if '§' in translators:
                    # finds character §
                    start = translators.find('§') 
                    # finds the character "," a matches everything ahead it 
                    surname = delete_whitespaces(re.search('.*(?=,)', translators[:start] ).group(0)) 
                    # finds the character "," a matches everything behind it 
                    name = delete_whitespaces(re.search('(?<=\,\s).+', translators[:start]).group(0)) 
                    c += name + ' ' +  surname + ' , '
                    translators = translators[start + 1: ]
                else:
                    break 
        # finds the character "," a matches everything ahead it 
        surname = delete_whitespaces(re.search('.*(?=,)', translators ).group(0)) 
        # finds the character "," a matches everything behind it 
        name = delete_whitespaces(re.search('(?<=\,\s).+', translators).group(0))
        c += name + ' ' +  surname 
    if not pd.isnull(liability):
        c += ' ; ' + delete_whitespaces(str(liability))   
    return c    

def add_245(row, liability, title, subtitle, author, translators,  record):
    """Adds data to subfield 245. 
    Finds if work's title starts with an article -> writes how many positions the article takes
    """
    # matches first word in string
    first_word = re.search('^([\w]+)', title)
    if not first_word is None: 
        # matches first word in string
        first_word = re.search('^([\w]+)', title).group(0)
        if first_word.lower() in italian_articles:
            skip = str(len(first_word) + 1)
        else:
            skip = str(0)    
    else:
        skip = str(0)
    if title[0:2].lower() == "l'":
            skip = str(2)
    if title[0:2].lower() == "un'":
            skip = str(3) 
    c = c_245(row, liability, author, translators)  
    title = delete_whitespaces(title)      
    if subtitle == '' and c == '':                                                                          
        record.add_ordered_field(Field(tag = '245', indicators = ['1', skip], subfields = ['a', title]))                                                                          
    else:
        if c == '':
            subtitle = delete_whitespaces(subtitle)
            record.add_ordered_field(Field(tag = '245', indicators = ['1', skip], subfields = ['a', title + " :", 
                                                                                    'b', subtitle]))
        elif subtitle == '':  
            c = delete_whitespaces(c)    
            record.add_ordered_field(Field(tag = '245', indicators = ['1', skip], subfields = ['a', title, 
                                                                                    'c', c]))
        else:
            subtitle = delete_whitespaces(subtitle)
            c = delete_whitespaces(c) 
            record.add_ordered_field(Field(tag = '245', indicators = ['1', skip], subfields = ['a', title + " :",
                                                                                    'b', subtitle + " /", 
                                                                                    'c', c]))


def add_commmon(row, record, author, code, translators):
    """Adds data to fields that are common for all work types 
    """
    record.add_ordered_field(Field(tag='001', indicators = [' ', ' '], data=str('it22'+ "".join(['0' for a in range(6-len(str(row['Číslo záznamu'])))]) + str(row['Číslo záznamu'])))) 
    record.add_ordered_field(Field(tag='003', indicators = [' ', ' '], data='CZ PrUCL')) 
    
    if not(pd.isnull(row['ISBN'])):
        record.add_ordered_field(Field(tag='020', indicators=[' ',' '], subfields=['a', delete_whitespaces(str(row['ISBN']))] )) 

    record.add_ordered_field(Field(tag='040', indicators=[' ',' '], subfields=['a', 'ABB060',
                                                                               'b', 'cze',
                                                                               'e', 'rda']))
    
    if  pd.isnull(row['Zprostředkovací jazyk']):                                                                          
        record.add_ordered_field(Field(tag='041', indicators=['1',' '],subfields=['a', re.search('[^\s]+', str(row['Jazyk díla'])).group(0),
                                                                             'h', re.search('[^\s]+', str(row['Výchozí jazyk '])).group(0)])) 
    else:
        record.add_ordered_field(Field(tag='041', indicators=['1',' '],subfields=['a', re.search('[^\s]+', str(row['Jazyk díla'])).group(0),
                                                                             'h', re.search('[^\s]+', str(row['Výchozí jazyk '])).group(0),
                                                                             'k', re.search('[^\s]+', str(row['Zprostředkovací jazyk'])).group(0)]) )
    
    if not(pd.isnull(row['Původní název'])) and ("originál neznámý" in str(row['Původní název']).lower())  or ("originál neexistuje" in str(row['Původní název']).lower()):
        original_title = delete_whitespaces(row['Původní název'])                                                                        
        record.add_ordered_field(Field(tag='240', indicators = ['1', '0'], subfields = ['a', original_title , 
                                                                              'l', 'italsky' ]))
        
    if not(pd.isnull(row['Počet stran'])) and row['Počet stran'].isnumeric():
        record.add_ordered_field(Field(tag = '300', indicators=[' ', ' '], subfields=['a', str(int(row['Počet stran'])) + ' p.']))
    
    if not(pd.isnull(row['Zdroj či odkaz'])) and not (row['Zdroj či odkaz'] == ' '):
          record.add_ordered_field(Field(tag = '998', indicators=[' ', ' '], subfields=['a', row['Zdroj či odkaz'] ] ) )

    add_595(record, row, author, code)  

    if not(pd.isnull(translators)):
        add_translator(translators, record ) 

    (title, subtitle) = get_title_subtitle(str(row['Název díla dle titulu (v příslušném písmu)']))
    liabiliy = row['Údaje o odpovědnosti a další informace']
    add_245(row, liabiliy, title, subtitle, author, translators,record)    
    record.add_ordered_field(Field(tag = '910', indicators=[' ', ' '], subfields=['a', 'ABB060' ] ) )
    record.add_ordered_field(Field(tag = '964', indicators=[' ', ' '], subfields=['a', 'TRL' ] ) )
    record.add_ordered_field(Field(tag = 'OWN', indicators = [' ', ' '], subfields = ['a', 'UCLA']))

def add_994_book(row, df, record):
    """Adds id's of all parts of the collective work to field 994."""
    cislo_zaznamu = row['Číslo záznamu']
    is_part_of = df['Je součást čeho (číslo záznamu)']==cislo_zaznamu
    if any(is_part_of):
        book_rows = [i for i, val in enumerate(is_part_of) if val]
        sf = ['a', 'DN']
        for i in book_rows:
            sf.append('b')
            r = df.iloc[i]
            sf.append("".join(['0' for a in range(6-len(str(row['Číslo záznamu'])))]) + str(r['Číslo záznamu']))
        record.add_ordered_field(Field(tag = '995', indicators = [' ', ' '], subfields = sf))

def add_995_part_of_book(row, record):
    """Adds id of the collective work to field 995."""
    sf = ['a', 'UP', 'b']   
    is_part_of = str(int(row['Je součást čeho (číslo záznamu)']))
    sf.append("".join(['0' for a in range(6-len(is_part_of))]) + is_part_of)
    record.add_ordered_field(Field(tag = '995', indicators = [' ', ' '], subfields = sf))

def create_record_part_of_book(row, df):
    """Creates record for part of the book.
    Adds all fields that are specific to parts of book"""
    record = Record(to_unicode=True,
        force_utf8=True)
    record.leader = '-----naa---------4i-4500'  
    ind = int(row['Je součást čeho (číslo záznamu)'])
    book_row = df.loc[df['Číslo záznamu'] == ind]
    tup = add_author_code(book_row['Autor/ka + kód autority'].values[0], record)
    author = tup[0] 
    code = tup[1]
    translators = book_row['Překladatel/ka'].values[0]
    # from Dataframe to Pandas Series
    book_row = book_row.squeeze()
    add_008(book_row, record)
    add_264(book_row, record)
    add_commmon(row, record, author, code, translators)  
    add_995_part_of_book(row, record)
    return record


def create_record_book(row, df):
    """Creates record for book.
    Adds all fields that are specific to books"""
    record = Record(to_unicode=True,
        force_utf8=True)
    record.leader = '-----nam---------4i-4500'
    tup = add_author_code(row['Autor/ka + kód autority'], record)
    author = tup[0]
    code = tup[1]
    translators = row['Překladatel/ka']
    add_008(row, record)
    add_commmon(row, record, author, code, translators)      
    add_264(row, record)
    if row['typ díla (celé dílo, úryvek, antologie, souborné dílo)'] == 'souborné dílo':
        add_994_book(row, df, record)     
    return record

def create_article(row):
    """Creates record for the article.
    Adds all fields that are specific to articles."""
    record = Record(to_unicode=True,
        force_utf8=True)
    record.leader = '-----nab---------4i-4500' 
    tup = add_author_code(row['Autor/ka + kód autority'], record)
    author = tup[0]
    code = tup[1]
    translators = row['Překladatel/ka']
    add_008(row, record) 
    add_commmon(row, record, author, code, translators)
    add_773(record, row)
    return record 

# writes data to file in variable OUT
with open(OUT , 'wb') as writer:
    #iterates all rows in the table
    for index, row in df.iterrows():
        print(row['Číslo záznamu'])
        if 'kniha' in row['Typ záznamu']: 
            record = create_record_book(row, df)
        if 'část knihy' in row['Typ záznamu']: 
            record = create_record_part_of_book(row, df)
        if 'článek v časopise' in row['Typ záznamu']:
            record = create_article(row)
        print(record)    
        writer.write(record.as_marc())
writer.close()

