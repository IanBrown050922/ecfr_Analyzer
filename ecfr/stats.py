from ecfr.utils import get_connection
import math, statistics, re

# Compute average word count of a given level of the hierarchy within a higher level of the hierarchy.
# e.g., average word count of parts within the chapters of title 18
# Returns list of sqlite3.Row with columns [level, avg_words]
def avg_word_count_by(title: int, parent_level: str, level: str):
    connection = get_connection()
    connection.create_function('sqrt', 1, math.sqrt) # create sqrt function to use in SQl
    cursor = connection.cursor()

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
    return [
        {
            f'{parent_level} ID':  r['group_id'],
            f'Average {level} Word Count': r['avg_words'],
            f'Standard Deviation of {level} Word Count': r['stddev'],
        }
        for r in rows
        if r['group_id']
    ]

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
    return [
        {
            f'{level} ID': r['group_id'],
            f'\'{keyword}\' count per {level}': r['count'],
        }
        for r in rows
        if r['group_id']
    ]

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
        tokens = txt.split() # split on whitespace
        groups.setdefault(gid, []).extend(tokens)

    # Compute type–token ratio: #unique_tokens / #total_tokens
    rows = []
    for gid, tokens in groups.items():
        total = len(tokens)
        unique = len({t.lower() for t in tokens})
        ttr = unique / total if total > 0 else 0.0
        rows.append({f'{level} ID': gid, 'Lexical Diversity': ttr})

    return rows

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
    return [
        {
            f'{parent_level} ID':  r['group_id'],
            f'Average {level} Cross-Reference Count': r['avg_crossrefs'],
            f'Standard Deviation of {level} Cross-Reference Count': r['stddev'],
        }
        for r in rows
        if r['group_id']
    ]

# Compute the lexical similarity (Jaccard Similarity) between a given level in a given title
# with every other level of that type in another (or the same) title.
# e.g., what's the lexical similarity between Title 1 Chapter 3 and the chapters of Title 12?
def lexical_similarity_by(level: str, src_title: str, src_id: str, tgt_title: str):
    connection = get_connection()
    cursor = connection.cursor()

    # load all text for the source group
    cursor.execute(
        f'SELECT text FROM sections WHERE title=? AND {level}=?',
        (src_title, src_id)
    )
    src_texts = [row['text'] or '' for row in cursor.fetchall()]

    # build the set of words in the source (split on spaces)
    src_words = set(
        w.lower()
        for txt in src_texts
        for w in txt.split()
    )

    # load every section in the target title, grouped by the same level
    # build a single f-string for the whole query
    query = f'''
    SELECT {level}   AS group_id,
          text
      FROM sections
    WHERE title = ?
      AND {level} IS NOT NULL
      AND {level} <> ''
    '''
    cursor.execute(query, (tgt_title,))
    rows = cursor.fetchall()
    connection.close()

    # group all texts by group_id
    groups = {}
    for r in rows:
        gid = r['group_id']
        txt = r['text'] or ''
        groups.setdefault(gid, []).append(txt)

    # compute Jaccard similarity for each group:
    # |A intersect B| / |A union B|
    results = []
    for gid, texts in groups.items():
        tgt_words = set(
            w.lower()
            for t in texts
            for w in t.split()
        )
        # avoid divide-by-zero if both sets are empty
        union = src_words | tgt_words
        sim   = len(src_words & tgt_words) / len(union) if union else 0.0
        results.append({
            f'{level} ID': gid,
            'Similarity': sim
        })

    return results

# NOTE: Needs work
# For each child section (at `level`) under each parent (at `parent_level`) in `title`,
# compute how many hops of §-references you can follow until you reach a section with no refs.
def citation_depth_by(title: int, parent_level: str, level: str):
    connection = get_connection()
    cursor = connection.cursor()

    # fetch parent, child, and text
    query = f'''
    SELECT
      {parent_level} AS parent,
      {level}        AS child,
      text
    FROM sections
    WHERE title = ?
      AND {parent_level} IS NOT NULL AND {parent_level} <> ''
      AND {level}        IS NOT NULL AND {level}        <> ''
    '''
    cursor.execute(query, (title,))
    rows = cursor.fetchall()
    connection.close()

    # map each local section ID to its full lineage, and collect texts
    full_of_local = {}
    text_of_full = {}
    for r in rows:
        full = r['child'] # e.g. "Title 1 > Chapter I > … > SECTION 1.1"
        parts = full.rsplit('SECTION ', 1)
        local = parts[1] if len(parts) == 2 else full
        full_of_local[local] = full
        text_of_full[full] = r['text'] or ''

    # build parent map
    parent_of = {r['child']: r['parent'] for r in rows}

    # extract §‑references, translated to full lineage keys
    pattern = re.compile(r'§\s*([\w\.\-]+)')
    refs = {}
    for full, txt in text_of_full.items():
        locals_found = pattern.findall(txt)
        linked = [
            full_of_local[loc]
            for loc in locals_found
            if loc in full_of_local
        ]
        refs[full] = linked

    # compute depth with cycle‑detection
    cache = {}
    def depth(node, seen=None):
        if node in cache:
            return cache[node]
        if seen is None:
            seen = set()
        if node in seen:
            cache[node] = 0
            return 0
        seen_next = seen | {node}
        children = [t for t in refs.get(node, []) if t in refs]
        if not children:
            d = 0
        else:
            d = 1 + max(depth(t, seen_next) for t in children)
        cache[node] = d
        return d

    # special case: section→section returns raw depths
    if parent_level == level == 'section':
        return [
            {'group_id': sec, 'avg_depth': depth(sec), 'stddev_depth': 0.0}
            for sec in refs
        ]

    # group depths by parent and compute stats
    groups = {}
    for sec in refs:
        parent = parent_of.get(sec)
        if parent:
            groups.setdefault(parent, []).append(depth(sec))

    result = []
    for parent, depths in groups.items():
        avg = statistics.mean(depths)
        std = statistics.pstdev(depths)
        result.append({
            f'{parent_level}': parent,
            f'Average Citation Depth of {level}s': avg,
            f'Standard Deviation of Citation Depth of {level}s': std
        })

    return result
