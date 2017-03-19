import pytest

from docker_multi_build.dockerfile import Token, tokenize


NON_ASCII = "žluťoučký"


table_tokenize = [
    (
        [
            'FROM busybox\n',
            'CMD ["/bin/true"]\n'
        ], [
            Token('FROM', 0, 0, 'FROM busybox\n', 'busybox'),
            Token('CMD', 1, 1, 'CMD ["/bin/true"]\n', '["/bin/true"]'),
        ],
    ), (
        [
            "# comment\n",        # should be ignored
            " From  \\\n",        # mixed-case
            "   base\n",          # extra ws, continuation line
            " # comment\n",
            " label  foo  \\\n",  # extra ws
            "    # comment\n",    # should be ignored
            "    bar  \n",        # extra ws, continuation line
            "USER  {0}\n".format(NON_ASCII),
            "# comment \\\n",     # extra ws
            "# comment \\ \n",    # extra ws with a space
            "# comment \\\\ \n",  # two backslashes
            "RUN command1\n",
            "RUN command2 && \\\n",
            "    # comment\n",
            "    command3\n",
        ], [
           Token('FROM',
                 startline=1,  # 0-based
                 endline=2,
                 content=' From  \\\n   base\n',
                 arguments='base'),
           Token('LABEL',
                 startline=4,
                 endline=6,
                 content=' label  foo  \\\n    bar  \n',
                 arguments='foo      bar'),
           Token('USER',
                 startline=7,
                 endline=7,
                 content='USER  {0}\n'.format(NON_ASCII),
                 arguments='{0}'.format(NON_ASCII)),
           Token('RUN',
                 startline=11,
                 endline=11,
                 content='RUN command1\n',
                 arguments='command1'),
           Token('RUN',
                 startline=12,
                 endline=14,
                 content='RUN command2 && \\\n    command3\n',
                 arguments='command2 &&     command3')
        ],
    ),
]


@pytest.mark.parametrize('lines, expected', table_tokenize)
def test_tokenize(lines, expected):
    tokens = tokenize(lines)
    assert tokens == expected
