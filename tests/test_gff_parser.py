from src.gff_parser import GFF3Parser
import tempfile

def test_parse_serialize_roundtrip():
    sample = ('##gff-version 3',
                'chr1	RefSeq	gene	1	10	.	+	.	ID=gene1;Name=Gene1',
                'chr1	RefSeq	exon	1	5	.	+	.	ID=exon1;Parent=gene1')
    with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.gff3') as tmp:
        for s in sample:
            print(s, file=tmp)
        tmp.flush()
        path = tmp.name
    parser = GFF3Parser(path)
    # Ensure attributes are lists
    print(parser.features)
    assert parser.features[0].attributes['ID'], ['gene1']
    assert parser.features[1].attributes['Parent'], ['gene1']
    # Serialize and ensure content contains expected attributes (comma-joined)
    lines = list(parser.to_gff_lines())
    assert any('ID=gene1' in l for l in lines)

def test_percent_decoding_and_single_list():
    p = GFF3Parser.__new__(GFF3Parser)
    res = GFF3Parser._parse_attributes(p, 'ID=gene1;Name=My%20Gene')
    assert res['ID'], ['gene1']
    assert res['Name'], ['My Gene']

def test_repeated_keys_and_commas():
    p = GFF3Parser.__new__(GFF3Parser)
    res = GFF3Parser._parse_attributes(p, 'Note=first;Note=second,third;Tag=a,b;Tag=c')
    assert res['Note'], ['first', 'second', 'third']
    assert res['Tag'], ['a', 'b', 'c']

def test_bare_key_and_empty_value():
    p = GFF3Parser.__new__(GFF3Parser)
    res = GFF3Parser._parse_attributes(p, 'flag;Empty=;Another')
    assert res['flag'], ['']
    assert res['Empty'], ['']
    assert res['Another'], ['']
