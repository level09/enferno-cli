from setuptools import setup

setup(
    name="Enferno",
    author_email="nidal@level09.com",
    description="Enferno framework CLI tool, helps you create and setup your Enferno app quickly.",
    license='MIT',
    version='0.1',
    py_modules=['enferno'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        enferno=enferno:create
    ''',
)
