import streamlit as st
import scripts.fetch_ecfr as fetch
from ecfr.stats import *

st.set_page_config(page_title='eCFR Explorer', layout='wide')
st.title('eCFR Statistical Explorer')

# database builder
@st.cache_resource(ttl=7*24*60*60) # fetch at least once every 7 days
def build_db():
    fetch.run()
# rebuild database on a regular basis:
build_db()

METRICS = ['Average words per group',
           'Keyword count per group',
           'Lexical diversity',
           'Average cross-references per group',
           'Lexical similarity',
           'Citation depth']

# sidebar inputs
metric = st.sidebar.selectbox(
    'Choose a metric',
    METRICS
)

title = st.sidebar.number_input(
    'CFR Title (1–50)',
    min_value=1, max_value=50, value=1, step=1,
)

# UI By Metric
ORDER = ['title','chapter','subchapter','part','subpart','section']

if metric in [METRICS[i] for i in [0, 3]]:
    parent_levels = ORDER[:-1] # ['title', 'chapter', …, 'subpart']
    parent_level = st.sidebar.selectbox('Group by parent level', parent_levels)
    levels = ORDER[1:] # ['chapter', …, 'section']
    level = st.sidebar.selectbox('Group by level', levels)

    # Validate that parent is above child
    if ORDER.index(parent_level) >= ORDER.index(level):
        st.sidebar.error('Parent level must be above the child level in the hierarchy.')
        st.stop()
elif metric == METRICS[1]:
    levels = ORDER
    level = st.sidebar.selectbox('Group by level', levels)
    keyword = st.sidebar.text_input('Keyword (case-insensitive)')
    if not keyword:
        st.sidebar.warning('Enter a keyword to search for')
        st.stop()
elif metric == METRICS[2]:
    levels = ORDER
    level = st.sidebar.selectbox('Group by level', levels)
elif metric == METRICS[4]:
    levels = ORDER[1:]
    level = st.sidebar.selectbox('Group by level', levels)
    src_id = st.sidebar.text_input('Source Level ID (Format: \'title_num, CHAPTER chapter_num, SUBCHAP subchap_num, PART part_num, etc... \')')
    tgt_title = st.sidebar.number_input(
        'Target Title (1–50)',
        min_value=1, max_value=50, value=1, step=1
    )
if metric == METRICS[5]:
    parent_levels = ORDER # ['title', 'chapter', …, 'subpart']
    parent_level = st.sidebar.selectbox('Group by parent level', parent_levels)
    levels = ORDER[1:] # ['chapter', …, 'section']
    level = st.sidebar.selectbox('Group by level', levels)

    # Validate that parent is above child
    if ORDER.index(parent_level) >= ORDER.index(level) and parent_level != ORDER[-1]:
        st.sidebar.error('Parent level must be above the child level in the hierarchy.')
        st.stop()

# main content
if metric == METRICS[0]:
    data = avg_word_count_by(title, parent_level, level)
    st.subheader(f'Mean and stddev of {level.capitalize()} word count per {parent_level.capitalize()} in Title {title}')
elif metric == METRICS[1]:
    data = keyword_count_by(level, title, keyword)
    st.subheader(f'Instances of \'{keyword}\' per {level.capitalize()} in Title {title}')
elif metric == METRICS[2]:
    data = lexical_diversity_by(level, title)
    st.subheader(f'Type-Token ratio per {level.capitalize()} in Title {title}')
elif metric == METRICS[3]:
    data = cross_reference_count_by(title, parent_level, level)
    st.subheader(f'Mean and stddev of cross-references per {level.capitalize()} in {parent_level.capitalize()}s in Title {title}')
elif metric == METRICS[4]:
    data = lexical_similarity_by(level, title, src_id, tgt_title)
    st.subheader(f'Lexical Similarity (Jaccard Index) between Title {src_id}, and the {level.capitalize()}s in Title {tgt_title}')
elif metric == METRICS[5]:
    data = citation_depth_by(title, parent_level, level)
    st.subheader(f'Citation Depth')

# render table
st.table(data)