from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, List, Iterator, Optional, Tuple, Union
from .utils import open_file, bin_from_range_extended

@dataclass
class Feature:
    seqid: str
    source: str
    type: str
    start: int
    end: int
    score: Optional[float]
    strand: Optional[str]
    phase: Optional[int]
    attributes: Dict[str, Union[str, List[str]]]
    line_no: int = -1
    raw: str = ''
    parent_ids: List[str] = field(default_factory=list)
    children: List['Feature'] = field(default_factory=list)

    def __post_init__(self):
        # Normalize parent_ids from attributes if available
        p = self.attributes.get('Parent')
        if p:
            if isinstance(p, list):
                self.parent_ids = p
            else:
                self.parent_ids = [p]

    def id(self) -> Optional[str]:
        v = self.attributes.get('ID')
        if isinstance(v, list):
            return v[0]
        return v

    def to_tuple(self) -> Tuple:
        """Return a compact tuple representation (useful for sorting/comparison)."""
        return (self.seqid, self.start, self.end, self.type, self.id())

    def __repr__(self):
        return (f"Feature({self.seqid}:{self.start}-{self.end} {self.type}"
                f" id={self.id()!r} parents={self.parent_ids})")
    
    def get_single_attribute(self, key: str, default=None) -> Optional[str]:
        """Get a single attribute value for the given key, or default if not present.
        """
        v = self.attributes.get(key, default)
        if isinstance(v, list):
            return v[0]
        return v

    def get_attribute_list(self, key: str) -> List[str]:
        """Get the attribute value(s) for the given key as a list.
        If the attribute is not present, returns an empty list.
        """
        v = self.attributes.get(key, None)
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]
    
    def get_concatenated_attribute(self, key: str, sep: str = ';') -> str:
        """Get the attribute value(s) for the given key as a concatenated string.
        If the attribute is not present, returns an empty string.
        """
        vals = self.get_attribute_list(key)
        return sep.join(vals)

    def bin(self) -> int:
        """Compute the extended bin for this feature's range."""
        return bin_from_range_extended(self.start - 1, self.end)

