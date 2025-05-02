'''
Script to fetch updated contents of all 50 eCFR titles and construct a local database from their contents.
'''

import requests, os, sqlite3, xml.etree.ElementTree as ET

# API base url for versioner service
API_BASE_VS = 'https://www.ecfr.gov/api/versioner/v1'
# directory to save xml files
XML_DIR = './data/ecfr_xml'
DB_PATH = './data/ecfr.db'
NUM_TITLES = 50

# In order to retrieve the full content under a title, we need to construct it's full url using
# the most recent relevant date.
def latest_date(title: int):
    # The /versions/title-{title}.json endpoint returns a JSON list with the snapshot dates that
    # exist for a given title.
    url = f'{API_BASE_VS}/versions/title-{title}.json'
    resp = requests.get(url)
    resp.raise_for_status()
    # JSON content from request is stored as a python dict
    # return most recent relevant date for the title
    return resp.json()['meta']['latest_issue_date']

# Download the full XML dump corresponding to a title and snapshot date
def download_full_xml(title:int, date:str)->str:
    url  = f'{API_BASE_VS}/full/{date}/title-{title}.xml'
    r = requests.get(url)
    r.raise_for_status()
    # write the bytes of the response (r.content) to a local path
    path = f'{XML_DIR}/title_{title}_{date}.xml'
    with open(path, 'wb') as f:
        f.write(r.content)
    size_KB = len(r.content)/1_000 # size in KB of title's content
    return path, size_KB

def get_all_xmls():
    for title in range(1, NUM_TITLES+1):
        try:
            date = latest_date(title)
            path, size_KB = download_full_xml(title, date)
            print('Saved', path, f'({size_KB} KB)')
        except Exception as e:
            print('Title', title, 'failed:', e)

# Walk a title's XML tree to build rows of the database table
def walk_xml_tree(rows, elem, ctx, current_title, ancestry_id):
    t = elem.get('TYPE') # e.g. 'CHAPTER', 'SECTION', etc.
    n = elem.get('N') # the identifier (digit, Roman numeral, letter)
    if ancestry_id is None:
        full_id = n
    else:
        full_id = f'{ancestry_id}, {t} {n}' # full id with sequence of ancestral ids

    # update context based on TYPE
    if t == 'CHAPTER':
        ctx['chapter'] = full_id
    elif t == 'SUBCHAP':
        ctx['subchapter'] = full_id
    elif t == 'PART':
        ctx['part'] = full_id
    elif t == 'SUBPART':
        ctx['subpart'] = full_id
    elif t == 'SECTION':
        # when we hit a section div, build a row of the table
        # paragraphs = ' '.join(p.text or '' for p in elem.findall('.//P'))
        paragraphs = ' '.join(
            ''.join(p.itertext()) 
            for p in elem.findall('.//P')
        )
        rows.append((
            current_title,
            ctx.get('chapter'),
            ctx.get('subchapter'),
            ctx.get('part'),
            ctx.get('subpart'),
            full_id, # section number
            paragraphs,
            len(paragraphs.split())
        ))
    # recurse into child DIVs
    for child in elem:
        if child.tag.startswith('DIV'):
            walk_xml_tree(rows, child, dict(ctx), current_title, full_id)

def fill_rows(rows):
    for xml_file in os.listdir(XML_DIR):
        if not xml_file.endswith('.xml'): continue
        current_title = int(xml_file.split('_')[1])  # expects “title_1_YYYY-MM-DD.xml”
        path = os.path.join(XML_DIR, xml_file)
        tree = ET.parse(path)
        root = tree.getroot()
        # start context with no chapter/etc. - we only need to store ancestor types of section
        initial_ctx = {'chapter':None, 'subchapter':None, 'part':None, 'subpart':None}
        walk_xml_tree(rows, root, initial_ctx, current_title, None)

def run():
    # ensure ./data and ./data/ecfr_xml exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(XML_DIR, exist_ok=True)
    # get data as XML
    get_all_xmls()

    # construct/connect local database
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS sections (
        title      INTEGER,
        chapter    TEXT,
        subchapter TEXT,
        part       TEXT,
        subpart    TEXT,
        section    TEXT,
        text       TEXT,
        word_count INTEGER
    );
    DELETE FROM sections;
    ''')
    rows = []
    # iterate over XML files
    fill_rows(rows)
    # bulk‐insert into SQLite
    cursor.executemany(
        'INSERT INTO sections VALUES (?,?,?,?,?,?,?,?)',
        rows
    )
    # commit changes and close database
    connection.commit()
    connection.close()
    print(f'SQLite database built: {DB_PATH} ({len(rows)} sections inserted)')

# in case we need to run this script directly
if __name__ == '__main__':
    run()