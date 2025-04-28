from ecfr.utils import get_connection
import math

# Compute average word count of a given level of the hierarchy within a higher level of the hierarchy.
# e.g., average word count of parts within the chapters of title 18
# Returns list of sqlite3.Row with columns [level, avg_words]
def avg_word_count_by(title: int, parent_level: str, level: str):
    connection = get_connection()
    connection.create_function('sqrt', 1, math.sqrt) # create sqrt function to use in SQl
    cursor = connection.cursor()

    # disallow identical or invalid parent/child levels
    if parent_level == level:
        raise ValueError('parent_level must differ from level')
    if parent_level == 'section':
        raise ValueError('parent_level cannot be \'section\'')

    query = f'''
    WITH inner_sums AS (
      SELECT
        {parent_level} AS parent_id,
        {level}        AS child_id,
        SUM(word_count) AS sum_words
      FROM sections
      WHERE title = ?
        AND {level} IS NOT NULL
        AND {level} <> ''
      GROUP BY {parent_level}, {level}
    )
    SELECT
      parent_id      AS group_id,
      AVG(sum_words) AS avg_words,
      sqrt(
        AVG(sum_words * sum_words)
        - AVG(sum_words) * AVG(sum_words)
      ) as stddev
    FROM inner_sums
    GROUP BY parent_id
    ORDER BY parent_id
    '''
    cursor.execute(query, (title,))
    rows = cursor.fetchall()
    connection.close()
    rows = [r for r in rows if r['group_id']]
    return rows

# Count the occurences of `keyword` (case-insensitive) in each group of the specified level
# and title.
def keyword_count_by(level: str, title: int, keyword: str):
    connection = get_connection()
    cursor = connection.cursor()
    query = f'''
    SELECT {level} AS group_id,
      SUM(
        (LENGTH(LOWER(text))
        - LENGTH(REPLACE(LOWER(text), LOWER(?), ''))
        ) / LENGTH(?)
      ) AS count
    FROM sections
    WHERE title = ?
      AND text LIKE '%' || ? || '%'
    GROUP BY {level}
    ORDER BY {level}'''
    cursor.execute(query, (keyword, keyword, title, keyword))
    rows = cursor.fetchall()
    connection.close()
    rows = [r for r in rows if r['group_id']]
    return rows

# Compute the lexical diversity (type–token ratio) of each group at the given level
# within the specified CFR title.
def lexical_diversity_by(level: str, title: int):
    connection = get_connection()
    cursor = connection.cursor()

    # Pull every section's text along with its group label
    query = f'''
    SELECT {level} AS group_id, text
    FROM sections
    WHERE title = ?
      AND {level} IS NOT NULL
      AND {level} <> ''
    ORDER BY {level}
    '''
    cursor.execute(query, (title,))
    rows = cursor.fetchall()
    connection.close()

    # Aggregate all tokens per group
    groups = {}
    for r in rows:
        gid  = r['group_id']
        txt  = r['text'] or ''
        tokens = txt.split()              # split on whitespace
        groups.setdefault(gid, []).extend(tokens)

    # Compute type–token ratio: #unique_tokens / #total_tokens
    results = []
    for gid, tokens in groups.items():
        total = len(tokens)
        unique = len({t.lower() for t in tokens})
        ttr = unique / total if total > 0 else 0.0
        results.append({'group_id': gid, 'lexical_diversity': ttr})

    return results

# Compute the average number of cross-references (§ symbols) per group
# at the specified level within each parent group, for a given title.
def cross_reference_count_by(title: int, parent_level: str, level: str):
    connection = get_connection()
    connection.create_function('sqrt', 1, math.sqrt) # create sqrt function to use in SQl
    cursor = connection.cursor()

    query = f'''
    WITH crossrefs AS (
      SELECT
        {parent_level} AS parent_id,
        {level}        AS child_id,
        LENGTH(text) - LENGTH(REPLACE(text, '§', '')) AS num_crossrefs
      FROM sections
      WHERE title = ?
        AND {parent_level} IS NOT NULL
        AND {parent_level} <> ''
        AND {level} IS NOT NULL
        AND {level} <> ''
    )
    SELECT
      parent_id AS group_id,
      AVG(num_crossrefs) AS avg_crossrefs,
      sqrt(
        AVG(num_crossrefs * num_crossrefs)
        - AVG(num_crossrefs) * AVG(num_crossrefs)
      ) as stddev
    FROM crossrefs
    GROUP BY parent_id
    ORDER BY parent_id
    '''
    cursor.execute(query, (title,))
    rows = cursor.fetchall()
    connection.close()
    rows = [r for r in rows if r['group_id']]
    return rows
