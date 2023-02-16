from pymarc import Record, MARCReader
import pandas as pd
from pymarc.field import Field
from datetime import datetime
import re
import random

my_marc_file="data/czech_translations_full_18_01_2022.mrc"
# list of identifiers
identifiers = []

# dictionary with author - work:id pairs
dict_author_work = {}
with open(my_marc_file, 'rb') as data:
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
#print(dict_author_work)    



IN = 'Bibliografie_prekladu.csv'
OUT = 'data/marc_it.mrc'

df = pd.read_csv(IN, encoding='utf_8')

italian_articles =  ['il', 'lo', 'la', 'gli', 'le', 'i', 'l\'', 'un', 'una', 'uno', 'un\'', 'dei', 'degli', 'delle']

def add_008(row, record):
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
    if code is None:
        return None
    rand_number = str(random.randint(1000,9999))
    ret = "ubc"+code[0:4]+str(code[-2:])+rand_number
    while ret in identifiers:
        rand_number = str(random.randint(1000,9999))
        ret = "ubc"+code[0:4]+str(code[-2:])+rand_number
    return ret  

def add_595(record, row, author, code):
    work = str(row['Původní název'])
    while work[0] == '\n':  
        work = work[1:]
    while work[0] == ' ':  
        work = work[1:] 
    while work[-1] == ' ':
        work = work[0:-1]    
    if author is None:
        if not(pd.isnull(row['Původní název'])):  
            record.add_ordered_field(Field(tag='595', indicators = ['1', '2'], subfields = ['t', work  ]))                                                                         
    else:
        if not author.lower() in dict_author_work.keys():
            if ("originál neznámý" in work.lower())  or ("originál neexistuje" in work.lower()):
                id = None  
            else:
                id = generate_id(code)          
        else:
            
            dict_works = dict_author_work[author.lower()]
            if work.lower() in dict_works.keys():
                id = dict_works[work.lower()]
            else:
                if ("originál neznámý" in work.lower())  or ("originál neexistuje" in work.lower()):
                    id = None  
                else:
                    id = generate_id(code)  
        if code is None:
            record.add_ordered_field(Field(tag='595', indicators = ['1', '2'], subfields = ['a', author, 
                                                                            't', work  ]))
        else:  
            if id is None:
                record.add_ordered_field(Field(tag='595', indicators = ['1', '2'], subfields = ['a', author, 
                                                                            '7', str(code),
                                                                            't', work ]))  
            else:
                record.add_ordered_field(Field(tag='595', indicators = ['1', '2'], subfields = ['a', author, 
                                                                            '7', str(code),
                                                                            't', work ,
                                                                            '1', id ]))                                                                                                                                  
                                                                          
def add_773(record, row):
    data = row['Údaje o časopiseckém vydání']
    print("Údaje o časopiseckém vydání", data)
    comma = data.find(',') 
    
    if not comma == -1:
        magazine = data[:comma]
        rest = data[comma+1:]
        author = record['100']['a']
        print("author: ", author)
        year = row['Rok']
        if not pd.isnull(row['Překladatel/ka']): 
            translator = row['Překladatel/ka']
            print("translator: ", translator) 
            record.add_ordered_field(Field(tag='773', indicators = ['0', ' '], subfields = ['t', magazine, 
                                                                            'a', author ,
                                                                            'n', translator,
                                                                            'g', rest ]))
        else:                                                                    
            record.add_ordered_field(Field(tag='773', indicators = ['0', ' '], subfields = ['t', magazine, 
                                                                            'a', author ,
                                                                            'g', rest ]))
    




def add_author_code(data, record):
    if not(pd.isnull(data)):
        start = data.find('(')
        end = data.find(')') 
        if start == -1:
            record.add_ordered_field(Field(tag='100', indicators=['1',' '], subfields=['a', data, 
                                                                                '4', 'aut']))
            return (data, None)
        author = re.search('.*(?=\s+\()', data).group(0)
        if author[0] == " ":
            author = author[1:-1]
        code = data[start+1: end]
        record.add_ordered_field(Field(tag='100', indicators=['1',' '], subfields=['a', author,
                                                                                '7', code, 
                                                                                '4', 'aut']))
        return (author, code)
    else:
        return (None, None)

def get_title_subtitle(data):
    while data[0] == "\n":
        data = data[1:] 
    while data[0] == ' ':  
        data = data[1:] 
    while data[-1] == ' ':
        data = data[0:-1]
    split = data.find(':')
    if split == -1:
        return (data, '' )
    else:
        title = data[:split]
        subtitle = data[split+1:]
        while title[-1] == ' ':
            title = title[0:-1] 
        while subtitle[0] == ' ':
            subtitle = subtitle[1:]         
        return(title, subtitle)   

