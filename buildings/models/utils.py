
STRING_QUERIES_TO_FILTER = {
    "q_address": "address__icontains",
    "q_locality": "locality__icontains",
    "q_region": "region__icontains",
    "q_cubf": "cubf_str__icontains",
}


SQL_RANDOM_UNVOTED_ID = f"""
    SELECT e.id FROM evalunits e 
    JOIN hlms h ON h.eval_unit_id = e.id 
    LEFT OUTER JOIN buildings_vote v ON v.eval_unit_id = e.id
    WHERE v.id is null 
    ORDER BY random() LIMIT 1;
"""

SQL_RANDOM_UNVOTED_ID_WITH_EXCLUDE = f"""
    SELECT e.id FROM evalunits e 
    JOIN hlms h ON h.eval_unit_id = e.id 
    LEFT OUTER JOIN buildings_vote v ON v.eval_unit_id = e.id
    WHERE v.id is null 
    AND e.id != %s
    ORDER BY random() LIMIT 1;
"""

# The limit parameter gives the number of eval units from which we will randomly pick
# ideally we want it somewaht large (though not too much that the query is expensive)
# but it can't be less than the number of eval units minus 1, else the query won't work
SQL_RANDOM_LEAST_VOTED_ID = f"""
    SELECT sub.id FROM 
        (SELECT e.id FROM evalunits e
        JOIN hlms h ON h.eval_unit_id = e.id 
        LEFT OUTER JOIN buildings_vote v ON (e.id = v.eval_unit_id) 
        GROUP BY e.id 
        ORDER BY COUNT(v.id) ASC LIMIT %s) 
    AS sub ORDER BY RANDOM() LIMIT 1;
"""

SQL_RANDOM_LEAST_VOTED_ID_WITH_EXCLUDE = f"""
    SELECT sub.id FROM 
        (SELECT e.id FROM evalunits e 
        JOIN hlms h ON h.eval_unit_id = e.id 
        LEFT OUTER JOIN buildings_vote v ON (e.id = v.eval_unit_id) 
        WHERE e.id != %s 
        GROUP BY e.id ORDER BY COUNT(v.id) ASC limit %s) 
    AS sub ORDER BY RANDOM() LIMIT 1;
"""

SQL_RANDOM_ID = f"""
    SELECT sub.id FROM 
        (SELECT e.id FROM evalunits e LIMIT %s) 
    AS sub ORDER BY RANDOM() LIMIT 1;
"""

SQL_RANDOM_ID_WITH_EXCLUDE = f"""
    SELECT sub.id FROM 
        (SELECT e.id FROM evalunits e 
        WHERE e.id != %s LIMIT %s) 
    AS sub ORDER BY RANDOM() LIMIT 1;
"""
