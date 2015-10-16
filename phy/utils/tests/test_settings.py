# -*- coding: utf-8 -*-

"""Test settings."""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

import os.path as op
from textwrap import dedent

from pytest import raises, yield_fixture
from traitlets import Float
from traitlets.config import Configurable

from .. import settings as _settings
from ..settings import (BaseSettings,
                        Settings,
                        _recursive_dirs,
                        _load_config,
                        load_master_config,
                        )


#------------------------------------------------------------------------------
# Fixtures
#------------------------------------------------------------------------------

@yield_fixture(params=['py', 'json'])
def settings(request):
    if request.param == 'py':
        yield ('py', '''a = 4\nb = 5\nd = {'k1': 2, 'k2': '3'}''')
    elif request.param == 'json':
        yield ('json', '''{"a": 4, "b": 5, "d": {"k1": 2, "k2": "3"}}''')


#------------------------------------------------------------------------------
# Test settings
#------------------------------------------------------------------------------

def test_phy_user_dir():
    assert _settings.phy_user_dir().endswith('.phy/')


def test_temp_user_dir(temp_user_dir):
    assert _settings.phy_user_dir() == temp_user_dir


def test_recursive_dirs():
    dirs = list(_recursive_dirs())
    assert len(dirs) >= 5
    root = op.join(op.realpath(op.dirname(__file__)), '../../')
    for dir in dirs:
        dir = op.relpath(dir, root)
        assert '.' not in dir
        assert '_' not in dir


def test_base_settings():
    s = BaseSettings()

    # Namespaces are mandatory.
    with raises(KeyError):
        s['a']

    s['a'] = 3
    assert s['a'] == 3


def test_base_settings_wrong_extension(tempdir):
    path = op.join(tempdir, 'test')
    with open(path, 'w'):
        pass
    s = BaseSettings()
    s.load(path=path)


def test_base_settings_file(tempdir, settings):
    ext, settings = settings
    path = op.join(tempdir, 'test.' + ext)
    with open(path, 'w') as f:
        f.write(settings)

    s = BaseSettings()

    s['a'] = 3
    s['c'] = 6
    assert s['a'] == 3

    # Warning: wrong path.
    s.load(path=None)

    # Now, load the settings file.
    s.load(path=path)
    assert s['a'] == 4
    assert s['b'] == 5
    assert s['c'] == 6
    assert s['d'] == {'k1': 2, 'k2': '3'}

    s = BaseSettings()
    s['d'] = {'k2': 30, 'k3': 40}
    s.load(path=path)
    assert s['d'] == {'k1': 2, 'k2': '3', 'k3': 40}


def test_base_settings_invalid(tempdir, settings):
    ext, settings = settings
    settings = settings[:-2]
    path = op.join(tempdir, 'test.' + ext)
    with open(path, 'w') as f:
        f.write(settings)

    s = BaseSettings()
    s.load(path)
    assert 'a' not in s


def test_internal_settings(tempdir):
    path = op.join(tempdir, 'test.json')

    s = BaseSettings()

    # Set the 'test' namespace.
    s['a'] = 3
    s['c'] = 6
    assert s['a'] == 3
    assert s['c'] == 6

    s.save(path)
    assert s['a'] == 3
    assert s['c'] == 6

    s = BaseSettings()
    with raises(KeyError):
        s['a']

    s.load(path)
    assert s['a'] == 3
    assert s['c'] == 6


def test_settings_nodir():
    Settings()


def test_settings_manager(tempdir, tempdir_bis):
    tempdir_exp = tempdir_bis
    sm = Settings(tempdir)

    # Check paths.
    assert sm.phy_user_dir == tempdir
    assert sm.internal_settings_path == op.join(tempdir,
                                                'internal_settings.json')
    assert sm.user_settings_path == op.join(tempdir, 'user_settings.py')

    # User settings.
    with raises(KeyError):
        sm['a']
    assert sm.get('a', None) is None
    # Artificially populate the user settings.
    sm._bs._store['a'] = 3
    assert sm['a'] == 3
    assert sm.get('a') == 3

    # Internal settings.
    sm['c'] = 5
    assert sm['c'] == 5

    # Set an experiment path.
    path = op.join(tempdir_exp, 'myexperiment.dat')
    sm.on_open(path)
    assert op.realpath(sm.exp_path) == op.realpath(path)
    assert sm.exp_name == 'myexperiment'
    assert (op.realpath(sm.exp_settings_dir) ==
            op.realpath(op.join(tempdir_exp, 'myexperiment.phy')))
    assert (op.realpath(sm.exp_settings_path) ==
            op.realpath(op.join(tempdir_exp, 'myexperiment.phy/'
                                             'user_settings.py')))

    # User settings.
    assert sm['a'] == 3
    sm._bs._store['a'] = 30
    assert sm['a'] == 30

    # Internal settings.
    sm['c'] = 50
    assert sm['c'] == 50

    # Check persistence.
    sm.save()
    sm = Settings(tempdir)
    sm.on_open(path)
    assert sm['c'] == 50
    assert 'a' not in sm

    assert str(sm).startswith('<Settings')
    assert sm.keys()


#------------------------------------------------------------------------------
# Config tests
#------------------------------------------------------------------------------

def test_load_config(tempdir):

    class MyConfigurable(Configurable):
        my_var = Float(0.0, config=True)

    assert MyConfigurable().my_var == 0.0

    # Create and load a config file.
    config_contents = dedent("""
       c = get_config()

       c.MyConfigurable.my_var = 1.0
       """)

    path = op.join(tempdir, 'config.py')
    with open(path, 'w') as f:
        f.write(config_contents)

    c = _load_config(path)
    assert c.MyConfigurable.my_var == 1.0

    # Create a new MyConfigurable instance.
    configurable = MyConfigurable()
    assert configurable.my_var == 0.0

    # Load the config object.
    configurable.update_config(c)
    assert configurable.my_var == 1.0


def test_load_master_config(temp_user_dir):
    # Create a config file in the temporary user directory.
    config_contents = dedent("""
       c = get_config()
       c.MyConfigurable.my_var = 1.0
       """)
    with open(op.join(temp_user_dir, 'phy_config.py'), 'w') as f:
        f.write(config_contents)

    # Load the master config file.
    c = load_master_config()
    assert c.MyConfigurable.my_var == 1.