def add_264(row, record):
    if pd.isnull(row['Město vydání, země vydání, nakladatel']):
        return record    
    city_country_publisher = row['Město vydání, země vydání, nakladatel']
    while True:
        city =  re.search('^[\w\s]+', city_country_publisher).group(0)
        if '§' in city_country_publisher:
            start = city_country_publisher.find('§') 
            publisher = re.search('(?<=\:\s).+', city_country_publisher[:start]).group(0)
            year = row['Rok'] 
            record.add_ordered_field(Field(tag = '264', indicators = [' ', '1'], subfields = ['a', city + ':', 
                                                                            'b', publisher, 
                                                                            'c', str(int(year))]))
            city_country_publisher = city_country_publisher[start + 1: ]
           
        else:
            break    
    publisher = re.search('(?<=\:\s)[\w\s]+', city_country_publisher).group(0)
    year = row['Rok']
    record.add_ordered_field(Field(tag = '264', indicators = [' ', '1'], subfields = ['a', city + ':', 
                                                                            'b', publisher + ',',
                                                                            'c', str(int(year)) ]))    

def add_translator(translators, record):
    while '§' in translators:
            start = translators.find('§') 
            t = re.search('\w+', translators[:start ]).group(0)  
            record.add_ordered_field(Field(tag='700', indicators=['1',' '], subfields=['a', t,
                                                                                        '4', 'trl'])) 
            translators = translators[start+1:]
    t = re.search('\w+', translators).group(0)        
    record.add_ordered_field(Field(tag='700', indicators=['1',' '], subfields=['a', t,
                                                                                        '4', 'trl']))

def add_245(liability, title, subtitle,  record):
    
    if title[0:2].lower() == 'l\'':
        skip = str(2)
        
    first_word = re.search('^([\w]+)', title)
    if not first_word is None: 
        first_word = re.search('^([\w]+)', title).group(0)
        if first_word.lower() in italian_articles:
            skip = str(len(first_word))
        else:
            skip = str(0)    
    else:
        skip = str(0)

    if subtitle == '' and pd.isnull(liability):                                                                          
        record.add_ordered_field(Field(tag = '245', indicators = ['1', skip], subfields = ['a', title]))                                                                          
    else:
        if pd.isnull(liability):
            record.add_ordered_field(Field(tag = '245', indicators = ['1', skip], subfields = ['a', title + " : ", 
                                                                                    'b', subtitle]))
        elif subtitle == '':     
            record.add_ordered_field(Field(tag = '245', indicators = ['1', skip], subfields = ['a', title, 
                                                                                    'c', liability]))
        else:
            record.add_ordered_field(Field(tag = '245', indicators = ['1', skip], subfields = ['a', title + " : ",
                                                                                    'b', subtitle + " / ", 
                                                                                    'c', liability]))


def add_commmon(row, record, author, code):
    record.add_ordered_field(Field(tag='001', indicators = [' ', ' '], data=str('it22'+ "".join(['0' for a in range(6-len(str(row['Číslo záznamu'])))]) + str(row['Číslo záznamu'])))) 
    record.add_ordered_field(Field(tag='003', indicators = [' ', ' '], data='CZ PrUCL')) # institution
    
    
    # ISBN
    if not(pd.isnull(row['ISBN'])):
        record.add_ordered_field(Field(tag='020', indicators=[' ',' '], subfields=['a', str(row['ISBN'])] )) 

    record.add_ordered_field(Field(tag='040', indicators=[' ',' '], subfields=['a', 'ABB060',
                                                                               'c', 'cze',
                                                                               'e', 'rda']))
    if  pd.isnull(row['Zprostředkovací jazyk']):                                                                          
        record.add_ordered_field(Field(tag='041', indicators=['1',' '],subfields=['a', re.search('[^\s]+', str(row['Jazyk díla'])).group(0),
                                                                             'h', re.search('[^\s]+', str(row['Výchozí jazyk '])).group(0)])) 
    else:
        record.add_ordered_field(Field(tag='041', indicators=['1',' '],subfields=['a', re.search('[^\s]+', str(row['Jazyk díla'])).group(0),
                                                                             'h', re.search('[^\s]+', str(row['Výchozí jazyk '])).group(0),
                                                                             'k', re.search('[^\s]+', str(row['Zprostředkovací jazyk'])).group(0)]) )
    if not(pd.isnull(row['Původní název'])) and ("originál neznámý" in str(row['Původní název']).lower())  or ("originál neexistuje" in str(row['Původní název']).lower()):
        original_name = row['Původní název']
        while original_name[0] == "\n":
            original_name = original_name[1:] 
        while original_name[0] == ' ':  
            original_name = original_name[1:] 
        while original_name[-1] == ' ':
            original_name = original_name[0:-1]                                                                          
        record.add_ordered_field(Field(tag='240', indicators = ['1', '0'], subfields = ['a', original_name , 
                                                                              '1', 'italsky' ]))
    else: 
        record.add_ordered_field(Field(tag='240', indicators = ['1', '0'], subfields = [ '1', 'italsky' ]))    

    (title, subtitle) = get_title_subtitle(str(row['Název díla dle titulu (v příslušném písmu)']))
    liabiliy = row['Údaje o odpovědnosti a další informace']
    add_245(liabiliy, title, subtitle, record)
    add_595(record, row, author, code)  

    if not(pd.isnull(row['Překladatel/ka'])):
        add_translator(row['Překladatel/ka'], record ) 
        
    record.add_ordered_field(Field(tag = '910', indicators=[' ', ' '], subfields=['a', 'ABB060' ] ) )
    record.add_ordered_field(Field(tag = '964', indicators=[' ', ' '], subfields=['a', 'TRL' ] ) )

    record.add_ordered_field(Field(tag = 'OWN', indicators = [' ', ' '], subfields = ['a', 'UCLA']))

