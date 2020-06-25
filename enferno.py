import click
import os

@click.command()
@click.argument('dir')
def create(dir):
    if os.path.isdir(dir):
        print ('Directory already exists.')
    else:
        os.system('git clone https://github.com/level09/enferno {}'.format(dir))
        ve = os.path.join(dir,'env')
        os.system('virtualenv {}'.format(ve))
        act = os.path.join(ve,'bin','activate')
        pp = os.path.join(ve,'bin','pip')
        req = os.path.join(dir,'requirements.txt')
        os.system('{a} install -r {b}'.format(a=pp,b=req))
        print ("Enferno Framework installed successfully into {}".format(dir))
