#!/bin/bash
sudo pip install pylint
sudo pip install --upgrade --pre pylint-odoo
sudo pip install pre-commit
sudo pip install git-pylint-commit-hook

pre-commit install
mv .git/hooks/pre-commit .git/hooks/pre-commit.bk

echo "
#!/usr/bin/env bash
git-pylint-commit-hook --pylintrc .pylintrc
" > .git/hooks/pre-commit

sudo chmod a+x .git/hooks/pre-commit

wget "https://raw.githubusercontent.com/jokekerker/initial_odoo_pylintrc/master/initial_odoo_pylintrc/.pylintrc"