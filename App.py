import streamlit as st
from ecfr.stats import *

st.set_page_config(page_title='eCFR Explorer', layout='wide')
st.title('eCFR Statistical Explorer')

# sidebar inputs
metric = st.sidebar.selectbox(
    'Choose a metric',
    ['Average words per group',
     'Keyword count per group',
     'Lexical diversity',
     'Average cross-references per group']
)

title = st.sidebar.number_input(
    'CFR Title (1–50)',
    min_value=1, max_value=50, value=1, step=1
)

# UI
if metric == 'Average words per group':
    parent_levels = ['title', 'chapter', 'subchapter', 'part', 'subpart']
    parent_level = st.sidebar.selectbox('Group by parent level', parent_levels)
    levels = ['chapter', 'subchapter', 'part', 'subpart', 'section']
    level = st.sidebar.selectbox('Group by level', levels)
elif metric == 'Keyword count per group':
    levels = ['title', 'chapter', 'subchapter', 'part', 'subpart', 'section']
    level = st.sidebar.selectbox('Group by level', levels)
    keyword = st.sidebar.text_input('Keyword (case-insensitive)')
    if not keyword:
        st.sidebar.warning('Enter a keyword to search for')
        st.stop()
elif metric == 'Lexical diversity':
    levels = ['title', 'chapter', 'subchapter', 'part', 'subpart', 'section']
    level = st.sidebar.selectbox('Group by level', levels)
elif metric == 'Average cross-references per group':
    parent_levels = ['title', 'chapter', 'subchapter', 'part', 'subpart']
    parent_level = st.sidebar.selectbox('Group by parent level', parent_levels)
    levels = ['chapter', 'subchapter', 'part', 'subpart', 'section']
    level = st.sidebar.selectbox('Group by level', levels)

# main content
if metric == 'Average words per group':
    data = avg_word_count_by(title, parent_level, level)
    st.subheader(f'Mean and stddev of {level.capitalize()} word count per {parent_level.capitalize()} in Title {title}')
    st.table(data)
elif metric == 'Keyword count per group':
    data = keyword_count_by(level, title, keyword)
    st.subheader(f'Instances of \'{keyword}\' per {level.capitalize()} in Title {title}')
    st.table(data)
elif metric == 'Lexical diversity':
    data = lexical_diversity_by(level, title)
    st.subheader(f'Type-Token ratio per {level.capitalize()} in Title {title}')
    st.table(data)
elif metric == 'Average cross-references per group':
    data = cross_reference_count_by(title, parent_level, level)
    st.subheader(f'Mean and stddev of cross-references per {level.capitalize()} in {parent_level.capitalize()}s in Title {title}')
    st.table(data)