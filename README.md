# gnize

This tool is currently a work of progress. it will support two modes:

 - cog
 - recog


If you find a signal in some noise, **cog**nize it.  Later, if you have some noise and wonder if that signal is hiding in it, **recog**nize it.

For now it just provides the utility command `gn` which generates the fingerprints necessary for the above two modes.

## Install


    python3 -m .venv
    source .venv/bin/activate
    python setup.py develop

## Use

While in a venv with gnize installed:


    gn --help
    echo 'abcd' | gn -a

    apt insall fortune
    FORTUNE=$(fortune -l)
    echo $FORTUNE
    echo $FORTUNE | gn
    echo $FORTUNE | gn -sn
    echo $FORTUNE | gn -sp
    echo $FORTUNE | gn -spn

