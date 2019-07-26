"""
An OpenRefine reconciliation service
"""
from flask import Flask, request, jsonify, g
import getopt
import json
import collections
import fingerprints
import difflib

from flask_mysqldb import MySQL
import MySQLdb

LOAD_COUNTRIES_SQL = """
SELECT cd.id AS id, cn.country_name AS name_to_match, cd.owid_name AS canonical_name, "country" AS type
FROM country_name_tool_countryname cn
INNER JOIN country_name_tool_countrydata cd ON cd.id = cn.owid_country

UNION

SELECT e.id AS id, e.name AS name_to_match, e.name AS canonical_name, "entity" AS type
FROM entities e
"""

SUGGEST_SQL = """
    SELECT DISTINCT cd.id AS id, cd.owid_name AS name FROM country_name_tool_countrydata cd
    INNER JOIN country_name_tool_countryname cn ON cn.owid_country = cd.id
    WHERE LOWER(cn.`country_name`) like %s

    UNION

    SELECT DISTINCT e.id AS id, e.name as name FROM entities e
    WHERE LOWER(e.`name`) like %s
"""

FLYOUT_SQL = """
    SELECT * FROM country_name_tool_countrydata
    WHERE id = %s
"""

app = Flask(__name__)
app.config.from_envvar('OWID_RECONCILIATION_SETTINGS')
mysql = MySQL(app)


def get_countries():
    if 'countries' in g:
        return g.countries

    rv = collections.defaultdict(list)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(LOAD_COUNTRIES_SQL)
    for r in cursor.fetchall():
        rv[fingerprints.generate(r["name_to_match"])].append(r)

    g.countries = rv
    return g.countries


QUERY_TYPES = [
    {
        "id": "/geo/country",
        "name": "Countries"
    }
]

# Basic service metadata.
metadata = {
    "name": "OWID Country Reconciliation Service",
    "defaultTypes": QUERY_TYPES,
    "identifierSpace": "http://localhost/identifier",
    "schemaSpace": "http://localhost/schema",
    "view": {
        "url": "{{id}}"
    },
    "suggest": {
        "entity": {
            "service_path": "/suggest/entity",
            "service_url": "http://localhost:5000",
            # "flyout_service_path": "/flyout/entity?id=${id}"
        }
    }
}


def jsonpify(obj):
    """
    Helper to support JSONP
    """
    try:
        callback = request.args['callback']
        response = app.make_response("%s(%s)" % (callback, json.dumps(obj)))
        response.mimetype = "text/javascript"
        return response
    except KeyError:
        return jsonify(obj)


def search(raw_query, query_type='/geo/country'):
    raw_query = fingerprints.generate(raw_query)
    countries = get_countries()

    rv = []

    matches = countries[fingerprints.generate(raw_query)]
    for m in matches:
        m['comparison_score'] = difflib.SequenceMatcher(
            None, raw_query, fingerprints.generate(m['name_to_match'])) \
            .quick_ratio()

    for m in sorted(matches,
                    key=lambda i: i['comparison_score'],
                    reverse=True):
        score = m['comparison_score']
        rv.append({
            'id': str(m['id']),
            'name': m['canonical_name'],
            'type': [QUERY_TYPES[0]['id']],
            'score': score * 100,
            'match': m['type'] == 'country' and score == 1.0,
            'all_labels': {
                'score': score * 100,
                'weighted': score * 100
            }
        })

    return rv


@app.route("/suggest/entity", methods=["GET"])
def suggest_entity():
    prefix = request.args.get('prefix')
    resp = {
        "code": "/api/status/ok",
        "status": "200 OK",
        "prefix": prefix,
    }

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(SUGGEST_SQL, ('%%%s%%' % prefix.lower(),) * 2)

    results = []
    for result in cursor.fetchall():
        results.append({
            "id": str(result['id']),
            "name": result['name']
        })

    resp['result'] = results

    return jsonpify(resp)


@app.route("/flyout/entity", methods=["GET"])
def flyout():
    _id = request.args.get('id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(FLYOUT_SQL, (_id,))
    results = cursor.fetchall()

    return jsonpify(
        {
            "id": str(results[0]['id']),
            "html": "<p style=\"font-size: 0.8em; color: black;\">%s</p>" % results[0]['owid_name']
        }
    )


@app.route("/reconcile", methods=['POST', 'GET'])
def reconcile():
    # If a 'queries' parameter is supplied then it is a dictionary
    # of (key, query) pairs representing a batch of queries. We
    # should return a dictionary of (key, results) pairs.
    if request.method == 'POST':
        queries = request.form.get('queries')
    else:
        queries = request.args.get('queries')

    if queries:
        queries = json.loads(queries)
        results = {}
        for (key, query) in queries.items():
            qtype = query.get('type')
            if qtype is None:
                return jsonpify(metadata)
            data = search(query['query'], query_type=qtype)
            results[key] = {"result": data}
        return jsonpify(results)
    # If neither a 'query' nor 'queries' parameter is supplied then
    # we should return the service metadata.
    return jsonpify(metadata)


if __name__ == '__main__':
    from optparse import OptionParser

    oparser = OptionParser()
    oparser.add_option('-d', '--debug', action='store_true', default=False)
    opts, args = oparser.parse_args()
    app.debug = opts.debug

    app.run(host='0.0.0.0')