class GFF3Parser:
    """Iterator/parser for GFF3 files.

    Example usage:
        parser = GFF3Parser('file.gff3')
        for feat in parser:
            process(feat)

    It stores:
    - directives: list of (directive_line_no, directive_text)
    - comments: list of (line_no, comment_text)
    - features: list of Feature objects
    - fasta: dict mapping name -> sequence (if ##FASTA present)
    - id_index: mapping id -> Feature
    """

    def __init__(self, path: str):
        self.path = path
        self.directives: List[Tuple[int, str]] = []
        self.comments: List[Tuple[int, str]] = []
        self.features: List[Feature] = []
        self.id_index: Dict[str, Feature] = {}
        self.fasta: Dict[str, str] = {}
        self._parse()

    def extract_directive(self, directive_name: str) -> str:
        for index, line in self.directives:
            if line.startswith(f"#!{directive_name}"):
                return line[len(directive_name)+2:].strip()
        for index, line in self.comments:
            if line.startswith(f"#!{directive_name}"):
                return line[len(directive_name)+2:].strip()
        return ""

    @staticmethod
    def _parse_attributes(attrtext: str) -> Dict[str, List[str]]:
        """Parse the attribute column into a dict. Values are percent-decoded and
        **always** returned as lists (even single values).

        Behavior:
        - Uses urllib.parse.unquote (percent-decoding). Does not treat '+' as space.
        - Splits on semicolons (';') to separate attributes. Empty parts are ignored.
        - For key=value pairs, the value is split on commas. Each resulting string is
          percent-decoded and included in the list even if there's only one element.
        - Repeated keys are merged into a single list preserving order.
        - Bare keys (no '=') are represented as an empty-string value [''].
        """
        attrs: Dict[str, List[str]] = {}
        if not attrtext or attrtext == '.':
            return attrs

        parts = [p for p in attrtext.split(';') if p != '']
        for part in parts:
            if '=' in part:
                k, v = part.split('=', 1)
                k = urllib.parse.unquote(k)
                # Keep percent-decoding semantics; do NOT use unquote_plus
                v_decoded = urllib.parse.unquote(v)
                # Split on commas to produce a list, even if single item
                values = [x for x in v_decoded.split(',')]
                if k in attrs:
                    attrs[k].extend(values)
                else:
                    attrs[k] = values
            else:
                # Bare key -> empty string value
                k = urllib.parse.unquote(part)
                if k in attrs:
                    attrs[k].append('')
                else:
                    attrs[k] = ['']
        return attrs

    def _parse_feature_line(self, line: str, line_no: int) -> Optional[Feature]:
        parts = line.rstrip('\n').split('\t')
        if len(parts) != 9:
            # not a feature line
            return None
        seqid, source, typ, start, end, score, strand, phase, attributes = parts
        try:
            start_i = int(start)
            end_i = int(end)
        except ValueError:
            raise ValueError(f"Invalid start/end at line {line_no}: {start},{end}")
        score_v: Optional[float]
        if score == '.' or score.strip() == '':
            score_v = None
        else:
            try:
                score_v = float(score)
            except ValueError:
                score_v = None
        strand_v = strand if strand in ('+', '-', '.') else None
        phase_v: Optional[int]
        if phase == '.' or phase.strip() == '':
            phase_v = None
        else:
            try:
                phase_v = int(phase)
            except ValueError:
                phase_v = None
        attrs = self._parse_attributes(attributes)
        feat = Feature(seqid=seqid, source=source, type=typ, start=start_i, end=end_i,
                       score=score_v, strand=strand_v, phase=phase_v,
                       attributes=attrs, line_no=line_no, raw=line.rstrip('\n'))
        return feat

    def _parse(self):
        in_fasta = False
        current_fasta_name = None
        seq_chunks: List[str] = []
        with open_file(self.path) as fh:
            for i, raw in enumerate(fh, start=1):
                line = raw.rstrip('\n')
                if in_fasta:
                    if line.startswith('>'):
                        # save previous
                        if current_fasta_name is not None:
                            self.fasta[current_fasta_name] = ''.join(seq_chunks)
                        current_fasta_name = line[1:].strip().split()[0]
                        seq_chunks = []
                    else:
                        seq_chunks.append(line.strip())
                    continue

                if not line:
                    continue
                if line.startswith('##'):
                    self.directives.append((i, line))
                    if line.strip().upper() == '##FASTA':
                        in_fasta = True
                        current_fasta_name = None
                        seq_chunks = []
                    continue
                if line.startswith('#'):
                    self.comments.append((i, line))
                    continue
                # Feature line
                feat = self._parse_feature_line(line, i)
                if feat is not None:
                    self.features.append(feat)
                    fid = feat.id()
                    if fid:
                        # If multiple features share same ID, keep the first one in index
                        if fid not in self.id_index:
                            self.id_index[fid] = feat
        # finish any fasta
        if in_fasta and current_fasta_name is not None:
            self.fasta[current_fasta_name] = ''.join(seq_chunks)

        # Build parent-child relationships
        for feat in self.features:
            for pid in feat.parent_ids:
                parent = self.id_index.get(pid)
                if parent:
                    parent.children.append(feat)

    def __iter__(self) -> Iterator[Feature]:
        yield from self.features

    def get_by_id(self, id_: str) -> Optional[Feature]:
        return self.id_index.get(id_)

    def features_by_seqid(self, seqid: str) -> List[Feature]:
        return [f for f in self.features if f.seqid == seqid]

    def features_by_type(self, typ: str) -> List[Feature]:
        return [f for f in self.features if f.type == typ]

    def to_gff_lines(self) -> Iterator[str]:
        """Serialize parsed content back to GFF3-ish lines (directives, comments, features)."""
        for ln, d in self.directives:
            yield d
        for ln, c in self.comments:
            yield c
        for f in self.features:
            attrs = []
            for k, v in f.attributes.items():
                if isinstance(v, list):
                    val = ','.join(v)
                else:
                    val = v
                # percent-encode keys and values to be safe
                key_enc = urllib.parse.quote(k, safe='')
                val_enc = urllib.parse.quote(str(val), safe='')
                attrs.append(f"{key_enc}={val_enc}")
            attrcol = ';'.join(attrs) if attrs else '.'
            score = '.' if f.score is None else str(f.score)
            strand = f.strand if f.strand is not None else '.'
            phase = '.' if f.phase is None else str(f.phase)
            yield '\t'.join([f.seqid, f.source, f.type, str(f.start), str(f.end), score, strand, phase, attrcol])
        if self.fasta:
            yield '##FASTA'
            for name, seq in self.fasta.items():
                yield f">{name}"
                # wrap at 60 chars
                for i in range(0, len(seq), 60):
                    yield seq[i:i+60]

