from distutils.core import setup, Extension
setup( 
    name = 'fullword',
    version = '1.0',
    ext_modules = [Extension('fullword', ['fullwordmodule.c'])]
)
