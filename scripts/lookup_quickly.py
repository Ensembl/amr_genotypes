#!/usr/bin/env python3

# Add src as a package
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import csv
from src.lookup import Lookup
from src.utils import open_file

data_str = """
[{"subclass":"QUINOLONE"},
{"subclass":"BLEOMYCIN"},
{"subclass":"NARASIN"},
{"subclass":"XERUBORBACTAM"},
{"subclass":"FOSMIDOMYCIN"},
{"subclass":"MUPIROCIN"},
{"subclass":"MADURAMICIN"},
{"subclass":"SULFONAMIDE"},
{"subclass":"CARBAPENEM"},
{"subclass":"AMINOGLYCOSIDE"},
{"subclass":"PHENICOL"},
{"subclass":"EFFLUX"},
{"subclass":"PLEUROMUTILIN"},
{"subclass":"AMINOCOUMARIN"},
{"subclass":"ISONIAZID"},
{"subclass":"FOSFOMYCIN"},
{"subclass":"STREPTOTHRICIN"},
{"subclass":"COLISTIN"},
{"subclass":"BETA-LACTAM"},
{"subclass":"LINCOSAMIDE"},
{"subclass":"TETRACYCLINE"},
{"subclass":"FUSIDIC_ACID"},
{"subclass":"FLUOROQUINOLONE"},
{"subclass":"RIFAMYCIN"},
{"subclass":"TRICLOSAN"},
{"subclass":"SALINOMYCIN"},
{"subclass":"TRIMETHOPRIM"},
{"subclass":"STREPTOGRAMIN"},
{"subclass":"FUSIDIC ACID"}]
"""

data = json.loads(data_str)
l = Lookup()

fieldnames = [
    "subclass",
    "ontology",
    "id",
    "label",
    "iri",
    "short_form",
    "ontology_link",
]
output = []
for i in data:
    subclass = i["subclass"]
    a = l.convert_antibiotic(subclass)
    if a:
        print(f"Subclass {subclass} converts to: {a}")
        a["subclass"] = subclass
        output.append(a)
    else:
        print(f"Subclass {subclass} no hit")


with open_file("antibiotic_lookup.csv", "wt") as fh:
    w = csv.DictWriter(f=fh, fieldnames=fieldnames, dialect="excel")
    w.writeheader()
    w.writerows(output)
