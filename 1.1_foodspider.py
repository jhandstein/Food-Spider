import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup
import ssl
import re
import sqlite3

def article_crawl(baseurl, num):

    url = baseurl + "/" + str(num)
    html = urllib.request.urlopen(url, context=ctx).read()
    print(type(html))
    soup = BeautifulSoup(html, 'html.parser')
    tags = soup('a')

    pagelist = list()

    for tag in tags:
        tag = tag.decode()
        if re.findall('href="(/product[\S]+)"', tag):
            page = baseurl + re.findall('href="(/product[\S]+)"', tag)[0]
            pagelist.append(page)
            # print(i, page)
        else:
            continue
    # print(pagelist)
    return pagelist

def get_attributes(bs4_object):
    scripts = bs4_object.find_all(
        'script', attrs={'type': 'text/javascript'})
    # print('Type scripts:', type(scripts))

    for script in scripts:

        script = script.decode()
        if not re.findall('src',script):
            pass
            # print('Correct tag!')
        else:
            continue

        if re.findall('{.+}', script):
            attr = re.findall('{.+}', script)[0]
            attr_dict = eval(attr)
            # print('Decoded: ',type(script))
        else:
            attr_dict = dict()
            print("Couldn't create dictionary from website")

    return attr_dict

def brand_insert(placeholder):

    cur.execute('''INSERT OR IGNORE INTO Brands (name)
        VALUES ( ? )''', ( placeholder, ) )

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = sqlite3.connect('foodspider.sqlite')
cur = conn.cursor()

cur.executescript('''   DROP TABLE IF EXISTS Articles;
                        DROP TABLE IF EXISTS Brands;
                        DROP TABLE IF EXISTS Nova;
                        DROP TABLE IF EXISTS Nutri
                ''')

cur.execute('''CREATE TABLE IF NOT EXISTS Articles
            (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            url TEXT UNIQUE,
            brand_id INTEGER,
            nova_id,
            nutri_id
            )''')

cur.execute('''CREATE TABLE Brands (
                id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                name    TEXT UNIQUE)''')

cur.execute('''CREATE TABLE Nova (
                id  INTEGER NOT NULL PRIMARY KEY,
                score TEXT UNIQUE,
                slogan TEXT UNIQUE)''')

cur.execute('''CREATE TABLE Nutri (
                id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                score TEXT,
                description TEXT
             )''')


url = "https://world.openfoodfacts.org"
if url.endswith("/"): url = url[:-1]


pagenum = input('Enter an integer number: ')

if len(pagenum) < 1:
    pagenum = 1

try:
    pagenum = int(pagenum)
except:
    print('Not an integer!')
    quit()


urls = list()

for page in range(pagenum):
    page = page + 1 # +1 is because otherwise it will fetch page 0 first
    if page == 1:
        print("Retrieved:", page, 'page')
    else:
        print("Retrieved:", page, 'pages')

    urls.extend(article_crawl(url, page))

print(len(urls))

for link in urls:
    print(link, '\n')
    html = urllib.request.urlopen(link, context=ctx).read()
    soup = BeautifulSoup(html, 'html.parser')
    artankers = soup('a')

    brandlist = list()

    # get brands
    for anker in artankers:
        anker = anker.decode()

        if re.findall('/brand/', anker):
            brandlist.append(re.findall('"brand">(.+)<', anker)[0])
            # print(brandlist)
        else:
            continue

        # probably redundant
        if len(brandlist) < 1:
            continue
        elif len(brandlist) == 1:
            brand = brandlist[0]
        else:
            brand = ", ".join(brandlist)
            print('Two brands???:', '\n')

            for entry in brandlist:
                entry  = entry.strip()
                # print(entry)
                brand_insert(entry)

        # print(brand)
        brand_insert(brand)
        cur.execute('SELECT id FROM Brands WHERE name = ? ', (brand, ))
        brand_id = cur.fetchone()[0]

        print("Brand ID: ", brand_id, 'Brand:', brand)

    # get article attributes from webpage and write to dictionary
    attributes_dict = get_attributes(soup)

    # NOVA score information
    nova = attributes_dict['attribute_groups'][3]['attributes'][0]['title']
    try:
        nova_id = int(nova[4:])
    except:
        nova_id = 5

    for ank in artankers:
        ank = ank.decode()
        if re.findall('/nova', ank):
            if re.findall('alt=', ank):
                # ? at the end of regex necessary to prevent junk at the end of string
                nova_slogan = re.findall('alt="(.*?)"\s', ank)[0]
                nova_slogan = nova_slogan[4:]
            else:
                nova_slogan ='Food processing level unknown'
    # print(nova_id, nova, nova_slogan)

    # nutriscore information
    nutri = attributes_dict['attribute_groups'][0]['attributes'][0]['title']
    nutri_letter = re.findall('[\S+]\s(\w)', nutri)[0]
    index_dict = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
    try:
        nutri_id = index_dict[nutri_letter]
    except:
        nutri_id = 6
        nutri_letter = 'NA'
    nutri_desc = attributes_dict['attribute_groups'][0]['attributes'][0]['description_short']
    # print(nutri_id, nutri_letter, nutri_desc)

    cur.execute('''INSERT OR IGNORE INTO Brands (id, name)
        VALUES ( ?, ? )''', ( brand_id, brand ) )

    cur.execute('''INSERT OR IGNORE INTO Nova (id, score, slogan)
        VALUES ( ?, ?, ? )''', ( nova_id, nova, nova_slogan ) )

    cur.execute('''INSERT OR IGNORE INTO Nutri (id, score, description)
        VALUES ( ?, ?, ? )''', ( nutri_id, nutri_letter, nutri_desc ) )

    cur.execute('''INSERT OR REPLACE INTO Articles
        (url, brand_id, nova_id, nutri_id)
        VALUES ( ?, ?, ?, ? )''',
        ( link, brand_id, nova_id, nutri_id ) )


    conn.commit()

# print(idlst)

cur.close()