class GFF3StreamingParser:
    _parse_attributes = staticmethod(GFF3Parser._parse_attributes)
    _parse_feature_line = GFF3Parser._parse_feature_line
    
    """A streaming GFF3 parser that yields Feature objects without holding everything in memory.

    - Does not build parent/child relationships or store an ID index.
    - Parses directives and comments on the fly (available via small buffers if desired).
    - If a FASTA section is present, the generator stops yielding features and leaves FASTA
      handling to the caller via the `.fasta_generator()` method.

    Usage:
        with GFF3StreamingParser('file.gff3') as stream:
            for feat in stream:
                process(feat)
            # handle FASTA if present:
            for name, seq in stream.fasta_generator():
                handle_sequence(name, seq)
    """
    def __init__(self, path: str):
        self.path = path
        self._fh = None
        self.directives = []  # small buffer of seen directives
        self.comments = []
        self._in_fasta = False
        self._fasta_start_pos = None

    def __enter__(self):
        self._fh = open_file(self.path)
        # Position at start
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass
        self._fh = None

    def __iter__(self):
        if self._fh is None:
            self._fh = open_file(self.path)
        in_fasta = False
        for i, raw in enumerate(self._fh, start=1):
            line = raw.rstrip('\n')
            if in_fasta:
                # once FASTA begins, stop yielding features
                break
            if not line:
                continue
            if line.startswith('##'):
                self.directives.append((i, line))
                if line.strip().upper() == '##FASTA':
                    in_fasta = True
                    # remember file position for fasta_generator if possible
                    try:
                        # only works for real files, not pipes
                        self._fasta_start_pos = self._fh.tell()
                    except Exception:
                        self._fasta_start_pos = None
                continue
            if line.startswith('#'):
                self.comments.append((i, line))
                continue
            feat = GFF3Parser._parse_feature_line(self, line, i)
            if feat is not None:
                # Do not set children or index; only parse and yield
                yield feat
        # after iteration, mark fasta flag
        self._in_fasta = in_fasta

    def extract_directive(self, directive_name: str) -> str:
        for index, line in self.directives:
            if line.startswith(f"#!{directive_name}"):
                return line[len(directive_name)+2:].strip()
        for index, line in self.comments:
            if line.startswith(f"#!{directive_name}"):
                return line[len(directive_name)+2:].strip()
        return ""

    def fasta_generator(self):
        """Generator yielding (name, sequence) tuples for FASTA records.

        If the parser could seek to the FASTA section (file not a pipe), it will reuse
        the same file descriptor. Otherwise it will re-open the file and scan forward.
        """
        if not self._in_fasta:
            return
        fh = None
        try:
            if self._fh is not None and self._fasta_start_pos is not None:
                self._fh.seek(self._fasta_start_pos)
                fh = self._fh
            else:
                fh = open_file(self.path)
                # advance to FASTA marker
                for line in fh:
                    if line.startswith('##FASTA'):
                        break
            current_name = None
            seq_chunks = []
            for raw in fh:
                line = raw.rstrip('\n')
                if not line:
                    continue
                if line.startswith('>'):
                    if current_name is not None:
                        yield current_name, ''.join(seq_chunks)
                    current_name = line[1:].strip().split()[0]
                    seq_chunks = []
                else:
                    seq_chunks.append(line.strip())
            if current_name is not None:
                yield current_name, ''.join(seq_chunks)
        finally:
            # if we opened a new file handle, close it
            if fh is not None and fh is not self._fh:
                try:
                    fh.close()
                except Exception:
                    pass

