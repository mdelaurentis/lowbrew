#!/usr/bin/env python

import sys
import re
from itertools import takewhile 
from collections import namedtuple

class Header:
    def __init__(self, name, level):
        self.name = name[1]
        self.level = level[1]

    def __str__(self):
        return "%s\n%s" % (self.name, len(self.name) * "-")

class Weight:
    def __init__(self, number, unit):
        self.number = number
        self.unit = unit

    def __str__(self):
        return "%s %s" % (self.pounds(), "lbs")

    def pounds(self):
        (t, s) = self.number

        if self.unit.kind in ["LB", "LBS"]:
            if t in ["INT", "FLOAT"]:
                return float(s)
            if t == "RATIONAL":
                (n, d) = s.split("/")
                return float(n) / float(d)

class Grain:

    def __init__(self, name, weight, mashed=True):
        self.name = name
        self.weight = weight
        self.mashed = mashed

    def __str__(self):
        return "%s %s" % (self.weight, " ".join([x[1] for x in self.name]))

def categorize_token(token):

    types = [
        ("H1", re.compile("=+")),
        ("H2", re.compile("-+")),
#        ("GRAINS", re.compile("grains", re.I)),
        ("NOTES", re.compile("notes", re.I)),
#        ("HOPS", re.compile("hops", re.I)),
        ("LBS", re.compile("lb|lbs", re.I)),
        ("OZ", re.compile("oz", re.I)),
        ("SG", re.compile("sg", re.I)),
        ("MINUTES", re.compile("min|mins|minutes|minute", re.I)),
        ("BLANK", re.compile("\s+")),
        ("INT", re.compile("^\d+$")),
        ("FLOAT", re.compile("\d+\.\d+")),
        ("RATIONAL", re.compile("\d+\/\d+")),
        ("PREBOIL", re.compile("pre-boil", re.I)),
        ("POSTBOIL", re.compile("post-boil", re.I)),
        ("GAL", re.compile("gal|gals|gallons|gallon", re.I))]

    for (name, pat) in types:
        if pat.match(token) is not None:
            return Token(name, token)
    return Token("WORD", token)

def is_number(token):
    return token.kind in ["INT", "FLOAT", "RATIONAL"]

def is_weight_unit(token):
    return token.kind in ["OZ", "LBS"]

def is_word(token):
    return token.kind in ["WORD"]

def is_word_or_number(token):
    return is_word(token) or is_number(token)

def complement(f):
    return lambda x: not f(x)

Token = namedtuple('Token', ['kind', 'text'])

class Recipe:
    
    def __init__(self, filename):
        self.name = None
        self.grains = []
        self.hops = []
        self.pre_boil_volume = None
        self.post_boil_volume = None
        self.pre_boil_sg = None
        self.post_boil_sg = None
        self.notes = None
        
        if filename is not None:
            self._parse(filename)

    def _parse(self, filename):
        tokens = self._tokenize(filename)
        
        while tokens is not None and len(tokens) > 0:
            (grains, tokens) = self._parse_grain_list(tokens)
            if grains is None:
                tokens = tokens[1:]
            else:
                self.grains = grains
                return

    def _tokenize(self, filename):
        result = []
        lines = None
        with open(filename) as f:
            lines = f.readlines()
        f.close()
        for line in lines:
            result.extend(map(categorize_token, line[0:-1].split()))
            result.append(Token("NEWLINE", "\n"))
        return result
    
    def _parse_weight(self, tokens):
        if len(tokens) < 2:
            return (None, tokens)
        weight = tokens[0]
        unit   = tokens[1]
        if (is_number(weight) and
            is_weight_unit(unit)):
            return (Weight(weight, unit), tokens[2:])
        return (None, tokens)
        
    def _parse_grain(self, tokens):
        """Attempts to parse a grain specification from the given
        tokens.  Returns (grain, rest) if it can parse a grain from
        the beginning of tokens, otherwise (None, tokens)."""

        (weight, tokens) = self._parse_weight(tokens)
        if weight is not None:
            name = [x for x in takewhile(is_word_or_number, tokens)]
            return (Grain(name, weight), tokens[len(name):])
        return (None, tokens)

    def _parse_header(self, tokens):
        if len(tokens) < 3:
            return (None, tokens)

        name = tokens[0]
        newline = tokens[1]
        line = tokens[2]
        if (is_word(name) and
            newline.kind == "NEWLINE" and
            line.kind in ["H1", "H2"]):
            return (Header(name, line), tokens[2:])
        return (None, tokens)

    def _parse_grain_list(self, tokens):

        (header, rest) = self._parse_header(tokens)

        grains = []
        if header is not None and header.name == "Grains":
            while (rest is not None and
                   len(rest) > 0 and
                   self._parse_header(rest)[0] is None):
                (g, rest) = self._parse_grain(rest)
                if g is None:
                    rest = rest[1:]
                else:
                    grains.append(g)
            return (grains, rest)
        return (None, tokens)

    def __str__(self):
        res = ""
        res += "\n\n"
        res += "Grains\n"
        res += "------\n"
        for g in self.grains:
            res += str(g) + "\n"
        return res

recipe = Recipe(sys.argv[1])
print recipe
