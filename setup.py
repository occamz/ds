from setuptools import setup

setup(
    name="ds",
    version="1.0",
    py_modules=["ds"],
    install_requires=[
        "click",
        "click_aliases",
        "colorama",
        "hruid",
        "terminaltables",
        "PyYAML",
        "docker",
    ],
    entry_points="""
        [console_scripts]
        ds=ds:cli
    """,
)
