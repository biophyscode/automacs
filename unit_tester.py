#!/usr/bin/env python

"""
Unit tester.
Called from ortho/unit_tester.py which does an external python call to this script, which must be found
in ortho and must be called via `python ortho/unit_tests.py.bak`.
"""

from __future__ import print_function
import shutil,os,sys
import unittest
import ortho

# unit tests are ordered by line number using the caseFactory and suiteFactory which must follow
# ordered unit tests via: https://codereview.stackexchange.com/questions/122532

import re,inspect

def caseFactory(scope,caseSorter=None,regex_test=None,
    caseSuperCls=unittest.TestCase):
    """Get test objects by occurence in the incoming scope."""
    if not scope: scope = globals().copy()
    if not caseSorter: caseSorter = lambda f: inspect.findsource(f)[1]
    if not regex_test: regex_test = "^Test"
    caseMatches = re.compile(regex_test)
    return sorted([scope[obj] for obj in scope if
        inspect.isclass(scope[obj]) and issubclass(scope[obj],caseSuperCls)
        and re.match(caseMatches,obj)
        ],key=caseSorter)

def suiteFactory(*testcases,**kwargs):
    testSorter = kwargs.get('testSorter',None)
    suiteMaker = kwargs.get('suiteMaker',unittest.makeSuite)
    newTestSuite = kwargs.get('newTestSuite',unittest.TestSuite)
    if testSorter is None:
        ln = lambda f: getattr(tc, f).__code__.co_firstlineno
        testSorter = lambda a, b: ln(a) - ln(b)
    test_suite = newTestSuite()
    for tc in testcases: 
        # special function to programatically add tests
        #! should this happen in self.setUp?
        if hasattr(tc,'_generate_programmatic_tests'): 
            getattr(tc,'_generate_programmatic_tests')()
        test_suite.addTest(suiteMaker(tc,sortUsing=testSorter))
    return test_suite

import os,shutil,tempfile

class temporary_copy(object):
    """
    Copy a file, temporarily. 
    via: https://stackoverflow.com/questions/6587516
    """
    def __init__(self,original_path):
        self.original_path = original_path
    def __enter__(self):
        temp_dir = tempfile.gettempdir()
        base_path = os.path.basename(self.original_path)
        self.path = os.path.join(temp_dir,base_path)
        shutil.copy2(self.original_path, self.path)
        return self.path
    def __exit__(self,exc_type, exc_val, exc_tb):
        os.remove(self.path)

def get_unit_tests():
    """Scan ortho for any unit tests. Tests are identified if they contain `unittest.` text."""
    import fnmatch
    matches = []
    for root,_,filenames in os.walk('ortho'):
        for filename in fnmatch.filter(filenames,'*.py'):
            if filename == 'unit_tester.py': continue
            fn = os.path.join(root,filename)
            with open(fn) as fp: text = fp.read()
            #! is this criterion too weak? consider modulefinder
            if re.search(r'unittest\.',text,re.M):
                matches.append(os.path.join(root,filename))
    return matches

def unit_tester(name='basic',save_config=False):
    """Run the unit tests."""
    special_imports = ['print_function']
    regex_test = {'basic':None,'special':'^SpecialTest'}.get(name,'^%s'%name)
    #! previously daisy-chained this function to a system call to a separated unit test file
    #! ... however placing the test here means that it runs inside a single execution
    config_fn = 'config.json'
    targets = get_unit_tests()
    mods = {}
    # collect items from unit tests
    for target in targets:
        # store functions by target
        mods[target] = {}
        print('status','importing %s'%target)
        #! you must be very careful not to use files like tests.py in ortho which contain unit tests
        #!   because a name collision with site-packages in e.g. a conda environment will cause no 
        #!   tests to be returned. this error is fairly opaque. it could be avoided with a call to
        #!   importlib that uses the dot notation e.g. importlib.import_module('ortho.tests')
        #! this might reflect a problem with the import scheme. collisions can be difficult to debug
        mod = ortho.importer(target) # pylint: disable=no-member
        for key,val in mod.items():
            if key in mods[target]: 
                raise Exception(
                    'refusing to overwrite redundant function when searching tests: %s from %s'%(
                        key,target))
            elif key in sys.modules: continue
            else: mods[target][key] = val
    if False:
        # merge functions from multiple targets
        mods_merged = {}
        for key in mods:
            for func_name in mods[key]:
                if func_name in mods_merged: raise Exception('name collision on testing: %s'%func_name)
                else: mods_merged[func_name] = mods[key][func_name]
    # temporary copy of config.json while we test
    # besides moving config.json, we use novel paths for all other tests
    with temporary_copy(config_fn) as fp:
        try:
            os.remove(config_fn)
            # unit test sequence starts here and detects all test suites above with names matching "^Test"
            these = [i for j in [caseFactory(scope=mods[k],regex_test=regex_test) for k in mods] for i in j]
            cases = suiteFactory(*these)
            #! could replace _generate_programmatic_tests with setUp if you pre-detect tests?
            runner = unittest.TextTestRunner(verbosity=2)
            runner.run(cases)
        except Exception as e: 
            print('warning','exception during unit_tester so we are replacing %s'%config_fn)
            print('error',e)
            shutil.copyfile(fp,config_fn)
            raise Exception(e)
        else: 
            if os.path.isfile(config_fn) and save_config: 
                shutil.copyfile(config_fn,'config.json.tested')
            shutil.copyfile(fp,config_fn)
