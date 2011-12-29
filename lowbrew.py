#!/usr/bin/env python

import sys
import re
import argparse
import unittest

from itertools import takewhile 
from collections import namedtuple

class Header:
    def __init__(self, name, level):
        self.name = name[1]
        self.level = level[1]

    def __str__(self):
        return "%s\n%s" % (self.name, len(self.name) * "-")

class Weight:
    def __init__(self, numerator, denominator, unit):
        d = 1 if denominator is None else denominator
        self.number = numerator / d
        self.unit = unit

    def __str__(self):
        return "%s %s" % (self.pounds(), "lbs")

    def pounds(self):
        return self.number

class Grain:

    def __init__(self, name, weight, mashed=True):
        self.name = name
        self.weight = weight
        self.mashed = mashed

    def __str__(self):
        return "%s %s" % (self.weight, self.name)

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

def parse_name(text):
    print "Searching"
    m = re.search("(.*)\n=+", text)    
    return m.group(1)

def section_end_pos(text, name):
    
    section_re = re.compile("^" + name + "\n-+$", re.I|re.MULTILINE)
    section = section_re.search(text)
    return section.end()


def next_section_start_pos(text, start):
    """Returns the position of the start of the next level 1 or 2
    header following the given start position, or the length of the
    text if there are no more headers."""
    section_re = re.compile("^.*\n-+$", re.I|re.MULTILINE)    
    next_section = section_re.search(text, start)
    return len(text) if next_section is None else next_section.start()

def section_limits(text, name):
    start = section_end_pos(text, "grains")
    end = next_section_start_pos(text, start)
    return (start, end)

def parse_grains(text):
    
    grain_line_re = re.compile("^(\d+|\d*\.\d+|\d+\.\d*)(/(\d+))?\s+(lb|lbs|oz)\s+(.*)$", re.I|re.MULTILINE)

    (start, end) = section_limits(text, "grains")
    
    grains = []

    for m in grain_line_re.finditer(text, start, end):

        (n, d, unit, name) = m.group(1,3,4,5)
        n = float(n)
        if d is not None: d = float(d)
        w = Weight(n, d, unit)
        g = Grain(name, w)
        grains.append(g)
    return grains

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
        self.text = ""
        with open(filename) as f:
            text = f.read()
        f.close()
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

    def __str__(self):
        res = ""
        res += "\n\n"
        res += "Grains\n"
        res += "------\n"
        for g in self.grains:
            res += str(g) + "\n"
        return res
    
class LBTest(unittest.TestCase):
    def test_parse_name(self):
        name = parse_name("Other Stuff\nOatmeal Stout\n====\n")
        self.assertEqual(name, "Oatmeal Stout")

    def test_parse_grains(self):
        text = """
Fake Ale
========

Grains
------

11 lbs American 2 Row Pale
1.0 lb Crystal 60
1. lb Crystal 45
.5 lb Crystal 120
1/2 lb Chocolate Malt

Hops
----
1 oz Northern Brewer
1 oz Cascade
"""
        grains = parse_grains(text)
        weights = [g.weight.number for g in grains]
        names = [g.name for g in grains]
        expected_names = [
            "American 2 Row Pale",
            "Crystal 60",
            "Crystal 45",
            "Crystal 120",
            "Chocolate Malt"]
        self.assertEquals([11, 1, 1, .5, .5], weights)        
        self.assertEquals(expected_names, names)


def dotest(args):
    suite = unittest.TestLoader().loadTestsFromTestCase(LBTest)
    unittest.TextTestRunner(verbosity=2).run(suite)

parser = argparse.ArgumentParser(description="Do some stuff")
subparsers=parser.add_subparsers(help="Sub-command help")

parser_test=subparsers.add_parser("test", help="test")
parser_test.set_defaults(func=dotest)

args = parser.parse_args()
args.func(args)
#recipe = Recipe(sys.argv[1])
#print recipe