def create_record_part_of_book(row, df):
    record = Record(to_unicode=True,
        force_utf8=True)
    #print(row['Číslo záznamu'])
    record.leader = '-----naa----------------'  
    ind = int(row['Je součást čeho (číslo záznamu)'])
    book_row = df.loc[df['Číslo záznamu'] == ind]
    tup = add_author_code(book_row['Autor/ka + kód autority'].values[0], record)
    author = tup[0] 
    code = tup[1]
    # From Dataframe to Pandas Series
    book_row = book_row.squeeze()
    add_008(book_row, record)
    add_264(book_row, record)
    add_commmon(row, record, author, code)  

    return record


def create_record_book(row):
    record = Record(to_unicode=True,
        force_utf8=True)

    #print(row['Číslo záznamu']
    record.leader = '-----nam----------------'
    tup = add_author_code(row['Autor/ka + kód autority'], record)
    author = tup[0]
    code = tup[1]
    add_008(row, record)
    add_commmon(row, record, author, code)      
    add_264(row, record)
    if not(pd.isnull(row['Počet stran'])):
        record.add_ordered_field(Field(tag = '300', indicators=[' ', ' '], subfields=['a', str(int(row['Počet stran'])) + ' p.'  ]))                                                                             
                                                                             
    if not(pd.isnull(row['technická poznámka'])):
        record.add_ordered_field(Field(tag='506', indicators = [' ', ' '], data = row['technická poznámka']))

    if not(pd.isnull(row['Zdroj či odkaz'])):
          record.add_ordered_field(Field(tag = '998', indicators=[' ', ' '], subfields=['a', row['Zdroj či odkaz'] ] ) )
    
    return record

def create_article(row):
    record = Record(to_unicode=True,
        force_utf8=True)
    record.leader = '-----nab----------------' 
    tup = add_author_code(row['Autor/ka + kód autority'], record)
    author = tup[0]
    code = tup[1]
    add_008(row, record) 
    add_commmon(row, record, author, code)
    add_773(record, row)


    if not(pd.isnull(row['Počet stran'])):
        record.add_ordered_field(Field(tag = '300', indicators=[' ', ' '], subfields=['a', str(int(row['Počet stran'])) ]))                                                                             
                                                                             
    if not(pd.isnull(row['technická poznámka'])):
        record.add_ordered_field(Field(tag='506', indicators = [' ', ' '], data = row['technická poznámka']))

    if not(pd.isnull(row['Zdroj či odkaz'])):
          record.add_ordered_field(Field(tag = '998', indicators=[' ', ' '], subfields=['a', row['Zdroj či odkaz'] ] ) )

    return record 




with open(OUT , 'wb') as writer:
    for index, row in df.iterrows():
        print(row['Číslo záznamu'])
        if 'kniha' in row['Typ záznamu']: 
            record = create_record_book(row)
        if 'část knihy' in row['Typ záznamu']: 
            record = create_record_part_of_book(row, df)
        if 'článek v časopise' in row['Typ záznamu']:
            record = create_article(row)
            print(record)
        writer.write(record.as_marc())


writer.close()

